import argparse
import os
import shutil
import sys
from pathlib import Path

try:
    from mutagen.mp3 import MP3
except ImportError:
    print("缺少 mutagen 库。请先在命令行运行：pip install mutagen")
    input("按回车键退出...")
    sys.exit(1)

# 只删除封面的 ID3 帧类型（APIC 是内嵌封面）
COVER_FRAME_IDS = ('APIC',)
# TXXX 帧描述里包含这些关键词的也视为封面相关
TXXX_COVER_KEYWORDS = ('cover', 'artwork', 'picture')
# 歌词帧：明确保留，用于统计提示
LYRIC_FRAME_IDS = ('USLT', 'SYLT')


def classify_cover_tags(mp3_path):
    """返回 (tags对象或None, 待删除key列表, 保留的歌词key列表)"""
    audio = MP3(mp3_path)
    if audio.tags is None:
        return None, [], []

    to_remove, lyric_keys = [], []
    for key in list(audio.tags.keys()):
        frame_id = key.split(':', 1)[0]
        if frame_id in COVER_FRAME_IDS:
            to_remove.append(key)
        elif frame_id == 'TXXX':
            desc = key.split(':', 1)[1].lower() if ':' in key else ''
            if any(kw in desc for kw in TXXX_COVER_KEYWORDS):
                to_remove.append(key)
        elif frame_id in LYRIC_FRAME_IDS:
            lyric_keys.append(key)
    return audio.tags, to_remove, lyric_keys


def strip_cover_one(mp3_path, dry_run=False, backup=False):
    """只去除封面，返回 (状态, 删除的key列表, 保留的歌词key列表)"""
    tags, to_remove, lyric_keys = classify_cover_tags(mp3_path)
    if tags is None:
        return 'no_tags', [], []
    if not to_remove:
        return 'nothing_to_remove', [], lyric_keys
    if dry_run:
        return 'would_remove', to_remove, lyric_keys

    if backup:
        shutil.copy2(mp3_path, mp3_path.with_suffix(mp3_path.suffix + '.bak'))

    # 先写临时文件，成功后替换，避免中途失败损坏原文件
    tmp = mp3_path.with_name(mp3_path.stem + '.tmp_nocover.mp3')
    shutil.copy2(mp3_path, tmp)
    try:
        audio = MP3(tmp)
        # 记录原 ID3 版本，保存时保持一致，避免 2.3/2.4 来回转换
        v2_minor = 3
        if audio.tags is not None and hasattr(audio.tags, 'version'):
            v2_minor = audio.tags.version[1] or 3
            if v2_minor not in (3, 4):
                v2_minor = 3
        for key in to_remove:
            if key in audio.tags:
                del audio.tags[key]
        audio.save(v2_version=v2_minor)
        os.replace(tmp, mp3_path)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise

    return 'removed', to_remove, lyric_keys


def main():
    parser = argparse.ArgumentParser(
        description='批量去除 MP3 内嵌封面，保留歌词和其他标签'
    )
    parser.add_argument('directory', nargs='?', default=None,
                        help='音乐目录（默认：脚本所在目录）')
    parser.add_argument('--dry-run', action='store_true',
                        help='只预览会删除什么，不实际修改')
    parser.add_argument('--backup', action='store_true',
                        help='修改前生成 .bak 备份')
    args = parser.parse_args()

    music_dir = Path(args.directory).resolve() if args.directory else Path(__file__).resolve().parent

    if not music_dir.is_dir():
        print(f'错误：目录不存在：{music_dir}')
        sys.exit(1)

    mp3_files = sorted(music_dir.rglob('*.mp3'))
    if not mp3_files:
        print(f'目录中没有找到 MP3：{music_dir}')
        sys.exit(0)

    print(f'目录: {music_dir}')
    print(f'MP3 数量: {len(mp3_files)}')
    if args.dry_run:
        print('模式: 预览（不会修改文件）')
    print('=' * 60)

    removed_count = 0
    nothing_count = 0
    no_tag_count = 0
    error_count = 0
    lyric_kept_total = 0

    for idx, mp3 in enumerate(mp3_files, 1):
        prefix = f'[{idx}/{len(mp3_files)}]'
        try:
            status, removed, lyric_keys = strip_cover_one(
                mp3, dry_run=args.dry_run, backup=args.backup
            )

            if status == 'no_tags':
                print(f'{prefix} 无 ID3 标签: {mp3.name}')
                no_tag_count += 1
                continue
            if status == 'nothing_to_remove':
                note = f'（保留歌词 {len(lyric_keys)} 项）' if lyric_keys else ''
                print(f'{prefix} 无封面: {mp3.name} {note}')
                nothing_count += 1
                lyric_kept_total += len(lyric_keys)
                continue

            action = '将删除' if status == 'would_remove' else '已删除'
            print(f'{prefix} {action}封面 {len(removed)} 项: {mp3.name}')
            for key in removed:
                print(f'        - {key}')
            if lyric_keys:
                print(f'        保留歌词 {len(lyric_keys)} 项: {", ".join(lyric_keys)}')
            else:
                print('        未发现歌词帧')
            lyric_kept_total += len(lyric_keys)
            if status == 'removed':
                removed_count += 1

        except Exception as e:
            print(f'{prefix} 错误: {mp3.name} - {e}')
            error_count += 1

    print('=' * 60)
    if args.dry_run:
        print(f'预览完成。需去除封面: {len(mp3_files) - nothing_count - no_tag_count}, '
              f'无封面: {nothing_count}, 无标签: {no_tag_count}, 错误: {error_count}')
    else:
        print(f'处理完成。已去除封面: {removed_count}, 无封面: {nothing_count}, '
              f'无标签: {no_tag_count}, 错误: {error_count}')
    print(f'保留歌词帧总数: {lyric_kept_total}')
    print(f'目录: {music_dir}')

    if not args.dry_run and sys.argv[1:] == []:
        input('\n按回车键退出...')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n已中断。')
        sys.exit(130)
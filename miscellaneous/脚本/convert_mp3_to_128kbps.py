import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def parse_report(txt_path):
    """解析报告文件，返回 (扫描目录, [文件名列表])"""
    text = Path(txt_path).read_text(encoding='utf-8-sig')
    music_dir = None
    files = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith('扫描目录'):
            music_dir = line.split(':', 1)[-1].split('：', 1)[-1].strip()
            continue
        if line.startswith('MP3') or line.startswith('==='):
            continue
        if '\t' in line:
            name = line.split('\t', 1)[0].strip()
            if name:
                files.append(name)

    return music_dir, files


def convert_one(src, dst, quality=5):
    """用 FFmpeg 以 VBR 模式把 src 转成 MP3，输出到 dst。
    quality: LAME VBR 等级 0-9，数字越小音质越高、体积越大。"""
    cmd = [
        'ffmpeg', '-hide_banner', '-loglevel', 'error',
        '-i', str(src),
        '-map', '0:a', '-map', '0:v?',
        '-c:a', 'libmp3lame', '-q:a', str(quality),
        '-c:v', 'copy',
        '-map_metadata', '0',
        '-id3v2_version', '3',
        '-y', str(dst),
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding='utf-8', errors='replace'
        )
    except FileNotFoundError:
        return False, '找不到 ffmpeg，请先安装并加入 PATH'
    if result.returncode != 0:
        err = (result.stderr or '').strip().splitlines()
        return False, err[-1] if err else f'ffmpeg 退出码 {result.returncode}'
    return True, ''


def main():
    parser = argparse.ArgumentParser(
        description='将 non_128kbps_songs.txt 中列出的 MP3 以 VBR 模式重新编码'
    )
    parser.add_argument('report', nargs='?', default='non_128kbps_songs.txt',
                        help='报告文件路径（默认 non_128kbps_songs.txt）')
    parser.add_argument('--out', default=None,
                        help='输出目录（默认：音乐目录同级的 <目录名>-vbr<等级>）')
    parser.add_argument('--in-place', action='store_true',
                        help='原地替换原文件（会先写临时文件，成功后替换）')
    parser.add_argument('--quality', type=int, default=5,
                        help='LAME VBR 质量等级 0-9（默认 5，约等于平均 130 kbps）')
    args = parser.parse_args()

    if not 0 <= args.quality <= 9:
        print('错误：--quality 必须在 0-9 之间。')
        sys.exit(1)

    if shutil.which('ffmpeg') is None:
        print('错误：未找到 ffmpeg。请安装 FFmpeg 并确保它在 PATH 中。')
        sys.exit(1)

    report_path = Path(args.report).resolve()
    if not report_path.is_file():
        print(f'错误：找不到报告文件 {report_path}')
        sys.exit(1)

    music_dir_str, files = parse_report(report_path)
    if not music_dir_str:
        print('错误：报告文件中没有找到“扫描目录”行。')
        sys.exit(1)
    if not files:
        print('报告文件中没有解析到任何 MP3 文件。')
        sys.exit(0)

    music_dir = Path(music_dir_str)
    if not music_dir.is_dir():
        print(f'错误：音乐目录不存在：{music_dir}')
        sys.exit(1)

    if args.in_place:
        out_dir = music_dir
    elif args.out:
        out_dir = Path(args.out).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = music_dir.parent / f'{music_dir.name}-vbr{args.quality}'
        out_dir.mkdir(parents=True, exist_ok=True)

    print(f'音乐目录: {music_dir}')
    print(f'输出目录: {out_dir}')
    print(f'VBR 质量等级: {args.quality}（0 最高，9 最低）')
    print(f'待处理文件: {len(files)}')
    print('=' * 60)

    ok = 0
    missing = 0
    failed = 0
    total_in = 0
    total_out = 0

    for idx, name in enumerate(files, 1):
        src = music_dir / name
        prefix = f'[{idx}/{len(files)}]'

        if not src.is_file():
            print(f'{prefix} 缺失: {name}')
            missing += 1
            continue

        if args.in_place:
            dst = src.with_name(src.stem + '.tmpvbr' + src.suffix)
        else:
            dst = out_dir / name

        print(f'{prefix} 转换: {name}')
        success, err = convert_one(src, dst, args.quality)

        if not success:
            print(f'        失败: {err}')
            failed += 1
            if args.in_place and dst.exists():
                dst.unlink()
            continue

        in_size = src.stat().st_size
        out_size = dst.stat().st_size
        total_in += in_size
        total_out += out_size

        if args.in_place:
            os.replace(dst, src)
            print(f'        完成（原地替换）: {in_size/1024/1024:.2f} MB -> {out_size/1024/1024:.2f} MB')
        else:
            print(f'        完成: {in_size/1024/1024:.2f} MB -> {out_size/1024/1024:.2f} MB')

        ok += 1

    print('=' * 60)
    print(f'处理完成。成功: {ok}, 缺失: {missing}, 失败: {failed}')
    if ok:
        saved = total_in - total_out
        print(f'总体积: {total_in/1024/1024:.2f} MB -> {total_out/1024/1024:.2f} MB '
              f'(节省 {saved/1024/1024:.2f} MB)')
    print(f'输出目录: {out_dir}')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n已中断。')
        sys.exit(130)
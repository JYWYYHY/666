import argparse
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


AUDIO_EXTS = (
    '.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.opus',
    '.wma', '.ape', '.aiff', '.aif', '.wv', '.mka',
)

CODEC_CONFIG = {
    'mp3':  {'codec': 'libmp3lame', 'ext': '.mp3'},
    'opus': {'codec': 'libopus',    'ext': '.opus'},
    'aac':  {'codec': 'aac',        'ext': '.m4a'},
    'm4a':  {'codec': 'aac',        'ext': '.m4a'},
    'flac': {'codec': 'flac',       'ext': '.flac'},
    'ogg':  {'codec': 'libvorbis',  'ext': '.ogg'},
    'wav':  {'codec': 'pcm_s16le',  'ext': '.wav'},
}

# 支持保留封面的输出格式（转 opus/ogg/wav 时封面会丢失）
COVER_OK_FORMATS = ('mp3', 'm4a', 'aac', 'flac')


def parse_report(txt_path):
    """解析报告文件。含“扫描目录”行时返回 (目录, 名字列表)，
    否则视为普通文件列表，目录取 .txt 所在目录。"""
    text = Path(txt_path).read_text(encoding='utf-8-sig')
    music_dir = None
    files = []
    has_header = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith('扫描目录'):
            music_dir = line.split(':', 1)[-1].split('：', 1)[-1].strip()
            has_header = True
            continue
        if line.startswith('MP3') or line.startswith('==='):
            continue
        name = line.split('\t', 1)[0].strip() if '\t' in line else line
        if name:
            files.append(name)
    if not has_header:
        music_dir = str(Path(txt_path).resolve().parent)
    return music_dir, files


def get_bitrate_kbps(path):
    """用 ffprobe 读取音频码率（kbps），失败返回 None。"""
    if shutil.which('ffprobe') is None:
        return None
    cmd = [
        'ffprobe', '-v', 'error', '-select_streams', 'a:0',
        '-show_entries', 'stream=bit_rate', '-of', 'default=nw=1:nk=1',
        str(path),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                           encoding='utf-8', errors='replace')
        if r.returncode == 0 and r.stdout.strip().isdigit():
            return int(r.stdout.strip()) / 1000.0
    except Exception:
        pass
    return None


def collect_files(inputs, recursive=True, exclude_dirs=()):
    """返回 [(base_dir, file_path)]，base_dir 用于计算输出相对路径。"""
    result, seen = [], set()
    exclude_resolved = [Path(p).resolve() for p in exclude_dirs]

    def is_excluded(p):
        rp = p.resolve()
        return any(rp == e or e in rp.parents for e in exclude_resolved)

    def add(base, f):
        key = str(f.resolve())
        if key not in seen:
            seen.add(key)
            result.append((base, f))

    for inp in inputs:
        p = Path(inp).resolve()
        if not p.exists():
            print(f'警告：输入不存在，跳过：{inp}')
            continue
        if p.is_file():
            suffix = p.suffix.lower()
            if suffix == '.txt':
                base_str, names = parse_report(p)
                base = Path(base_str).resolve()
                for name in names:
                    f = base / name
                    if f.is_file():
                        add(base, f)
                    else:
                        print(f'警告：报告中文件不存在：{f}')
            elif suffix in AUDIO_EXTS:
                add(p.parent, p)
            else:
                print(f'警告：不是音频文件，跳过：{p.name}')
        elif p.is_dir():
            globber = p.rglob('*') if recursive else p.glob('*')
            for f in globber:
                if not f.is_file() or f.suffix.lower() not in AUDIO_EXTS:
                    continue
                if is_excluded(f):
                    continue
                add(p, f)
    return result


def build_ffmpeg_cmd(src, dst, fmt, quality, bitrate, keep_cover=True):
    cfg = CODEC_CONFIG[fmt]
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error',
           '-i', str(src), '-map', '0:a']
    if keep_cover and fmt in COVER_OK_FORMATS:
        cmd += ['-map', '0:v?', '-c:v', 'copy']
    cmd += ['-c:a', cfg['codec']]
    if fmt == 'mp3':
        cmd += ['-q:a', str(quality), '-id3v2_version', '3']
    elif fmt == 'ogg':
        cmd += ['-q:a', str(quality)]
    elif fmt in ('opus', 'aac', 'm4a'):
        cmd += ['-b:a', bitrate]
    cmd += ['-map_metadata', '0', '-y', str(dst)]
    return cmd


def convert_one(src, dst, fmt, quality, bitrate, keep_cover=True):
    cmd = build_ffmpeg_cmd(src, dst, fmt, quality, bitrate, keep_cover)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
    except FileNotFoundError:
        return False, '找不到 ffmpeg'
    if r.returncode != 0:
        err = (r.stderr or '').strip().splitlines()
        return False, err[-1] if err else f'ffmpeg 退出码 {r.returncode}'
    return True, ''


def compute_output_path(out_dir, base, src, ext, used):
    """保持相对目录结构，冲突时加序号。"""
    rel = src.relative_to(base)
    dst = (out_dir / rel).with_suffix(ext)
    key = str(dst).lower()
    if key in used:
        i = 2
        while True:
            candidate = out_dir / rel.parent / f'{rel.stem} ({i}){ext}'
            ck = str(candidate).lower()
            if ck not in used:
                dst, key = candidate, ck
                break
            i += 1
    used.add(key)
    return dst


def main():
    parser = argparse.ArgumentParser(
        description='通用音频格式转换/重编码工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            '输入可混用多个：目录（递归查音频）、单个音频文件、报告文件（.txt）。\n'
            '不传输入时默认当前目录。\n\n'
            '示例：\n'
            '  python audio_convert.py .                       # 当前目录所有音频转 VBR5 MP3\n'
            '  python audio_convert.py . -f opus               # 转 128k Opus\n'
            '  python audio_convert.py . --min-bitrate 128     # 只处理 >=128k 的\n'
            '  python audio_convert.py non_128kbps_songs.txt   # 兼容旧报告格式\n'
        ),
    )
    parser.add_argument('inputs', nargs='*', help='输入（目录/文件/报告），默认当前目录')
    parser.add_argument('--format', '-f', default='mp3',
                        choices=sorted(CODEC_CONFIG.keys()), help='输出格式（默认 mp3）')
    parser.add_argument('--quality', '-q', type=int, default=5,
                        help='VBR 质量（mp3: 0-9，ogg: 0-10，默认 5）')
    parser.add_argument('--bitrate', '-b', default=None,
                        help='Opus/AAC 目标码率（默认 opus=128k, aac=192k）')
    parser.add_argument('--out', '-o', default=None, help='输出目录')
    parser.add_argument('--suffix', default=None, help='自动输出目录的后缀')
    parser.add_argument('--in-place', action='store_true',
                        help='原地替换（要求输出扩展名与源相同）')
    parser.add_argument('--min-bitrate', type=float, default=None,
                        help='只处理码率 >= 此值（kbps）的文件，需 ffprobe')
    parser.add_argument('--no-recursive', action='store_true', help='不递归子目录')
    parser.add_argument('--strip-cover', action='store_true', help='不保留封面')
    parser.add_argument('--dry-run', action='store_true', help='只预览，不实际转换')
    args = parser.parse_args()

    if args.format == 'mp3' and not 0 <= args.quality <= 9:
        print('错误：mp3 的 --quality 必须在 0-9 之间。')
        sys.exit(1)
    if args.format == 'ogg' and not 0 <= args.quality <= 10:
        print('错误：ogg 的 --quality 必须在 0-10 之间。')
        sys.exit(1)

    bitrate = args.bitrate
    if bitrate is None:
        if args.format == 'opus':
            bitrate = '128k'
        elif args.format in ('aac', 'm4a'):
            bitrate = '192k'

    if shutil.which('ffmpeg') is None:
        print('错误：未找到 ffmpeg。')
        sys.exit(1)
    if args.min_bitrate is not None and shutil.which('ffprobe') is None:
        print('错误：--min-bitrate 需要 ffprobe。')
        sys.exit(1)
    if args.in_place and args.out:
        print('注意：--in-place 与 --out 同时指定，--out 将被忽略。')

    inputs = args.inputs if args.inputs else ['.']

    # 确定输出目录
    if args.in_place:
        out_dir = None
    elif args.out:
        out_dir = Path(args.out).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        if args.suffix is not None:
            suffix = args.suffix
        elif args.format == 'mp3':
            suffix = f'-vbr{args.quality}'
        else:
            suffix = f'-{args.format}'

        dir_inputs = [Path(i).resolve() for i in inputs if Path(i).is_dir()]
        if len(inputs) == 1 and len(dir_inputs) == 1 and Path(inputs[0]).is_dir():
            base = dir_inputs[0]
            out_dir = base.parent / f'{base.name}{suffix}'
        else:
            out_dir = Path.cwd() / f'converted{suffix}'
        out_dir.mkdir(parents=True, exist_ok=True)

    entries = collect_files(inputs, recursive=not args.no_recursive,
                            exclude_dirs=[out_dir] if out_dir else [])
    if not entries:
        print('没有找到待处理的音频文件。')
        sys.exit(0)

    if args.min_bitrate is not None:
        filtered = []
        for base, f in entries:
            br = get_bitrate_kbps(f)
            if br is not None and br >= args.min_bitrate:
                filtered.append((base, f))
        entries = filtered
        if not entries:
            print(f'没有码率 >= {args.min_bitrate} kbps 的文件。')
            sys.exit(0)

    quality_desc = {
        'mp3': f'（VBR 质量 {args.quality}）',
        'ogg': f'（VBR 质量 {args.quality}）',
        'opus': f'（码率 {bitrate}）',
        'aac': f'（码率 {bitrate}）',
        'm4a': f'（码率 {bitrate}）',
        'flac': '（无损）',
        'wav': '（无损 PCM）',
    }[args.format]

    print(f'输出格式: {args.format}{quality_desc}')
    print(f'输出目录: {out_dir}' if out_dir else '模式: 原地替换')
    if args.format in ('opus', 'ogg', 'wav'):
        print('提示：该输出格式不支持保留封面')
    print(f'待处理文件: {len(entries)}')
    if args.dry_run:
        print('模式: 预览（不实际转换）')
    print('=' * 60)

    ext = CODEC_CONFIG[args.format]['ext']
    ok = skipped = failed = 0
    total_in = total_out = 0
    used_outputs = set()

    for idx, (base, src) in enumerate(entries, 1):
        prefix = f'[{idx}/{len(entries)}]'

        if args.in_place:
            if src.suffix.lower() != ext:
                print(f'{prefix} 跳过（原地替换要求扩展名一致：{src.suffix} != {ext}）: {src.name}')
                skipped += 1
                continue
            tmp_name = src.name + f'.tmp_{uuid.uuid4().hex[:8]}'
            dst, final_dst = src.with_name(tmp_name), src
        else:
            dst = compute_output_path(out_dir, base, src, ext, used_outputs)
            final_dst = dst

        print(f'{prefix} 转换: {src}')
        if args.dry_run:
            print(f'        → {final_dst}')
            ok += 1
            continue

        success, err = convert_one(
            src, dst, args.format, args.quality, bitrate,
            keep_cover=not args.strip_cover,
        )
        if not success:
            print(f'        失败: {err}')
            failed += 1
            if args.in_place and dst.exists():
                dst.unlink()
            continue

        in_size, out_size = src.stat().st_size, dst.stat().st_size
        total_in += in_size
        total_out += out_size

        if args.in_place:
            os.replace(dst, final_dst)
            print(f'        完成（原地替换）: {in_size/1024/1024:.2f} MB -> {out_size/1024/1024:.2f} MB')
        else:
            print(f'        完成: {in_size/1024/1024:.2f} MB -> {out_size/1024/1024:.2f} MB')
        ok += 1

    print('=' * 60)
    print(f'处理完成。{"待转换" if args.dry_run else "成功"}: {ok}, 跳过: {skipped}, 失败: {failed}')
    if not args.dry_run and ok and total_in:
        saved = total_in - total_out
        pct = saved / total_in * 100
        print(f'总体积: {total_in/1024/1024:.2f} MB -> {total_out/1024/1024:.2f} MB '
              f'(节省 {saved/1024/1024:.2f} MB, {pct:.1f}%)')
    if out_dir:
        print(f'输出目录: {out_dir}')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n已中断。')
        sys.exit(130)
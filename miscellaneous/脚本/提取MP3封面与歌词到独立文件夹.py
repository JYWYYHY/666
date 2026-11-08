import sys
from pathlib import Path

try:
    from mutagen.mp3 import MP3
except ImportError:
    print("缺少 mutagen 库。请先在命令行运行：pip install mutagen")
    input("按回车键退出...")
    sys.exit(1)

MIME_EXT = {
    'image/jpeg': '.jpg', 'image/jpg': '.jpg', 'image/png': '.png',
    'image/gif': '.gif', 'image/webp': '.webp', 'image/bmp': '.bmp',
    'image/tiff': '.tiff', 'image/tif': '.tiff',
}

INVALID_CHARS = '<>:"/\\|?*'


def safe_name(s, fallback='unnamed'):
    s = str(s or '')
    for ch in INVALID_CHARS:
        s = s.replace(ch, '_')
    s = s.strip().rstrip('.')
    return s or fallback


def mime_to_ext(mime):
    mime = (mime or '').lower().split(';')[0].strip()
    if mime in MIME_EXT:
        return MIME_EXT[mime]
    if '/' in mime:
        sub = mime.split('/', 1)[1].strip()
        if sub:
            return '.' + sub
    return '.bin'


def sylt_to_lrc(sylt):
    """把 SYLT 同步歌词转成 LRC 文本"""
    lines = []
    for entry in (sylt.text or []):
        if not isinstance(entry, (tuple, list)) or len(entry) != 2:
            continue
        text, ts = entry
        try:
            ms = int(ts)
        except (TypeError, ValueError):
            continue
        minutes = ms // 60000
        seconds = (ms % 60000) / 1000.0
        lines.append(f'[{minutes:02d}:{seconds:05.2f}]{text}')
    return '\n'.join(lines)


def extract_one(mp3_path, cover_dir, lyric_dir):
    """提取单个 MP3，返回 (封面数, 歌词数, 错误列表)"""
    errors = []
    covers = 0
    lyrics = 0

    try:
        audio = MP3(mp3_path)
    except Exception as e:
        return 0, 0, [f'无法读取: {e}']

    if audio.tags is None:
        return 0, 0, []

    stem = safe_name(mp3_path.stem)

    # ---------- 封面：{stem}.{ext}，多张时加 _2、_3 ----------
    apic_items = [audio.tags[k] for k in audio.tags.keys() if k.startswith('APIC')]
    used = set()
    for i, apic in enumerate(apic_items, 1):
        ext = mime_to_ext(apic.mime)
        base = stem if i == 1 else f'{stem}_{i}'
        name = base + ext
        n = 2
        while name.lower() in used:
            name = f'{base}_{n}{ext}'
            n += 1
        used.add(name.lower())
        cover_dir.mkdir(parents=True, exist_ok=True)
        try:
            (cover_dir / name).write_bytes(apic.data)
            covers += 1
        except Exception as e:
            errors.append(f'封面写入失败 {name}: {e}')

    # ---------- 歌词：全部存成 .lrc ----------
    # SYLT（同步）排在前面，USLT（纯文本）排在后面
    lyric_texts = []
    for k in audio.tags.keys():
        if k.startswith('SYLT'):
            lrc = sylt_to_lrc(audio.tags[k])
            if lrc.strip():
                lyric_texts.append(lrc)
    for k in audio.tags.keys():
        if k.startswith('USLT'):
            text = (audio.tags[k].text or '').strip()
            if text:
                lyric_texts.append(text)

    used = set()
    for i, content in enumerate(lyric_texts, 1):
        base = stem if i == 1 else f'{stem}_{i}'
        name = base + '.lrc'
        n = 2
        while name.lower() in used:
            name = f'{base}_{n}.lrc'
            n += 1
        used.add(name.lower())
        lyric_dir.mkdir(parents=True, exist_ok=True)
        try:
            (lyric_dir / name).write_text(content, encoding='utf-8')
            lyrics += 1
        except Exception as e:
            errors.append(f'歌词写入失败 {name}: {e}')

    return covers, lyrics, errors


def main():
    base_dir = Path(__file__).resolve().parent
    cover_dir = base_dir / 'cover'
    lyric_dir = base_dir / 'lyrics'

    mp3_files = sorted(f for f in base_dir.glob('*.mp3') if f.is_file())
    if not mp3_files:
        print(f'目录中没有找到 MP3：{base_dir}')
        sys.exit(0)

    print(f'目录: {base_dir}')
    print(f'封面输出: {cover_dir}')
    print(f'歌词输出: {lyric_dir}')
    print(f'MP3 数量: {len(mp3_files)}')
    print('=' * 60)

    total_covers = total_lyrics = files_with_data = 0
    files_no_data = error_count = 0

    for idx, mp3 in enumerate(mp3_files, 1):
        prefix = f'[{idx}/{len(mp3_files)}]'
        try:
            c, l, errs = extract_one(mp3, cover_dir, lyric_dir)
        except Exception as e:
            print(f'{prefix} 错误: {mp3.name} - {e}')
            error_count += 1
            continue

        for e in errs:
            print(f'{prefix} 警告: {e}')
            error_count += 1

        if c or l:
            parts = []
            if c: parts.append(f'{c} 封面')
            if l: parts.append(f'{l} 歌词')
            print(f'{prefix} {mp3.name} -> {", ".join(parts)}')
            total_covers += c
            total_lyrics += l
            files_with_data += 1
        else:
            print(f'{prefix} {mp3.name} 无封面/歌词')
            files_no_data += 1

    print('=' * 60)
    print(f'处理完成。有数据: {files_with_data}, 无数据: {files_no_data}, 错误: {error_count}')
    print(f'封面: {total_covers} 个文件, 歌词: {total_lyrics} 个文件')
    print(f'封面目录: {cover_dir}')
    print(f'歌词目录: {lyric_dir}')

    input('\n按回车键退出...')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n已中断。')
        sys.exit(130)
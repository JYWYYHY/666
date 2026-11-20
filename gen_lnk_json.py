#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描 lnk/ 目录生成 lnk.json
- .url 文件：解析 INI 中的 URL= （纯文本，跨平台）
- .lnk 文件：Windows 上用 pywin32 读 TargetPath；其它平台留空占位
用法：
    python gen_lnk_json.py            # 扫描 ./lnk
    python gen_lnk_json.py .          # 指定仓库根
    安装 pywin32：pip install pywin32
"""
import configparser, json, sys
from pathlib import Path


def parse_url_file(path):
    text = path.read_bytes().decode('utf-8', errors='replace')
    cp = configparser.ConfigParser()
    try:
        cp.read_string(text)
        for sec in cp.sections():
            for k, v in cp.items(sec):
                if k.lower() == 'url':
                    return v.strip()
    except Exception:
        pass
    for line in text.splitlines():
        line = line.strip()
        if line.lower().startswith('url='):
            return line.split('=', 1)[1].strip()
    return None


def parse_lnk_file(path):
    try:
        import win32com.client
    except ImportError:
        return None
    try:
        shell = win32com.client.Dispatch('WScript.Shell')
        sc = shell.CreateShortcut(str(path))
        target = (sc.TargetPath or '').strip()
        return target or None
    except Exception:
        return None


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
    lnk_dir = root / 'lnk'
    out_file = root / 'lnk.json'

    if not lnk_dir.exists():
        print(f'目录不存在：{lnk_dir}')
        return

    result = {}
    for path in sorted(lnk_dir.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        suffix = path.suffix.lower()
        if suffix == '.url':
            url = parse_url_file(path)
            if url:
                result[rel] = {'type': 'url', 'target': url}
            else:
                result[rel] = {'type': 'url', 'target': ''}
        elif suffix == '.lnk':
            target = parse_lnk_file(path)
            result[rel] = {'type': 'app', 'target': target or ''}

    out_file.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    print(f'✅ 已生成 {out_file}（{len(result)} 条）')
    empty = [k for k, v in result.items() if not v['target']]
    if empty:
        print(f'⚠️ 有 {len(empty)} 条目标为空，需要手动补充（多半是 .lnk 且非 Windows）：')
        for k in empty[:20]:
            print('   ', k)
        if len(empty) > 20:
            print(f'    ... 另有 {len(empty) - 20} 条')


if __name__ == '__main__':
    main()
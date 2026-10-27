#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接扫描磁盘目录，生成 index.json（格式一：嵌套 children）
供 GitHub Pages 上的文件索引页使用。

用法:
    python gen_index.py                           # 扫描当前目录 → index.json
    python gen_index.py -r D:\\Files -o index.json
    python gen_index.py -x .git -x node_modules   # 追加排除项
    python gen_index.py --keep                    # 保留 README.md / .gitattributes
"""
import argparse
import json
import os
import sys

# 默认排除（不写入 index.json）
DEFAULT_EXCLUDE = {
    # 版本控制 / 编辑器
    '.git', '.github', '.gitattributes', '.gitignore',
    '.vscode', '.idea',
    # 本脚本及其产物
    'gen_index.py', 'index.json', 'folder_structure.txt',
    'README.md',
    # 系统垃圾
    '.DS_Store', 'Thumbs.db', 'desktop.ini',
    # 缓存 / 虚拟环境
    'node_modules', '__pycache__', '.venv', 'venv',
}

def scan(path, exclude):
    """递归扫描，返回 [{name} | {name, children}] 列表"""
    try:
        entries = list(os.scandir(path))
    except (PermissionError, OSError):
        return []

    dirs, files = [], []
    for e in entries:
        name = e.name
        if name in exclude:
            continue
        try:
            if e.is_dir(follow_symlinks=False):
                dirs.append({
                    "name": name,
                    "children": scan(e.path, exclude),
                })
            elif e.is_file(follow_symlinks=False):
                files.append({"name": name})
        except OSError:
            continue

    key = lambda x: x["name"].lower()
    dirs.sort(key=key)
    files.sort(key=key)
    return dirs + files

def count(nodes):
    n = 0
    for x in nodes:
        n += count(x["children"]) if "children" in x else 1
    return n

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-r', '--root',   default='.',        help='扫描根目录（默认当前）')
    ap.add_argument('-o', '--output', default='index.json', help='输出文件')
    ap.add_argument('-x', '--exclude', action='append', default=[], help='额外排除项，可多次使用')
    ap.add_argument('--keep', action='store_true', help='保留 README.md / .gitattributes')
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f'❌ 目录不存在: {root}')
        sys.exit(1)

    exclude = set(DEFAULT_EXCLUDE) | set(args.exclude)
    if args.keep:
        exclude -= {'README.md', '.gitattributes'}

    data  = scan(root, exclude)
    total = count(data)

    out = args.output if os.path.isabs(args.output) else os.path.join(root, args.output)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({"children": data}, f, ensure_ascii=False, indent=1)

    print(f'✅ 已生成: {out}')
    print(f'   顶层条目: {len(data)}')
    print(f'   文件总数: {total}')

if __name__ == '__main__':
    main()
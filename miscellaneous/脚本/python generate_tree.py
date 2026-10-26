#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成当前目录的树形结构，保存为 txt 文件并打印到终端。

用法示例：
    python generate_tree.py
    python generate_tree.py -o structure.txt
    python generate_tree.py --no-files
    python generate_tree.py -d 3
    python generate_tree.py --all
    python generate_tree.py --print-only
"""

import argparse
import os
import sys
from pathlib import Path

DEFAULT_IGNORE_DIRS = {
    ".git", ".svn", ".hg",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", "venv", ".venv", "env", ".env",
    "dist", "build", ".idea", ".vscode",
}

DEFAULT_IGNORE_FILES = {
    ".DS_Store", "Thumbs.db",
}


def should_ignore(entry, ignore_dirs, ignore_files, include_all):
    if include_all:
        return False
    if entry.is_dir(follow_symlinks=False):
        return entry.name in ignore_dirs
    return entry.name in ignore_files


def generate_tree(root, output_path=None, max_depth=0, include_files=True, include_all=False):
    root = Path(root).resolve()
    output_abs = Path(output_path).resolve() if output_path else None

    ignore_dirs = set() if include_all else DEFAULT_IGNORE_DIRS
    ignore_files = set() if include_all else DEFAULT_IGNORE_FILES

    lines = [f"当前目录: {root}", f"{root.name or str(root)}/"]

    def walk(dir_path, prefix="", depth=1):
        if max_depth and depth > max_depth:
            return

        try:
            entries = list(os.scandir(dir_path))
        except PermissionError:
            lines.append(f"{prefix}└── [无权限访问]")
            return
        except OSError as e:
            lines.append(f"{prefix}└── [读取失败: {e}]")
            return

        filtered = []
        for entry in entries:
            # 排除输出文件本身，避免把自己写进结构里
            try:
                if output_abs and Path(entry.path).resolve() == output_abs:
                    continue
            except OSError:
                pass

            if should_ignore(entry, ignore_dirs, ignore_files, include_all):
                continue

            if not include_files and not entry.is_dir(follow_symlinks=False):
                continue

            filtered.append(entry)

        # 目录在前，文件在后；名称不区分大小写排序
        def sort_key(e):
            is_dir = e.is_dir(follow_symlinks=False)
            return (0 if is_dir else 1, e.name.lower())

        filtered.sort(key=sort_key)

        total = len(filtered)
        for i, entry in enumerate(filtered):
            is_last = i == total - 1
            connector = "└── " if is_last else "├── "
            is_dir = entry.is_dir(follow_symlinks=False)
            name = entry.name

            if is_dir:
                name += "/"
            elif entry.is_symlink():
                try:
                    name += f" -> {os.readlink(entry.path)}"
                except OSError:
                    pass

            lines.append(f"{prefix}{connector}{name}")

            if is_dir:
                # 不跟随符号链接目录，避免循环
                if entry.is_symlink():
                    continue
                next_prefix = prefix + ("    " if is_last else "│   ")
                walk(entry.path, next_prefix, depth + 1)

    walk(root, "", 1)
    return "\n".join(lines) + "\n"


def main():
    # 尽量让 Windows 终端也能正常输出 Unicode 树形字符
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="生成当前目录的树形结构 txt 文件")
    parser.add_argument(
        "-o", "--output",
        default="folder_structure.txt",
        help="输出文件名，默认 folder_structure.txt"
    )
    parser.add_argument(
        "-d", "--max-depth",
        type=int,
        default=0,
        help="最大深度，0 表示不限制"
    )
    parser.add_argument(
        "--no-files",
        action="store_true",
        help="只显示文件夹，不显示文件"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="包含隐藏文件和常见忽略目录，如 .git、node_modules"
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="只打印到终端，不写入文件"
    )
    args = parser.parse_args()

    root = Path.cwd()
    output_path = None if args.print_only else (root / args.output)

    text = generate_tree(
        root=root,
        output_path=output_path,
        max_depth=args.max_depth,
        include_files=not args.no_files,
        include_all=args.all,
    )

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
        print(f"已生成: {output_path}")

    print(text, end="")


if __name__ == "__main__":
    main()
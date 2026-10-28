#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描磁盘目录，生成 index.json（嵌套 children 格式）
支持 .indexignore 排除规则（类 gitignore 语法）

用法:
    python gen_index.py                              # 扫描当前目录 → index.json
    python gen_index.py -r D:\\Files -o index.json
    python gen_index.py -i .indexignore
"""
import argparse
import json
import os
import re
import sys

# 无论如何都不能被扫描进来的文件（防止自身递归 / index.json 包含自己）
MUST_EXCLUDE = {'index.json', 'gen_index.py', '.indexignore'}


class IgnoreRule:
    """单条 gitignore 风格规则"""
    __slots__ = ('negate', 'dir_only', 'root_only', 'has_slash', 'regex')

    def __init__(self, pattern):
        self.negate = False
        if pattern.startswith('!'):
            self.negate = True
            pattern = pattern[1:]
        self.dir_only = pattern.endswith('/')
        if self.dir_only:
            pattern = pattern[:-1]
        self.root_only = pattern.startswith('/')
        if self.root_only:
            pattern = pattern[1:]
        self.has_slash = '/' in pattern
        self.regex = re.compile(self._compile(pattern))

    @staticmethod
    def _compile(pat):
        i, n, out = 0, len(pat), []
        while i < n:
            c = pat[i]
            if c == '*':
                if i + 1 < n and pat[i + 1] == '*':
                    if i + 2 < n and pat[i + 2] == '/':
                        out.append('(?:.*/)?')   # **/  → 任意层级
                        i += 3
                    else:
                        out.append('.*')          # **   → 任意字符
                        i += 2
                else:
                    out.append('[^/]*')           # *    → 单层任意
                    i += 1
            elif c == '?':
                out.append('[^/]')
                i += 1
            elif c == '[':
                j = i + 1
                if j < n and pat[j] in '!^':
                    j += 1
                if j < n and pat[j] == ']':
                    j += 1
                while j < n and pat[j] != ']':
                    j += 1
                if j >= n:
                    out.append(r'\[')
                    i += 1
                else:
                    stuff = pat[i + 1:j].replace('\\', r'\\')
                    if stuff.startswith('!'):
                        stuff = '^' + stuff[1:]
                    elif stuff.startswith('^'):
                        stuff = '\\' + stuff
                    out.append('[' + stuff + ']')
                    i = j + 1
            elif c == '\\' and i + 1 < n:
                out.append(re.escape(pat[i + 1]))
                i += 2
            else:
                out.append(re.escape(c))
                i += 1
        return ''.join(out)

    def match(self, relpath, is_dir):
        if self.dir_only and not is_dir:
            return False
        if self.root_only or self.has_slash:
            return self.regex.fullmatch(relpath) is not None
        base = relpath.rsplit('/', 1)[-1]
        return self.regex.fullmatch(base) is not None


def load_rules(path):
    if not os.path.exists(path):
        return []
    rules = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n').rstrip('\r')
            line = re.sub(r'(?<!\\) +$', '', line)   # 去掉行末未转义空格
            if not line.strip() or line.startswith('#'):
                continue
            rules.append(IgnoreRule(line))
    return rules


def is_ignored(relpath, is_dir, rules):
    """最后匹配的规则生效"""
    ignored = False
    for r in rules:
        if r.match(relpath, is_dir):
            ignored = not r.negate
    return ignored


def scan(root, cur, rules):
    try:
        entries = list(os.scandir(cur))
    except (PermissionError, OSError):
        return []

    dirs, files = [], []
    for e in entries:
        name = e.name
        if name in MUST_EXCLUDE:
            continue
        try:
            is_dir = e.is_dir(follow_symlinks=False)
            is_file = e.is_file(follow_symlinks=False)
        except OSError:
            continue

        relpath = os.path.relpath(e.path, root).replace(os.sep, '/')
        if is_ignored(relpath, is_dir, rules):
            continue

        if is_dir:
            dirs.append({
                "name": name,
                "children": scan(root, e.path, rules),
            })
        elif is_file:
            files.append({"name": name})

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
    ap.add_argument('-r', '--root',   default='.',          help='扫描根目录')
    ap.add_argument('-o', '--output', default='index.json', help='输出文件')
    ap.add_argument('-i', '--ignore', default='.indexignore', help='排除规则文件')
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f'❌ 目录不存在: {root}')
        sys.exit(1)

    ignore_path = args.ignore if os.path.isabs(args.ignore) \
                  else os.path.join(root, args.ignore)
    rules = load_rules(ignore_path)
    if rules:
        print(f'📋 已加载排除规则: {os.path.basename(ignore_path)}（{len(rules)} 条）')
    else:
        print(f'📋 未找到排除规则文件: {ignore_path}')

    data  = scan(root, root, rules)
    total = count(data)

    out = args.output if os.path.isabs(args.output) else os.path.join(root, args.output)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({"children": data}, f, ensure_ascii=False, indent=1)

    print(f'✅ 已生成: {out}')
    print(f'   顶层条目: {len(data)}')
    print(f'   文件总数: {total}')


if __name__ == '__main__':
    main()
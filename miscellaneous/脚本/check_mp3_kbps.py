#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
递归扫描指定目录下的所有 MP3，
把码率（kbps）不等于 128 的文件写入 txt，并在后面附上码率。
用法：
    python check_mp3_kbps.py            # 扫描当前目录
    python check_mp3_kbps.py D:\Music   # 扫描指定目录
"""

import os
import sys

try:
    from mutagen.mp3 import MP3
except ImportError:
    print("缺少 mutagen，请先运行：pip install mutagen")
    sys.exit(1)


def main():
    # 默认扫描当前目录，也可以命令行传目录
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
    output = os.path.join(root, "non_128kbps_songs.txt")

    total = 0
    bad = 0
    lines = []

    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if not name.lower().endswith(".mp3"):
                continue

            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            total += 1

            try:
                info = MP3(path).info
                kbps = round(info.bitrate / 1000) if info.bitrate else 0
            except Exception as e:
                # 读不出来也记下来，方便你手动检查
                lines.append(f"{rel}\t[读取失败: {e}]")
                bad += 1
                continue

            if kbps != 128:
                # 顺带标注 VBR / CBR，方便判断
                mode = ""
                try:
                    mode = f" ({info.bitrate_mode.name})"
                except Exception:
                    pass
                lines.append(f"{rel}\t{kbps} kbps{mode}")
                bad += 1

    # 写结果文件
    with open(output, "w", encoding="utf-8") as f:
        f.write(f"扫描目录: {root}\n")
        f.write(f"MP3 总数: {total}，非 128 kbps: {bad}\n")
        f.write("=" * 70 + "\n")
        if lines:
            f.write("\n".join(lines) + "\n")
        else:
            f.write("所有 MP3 都是 128 kbps。\n")

    print(f"共扫描 {total} 个 MP3，其中 {bad} 个不是 128 kbps。")
    print(f"结果已写入：{output}")


if __name__ == "__main__":
    main()
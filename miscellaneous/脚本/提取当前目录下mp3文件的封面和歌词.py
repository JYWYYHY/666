#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动从当前目录（或上级 static 目录）提取 MP3 的内嵌歌词和封面。
生成同名的 .lrc 和 .jpg 文件。
"""

import sys
import io
from pathlib import Path
from typing import Optional
from mutagen.mp3 import MP3

# 尝试导入 Pillow，用于 PNG 转 JPG
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def ms_to_lrc(ms: int) -> str:
    """毫秒转 LRC 时间标签 [mm:ss.xx]"""
    total_seconds = ms / 1000.0
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    hundredths = int((total_seconds - int(total_seconds)) * 100)
    return f"[{minutes:02d}:{seconds:02d}.{hundredths:02d}]"


def sylt_to_lrc(sylt_frame) -> str:
    """把 ID3 SYLT 同步歌词转成 LRC 文本"""
    lines = []
    for item in sylt_frame.text:
        if isinstance(item, tuple) and len(item) == 2:
            text, time_ms = item
            lines.append(f"{ms_to_lrc(time_ms)}{text}")
    return "\n".join(lines)


def extract_lyrics(tags) -> Optional[str]:
    """从 ID3 标签中提取歌词，优先同步歌词 SYLT，其次 USLT，最后 TXXX"""
    if tags is None:
        return None

    # 1. 同步歌词 SYLT
    for sylt in tags.getall("SYLT"):
        lrc = sylt_to_lrc(sylt)
        if lrc.strip():
            return lrc

    # 2. 非同步歌词 USLT
    for uslt in tags.getall("USLT"):
        text = getattr(uslt, "text", None)
        if text and text.strip():
            return text

    # 3. 一些软件把歌词放在 TXXX 自定义帧里
    for txxx in tags.getall("TXXX"):
        desc = (txxx.desc or "").lower()
        if desc in ("lyrics", "lyric", "unsyncedlyrics", "同步歌词", "歌词"):
            text = txxx.text
            if isinstance(text, list):
                return "\n".join(text)
            if text:
                return text
    return None


def extract_cover(tags, mp3_path: Path) -> Optional[Path]:
    """提取封面，统一保存为同名 .jpg"""
    if tags is None:
        return None

    covers = tags.getall("APIC")
    if not covers:
        return None

    # 优先 front cover（type == 3）
    front = [c for c in covers if c.type == 3]
    cover = front[0] if front else covers[0]
    data = cover.data
    mime = (cover.mime or "").lower()
    jpg_path = mp3_path.with_suffix(".jpg")

    # 如果原始封面是 PNG，尽量用 Pillow 转成 JPG
    if "png" in mime and HAS_PIL:
        try:
            img = Image.open(io.BytesIO(data))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(jpg_path, "JPEG", quality=90)
            return jpg_path
        except Exception as e:
            print(f"   [警告] PNG 转 JPG 失败: {e}")
    
    # 直接保存（如果是 PNG 且没装 Pillow，存为 .jpg 浏览器一般也能显示）
    jpg_path.write_bytes(data)
    return jpg_path


def process_mp3(mp3_path: Path):
    """处理单个 MP3 文件"""
    try:
        audio = MP3(mp3_path)
        tags = audio.tags
        if tags is None:
            print(f"   [跳过] 无 ID3 标签: {mp3_path.name}")
            return

        # 提取歌词（总是覆盖，确保最新）
        lrc_path = mp3_path.with_suffix(".lrc")
        lyrics = extract_lyrics(tags)
        if lyrics:
            lrc_path.write_text(lyrics, encoding="utf-8")
            print(f"   ✅ 歌词已生成: {lrc_path.name}")
        else:
            print(f"   ⚠️ 未找到内嵌歌词: {mp3_path.name}")

        # 提取封面（总是覆盖）
        cover_path = extract_cover(tags, mp3_path)
        if cover_path:
            print(f"   ✅ 封面已生成: {cover_path.name}")
        else:
            print(f"   ⚠️ 未找到内嵌封面: {mp3_path.name}")

    except Exception as e:
        print(f"   ❌ 处理失败 {mp3_path.name}: {e}")


def main():
    # 1. 确定要扫描的目录
    script_dir = Path(__file__).resolve().parent
    target_dir = script_dir  # 默认当前目录

    # 如果当前目录没有 MP3，但上一级有 static 目录，则自动切换到 static
    if not list(script_dir.glob("*.mp3")) and (script_dir.parent / "static").is_dir():
        target_dir = script_dir.parent / "static"
    
    print(f"🔍 正在扫描目录: {target_dir}")
    
    # 2. 递归查找所有 MP3 文件
    mp3_files = list(target_dir.glob("**/*.mp3"))
    
    if not mp3_files:
        print("❌ 没有找到任何 MP3 文件。")
        print("请确认 MP3 是否放在当前目录或上一级的 static 目录中。")
        return

    print(f"🎵 找到 {len(mp3_files)} 个 MP3 文件，开始处理...\n")

    # 3. 逐个处理
    for mp3_file in mp3_files:
        print(f"正在处理: {mp3_file.name}")
        process_mp3(mp3_file)

    print("\n🎉 全部处理完成！")
    print("请回到项目根目录，运行 python .\\py\\gen_music_list.py 重新生成歌单。")


if __name__ == "__main__":
    main()
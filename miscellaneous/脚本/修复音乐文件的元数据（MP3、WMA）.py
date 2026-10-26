#!/usr/bin/env python
# -*- coding: utf-8 -*-
# --------------------------------------------
# 修复音乐文件的乱码元数据（歌名、艺术家、专辑）
# 直接双击运行，处理当前目录下的 MP3/WMA 文件
# --------------------------------------------

import os
import sys

# 尝试导入 mutagen，如果失败则提示安装
try:
    from mutagen.id3 import ID3, TIT2, TPE1, TALB
except ImportError:
    print("错误：未安装 mutagen 库。")
    print("请先在命令行中运行：pip install mutagen")
    input("\n按回车键退出...")
    sys.exit(1)

# 脚本所在目录（即当前目录）
MUSIC_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_SUFFIXES = [".mp3", ".wma"]


def log_info(msg):
    print(f"[信息] {msg}")


def log_debug(msg):
    # 如果希望看到详细处理过程，可以取消下面这行的注释
    # print(f"[调试] {msg}")
    pass


def main():
    log_info(f"开始修复元数据，扫描目录：{MUSIC_DIR}")
    count = 0
    for file in os.listdir(MUSIC_DIR):
        if not file.lower().endswith(tuple(MUSIC_SUFFIXES)):
            continue

        music_path = os.path.join(MUSIC_DIR, file)
        music_name = os.path.splitext(file)[0]  # 去掉后缀
        fix_meta_to_utf8(music_path, music_name)
        count += 1

    log_info(f"修复完成，共处理 {count} 个文件。")


def fix_meta_to_utf8(music_path, music_name):
    """修复单个文件的元数据"""
    try:
        audio = ID3(music_path)
        album, artist, title = take_metadata(music_name)
        fix_title(audio, title)
        fix_artist(audio, artist)
        fix_album(audio, album)

        audio.save()  # 保存修改后的元数据
        log_debug(f"修复歌曲元数据成功：{music_name}")
    except Exception as e:
        # 正确的元数据因为无法解码报错，无需处理；但可以打印错误方便排查
        log_debug(f"跳过（可能无 ID3 标签或格式不支持）：{music_name}，原因：{e}")


def fix_title(audio, default_title):
    fix_metadata(audio, TIT2, 'TIT2', default_title, '<未知标题>')


def fix_artist(audio, default_artist):
    fix_metadata(audio, TPE1, 'TPE1', default_artist, '<未知艺术家>')


def fix_album(audio, default_album):
    fix_metadata(audio, TALB, 'TALB', default_album, '<未知唱片集>')


def fix_metadata(audio, meta_class, meta_tag, default_value, unknow_value):
    try:
        frames = audio.getall(meta_tag)  # 获取元标签的所有帧
        value = decode_gibberish(frames)
        if value == "" or value == unknow_value:
            value = default_value

        audio.delall(meta_tag)  # 删除元标签的所有帧
        audio.add(meta_class(encoding=3, text=value))  # 添加新的元标签帧
    except Exception:
        pass  # 无法解码或没有该标签，忽略


def decode_gibberish(frames):
    """乱码解码（以 GBK 存储的元数据会乱码）"""
    text = ""
    if frames:
        try:
            text = frames[0].text[0].encode('iso-8859-1').decode('gbk')
            text = text.strip()
        except Exception:
            text = ""
    return text


def take_metadata(music_name):
    """从文件名提取元数据（专辑-艺术家-标题）"""
    title = ""
    artist = ""
    album = ""
    metas = music_name.split('-')

    if len(metas) == 3:
        album = metas[0].strip()
        artist = metas[1].strip()
        title = metas[2].strip()
    elif len(metas) == 2:
        artist = metas[0].strip()
        title = metas[1].strip()
    else:
        title = music_name

    return album, artist, title


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"发生错误：{e}")
    finally:
        input("\n处理完毕，按回车键退出...")
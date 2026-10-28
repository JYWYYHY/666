import shutil
import sys
from pathlib import Path

try:
    from PIL import Image, ImageSequence, UnidentifiedImageError
except ImportError:
    print("缺少 Pillow 库。请先在命令行运行：pip install Pillow")
    input("按回车键退出...")
    sys.exit(1)

# ---------- 可调参数 ----------
QUALITY = 80          # 有损压缩质量 0-100；越高越清晰、体积越大
METHOD = 4            # 编码方法 0-6；越高越慢、压缩越好。动画建议 4，追求体积可改 6
LOSSLESS = False      # True = 无损压缩，体积大但画质完全保留
FORCE_LOOP_INFINITE = True   # True = 所有输出都无限循环；False = 尽量保留原 GIF 的循环设置
MIN_DURATION_MS = 20  # 每帧最小时长（毫秒），避免 0ms 导致部分浏览器行为异常
# --------------------------------


def gif_to_webp(gif_path, webp_path, quality=QUALITY, method=METHOD, lossless=LOSSLESS):
    """
    将单个 GIF 转换为动画 WebP。
    返回帧数。出错时抛出异常。
    """
    with Image.open(gif_path) as im:
        if im.format != 'GIF':
            raise ValueError(f"不是 GIF（实际格式：{im.format}）")

        frames = []
        durations = []

        # ImageSequence.Iterator 会按 GIF 的 disposal 规则合成每一帧，
        # 保证转出来的 WebP 每帧都是完整画面。
        for frame in ImageSequence.Iterator(im):
            # 统一转 RGBA，保证透明通道在每一帧都存在
            frames.append(frame.convert('RGBA'))
            d = frame.info.get('duration', 0) or 0
            durations.append(max(d, MIN_DURATION_MS))

        if not frames:
            raise ValueError("GIF 中没有可用的帧")

        # 循环次数：WebP 中 0 表示无限循环
        if FORCE_LOOP_INFINITE:
            loop = 0
        else:
            loop = im.info.get('loop', 1)  # GIF 没有 loop 扩展时默认只播一次

        webp_path.parent.mkdir(parents=True, exist_ok=True)
        save_kwargs = dict(
            format='WEBP',
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=loop,
            quality=quality,
            method=method,
            minimize_size=True,
        )
        if lossless:
            save_kwargs['lossless'] = True

        frames[0].save(webp_path, **save_kwargs)
        return len(frames)


def convert_folder(input_dir, output_dir):
    input_path = Path(input_dir).resolve()
    output_path = Path(output_dir).resolve()

    if not input_path.is_dir():
        print(f"错误：输入目录 '{input_path}' 不存在。")
        return

    if input_path == output_path:
        print("错误：输入目录与输出目录相同，已中止。")
        return

    converted_count = 0
    copied_webp_count = 0
    skipped_count = 0
    error_count = 0
    total_frames = 0

    for file_path in input_path.rglob('*'):
        if not file_path.is_file():
            continue

        # 跳过输出目录中的文件（防止重复处理）
        if output_path == file_path or output_path in file_path.parents:
            continue

        relative_path = file_path.relative_to(input_path)
        suffix = file_path.suffix.lower()

        # 只处理 .gif 和 .webp，其他扩展名直接忽略
        if suffix not in ('.gif', '.webp'):
            continue

        output_file_path = output_path / relative_path.with_suffix('.webp')

        try:
            with Image.open(file_path) as img:
                real_format = img.format

                # 已经是 WebP：原样复制，不重新编码
                if real_format == 'WEBP':
                    output_file_path.parent.mkdir(parents=True, exist_ok=True)
                    if not output_file_path.exists():
                        shutil.copy2(file_path, output_file_path)
                        print(f"复制 (已是 WebP): {relative_path}")
                    copied_webp_count += 1
                    continue

                # 扩展名是 .gif 但实际不是 GIF（比如改名的 PNG）
                if real_format != 'GIF':
                    print(f"跳过 (扩展名为 .gif 但实际是 {real_format}): {relative_path}")
                    skipped_count += 1
                    continue

            # 真正转换（重新打开一次，避免上面 with 块内状态影响）
            n_frames = gif_to_webp(file_path, output_file_path)
            print(f"转换: {relative_path} -> {output_file_path.relative_to(output_path)} "
                  f"({n_frames} 帧)")
            converted_count += 1
            total_frames += n_frames

        except UnidentifiedImageError:
            print(f"跳过 (不是有效图片): {relative_path}")
            skipped_count += 1
        except (OSError, ValueError) as e:
            print(f"错误: 无法处理 {relative_path} - {e}", file=sys.stderr)
            error_count += 1

    print("\n" + "=" * 40)
    print(f"处理完成。转换: {converted_count} (共 {total_frames} 帧), "
          f"复制WebP: {copied_webp_count}, 跳过: {skipped_count}, 错误: {error_count}")
    print(f"输出目录: {output_path}")


def main():
    double_click_mode = len(sys.argv) == 1

    if double_click_mode:
        input_folder = Path(__file__).resolve().parent
    else:
        input_folder = Path.cwd()

    output_folder = input_folder.parent / f"{input_folder.name}-webp"
    convert_folder(input_folder, output_folder)

    if double_click_mode:
        input("\n按回车键退出...")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"发生未预期的错误: {e}")
        input("按回车键退出...")
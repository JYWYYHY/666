import shutil
import sys
from pathlib import Path

try:
    from PIL import Image, UnidentifiedImageError
except ImportError:
    print("缺少 Pillow 库。请先在命令行运行：pip install Pillow")
    input("按回车键退出...")
    sys.exit(1)

# 禁用 Pillow 内置的模糊阈值，改用下方精确的像素数检查
Image.MAX_IMAGE_PIXELS = None
# 单张图片允许的最大像素数（约 5000 万），防止解压炸弹耗尽内存
MAX_PIXELS = 50_000_000

# 候选扩展名：只有这些扩展名的文件才会被尝试打开验证。
# .gif 保留在这里，以便识别后原样复制。
CANDIDATE_EXTS = (
    '.png', '.jpg', '.jpeg', '.jpe', '.jfif',
    '.tif', '.tiff', '.bmp', '.gif', '.webp',
)

# Pillow 识别出的、我们愿意转码的真实格式。
# GIF 不在此列：GIF 走单独的“原样复制”分支。
SUPPORTED_FORMATS = ('JPEG', 'MPO', 'PNG', 'TIFF', 'BMP', 'WEBP')


def convert_folder(input_dir, output_dir, quality=80):
    """
    递归地将输入目录中的所有图片转换为 WebP。
    GIF 不转换，原样复制到输出目录。
    保持原有的文件夹结构。
    """
    input_path = Path(input_dir).resolve()
    output_path = Path(output_dir).resolve()

    if not input_path.is_dir():
        print(f"错误：输入目录 '{input_path}' 不存在。")
        return

    if input_path == output_path:
        print("错误：输入目录与输出目录相同，已中止。")
        return

    converted_count = 0
    copied_gif_count = 0
    skipped_count = 0
    error_count = 0

    for file_path in input_path.rglob('*'):
        if not file_path.is_file():
            continue

        # 如果输出目录位于输入目录内部，跳过输出目录中的文件
        if output_path == file_path or output_path in file_path.parents:
            continue

        # 先按扩展名快速筛选，避免尝试打开无关文件
        if file_path.suffix.lower() not in CANDIDATE_EXTS:
            continue

        relative_path = file_path.relative_to(input_path)
        output_file_path = output_path / relative_path.with_suffix('.webp')

        try:
            with Image.open(file_path) as img:
                real_format = img.format
                format_name = real_format or '未知'

                # 已经是 WebP：直接复制，不重新编码，避免质量损失
                if real_format == 'WEBP':
                    output_file_path.parent.mkdir(parents=True, exist_ok=True)
                    if not output_file_path.exists():
                        shutil.copy2(file_path, output_file_path)
                        print(f"复制 (已是 WebP): {relative_path}")
                    skipped_count += 1
                    continue

                # GIF：不转换，原样复制，保留动画和原扩展名
                if real_format == 'GIF':
                    gif_output_path = output_path / relative_path
                    gif_output_path.parent.mkdir(parents=True, exist_ok=True)
                    if not gif_output_path.exists():
                        shutil.copy2(file_path, gif_output_path)
                        print(f"复制 (GIF，不转换): {relative_path}")
                    copied_gif_count += 1
                    continue

                # 真实格式不在支持列表（SVG、ICO 等）
                if real_format not in SUPPORTED_FORMATS:
                    print(f"跳过 (不支持的格式 {format_name}): {relative_path}")
                    skipped_count += 1
                    continue

                # 检查像素数，防止超大图片在 load 时耗尽内存
                if img.width * img.height > MAX_PIXELS:
                    print(f"跳过 (像素数过大 {img.width}x{img.height}): {relative_path}")
                    skipped_count += 1
                    continue

                # 强制完整解码，验证文件完整性（截断/损坏会在此抛异常）
                img.load()

                output_file_path.parent.mkdir(parents=True, exist_ok=True)
                img.save(output_file_path, 'WEBP', quality=quality, method=6)
                print(f"转换: {relative_path} -> {output_file_path.relative_to(output_path)}")
                converted_count += 1

        except UnidentifiedImageError:
            print(f"跳过 (不是有效图片): {relative_path}")
            skipped_count += 1
        except Image.DecompressionBombError:
            print(f"跳过 (图片尺寸异常过大): {relative_path}")
            skipped_count += 1
        except (OSError, ValueError) as e:
            print(f"错误: 无法处理 {relative_path} - {e}", file=sys.stderr)
            error_count += 1

    print("\n" + "=" * 40)
    print(f"处理完成。转换: {converted_count}, 复制GIF: {copied_gif_count}, "
          f"跳过: {skipped_count}, 错误: {error_count}")
    print(f"输出目录: {output_path}")


def main():
    # 没有额外参数 = 双击运行
    double_click_mode = len(sys.argv) == 1

    if double_click_mode:
        # 双击：以脚本所在目录为输入目录，质量固定 80
        input_folder = Path(__file__).resolve().parent
        quality_val = 80
    else:
        # 命令行：以当前目录为输入目录，可传质量
        input_folder = Path.cwd()
        try:
            quality_val = int(sys.argv[1])
        except ValueError:
            print("错误：质量参数必须是 0-100 之间的整数。")
            sys.exit(1)
        if not 0 <= quality_val <= 100:
            print("错误：质量参数必须在 0-100 之间。")
            sys.exit(1)

    output_folder = input_folder.parent / f"{input_folder.name}-webp"
    convert_folder(input_folder, output_folder, quality=quality_val)

    if double_click_mode:
        input("\n按回车键退出...")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"发生未预期的错误: {e}")
        input("按回车键退出...")
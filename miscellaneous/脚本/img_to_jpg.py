import shutil
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps, UnidentifiedImageError
except ImportError:
    print("缺少 Pillow 库。请先在命令行运行：pip install Pillow")
    input("按回车键退出...")
    sys.exit(1)

Image.MAX_IMAGE_PIXELS = None
MAX_PIXELS = 50_000_000

# 候选扩展名：不包含 .gif 和 .ico，它们在第一层就被忽略
CANDIDATE_EXTS = (
    '.png', '.jpg', '.jpeg', '.jpe', '.jfif',
    '.tif', '.tiff', '.bmp', '.webp',
)

# 明确跳过的真实格式
SKIP_FORMATS = ('GIF', 'ICO')

# 愿意转成 JPG 的真实格式
SUPPORTED_FORMATS = ('JPEG', 'MPO', 'PNG', 'TIFF', 'BMP', 'WEBP')

JPEG_EXTENSIONS = ('.jpg', '.jpeg', '.jpe', '.jfif')


def prepare_rgb(img):
    """把图片转成 RGB，透明区域填白，CMYK/灰度等统一转换。"""
    if img.mode == 'P':
        img = img.convert('RGBA')
    if img.mode in ('RGBA', 'LA'):
        if img.mode == 'LA':
            img = img.convert('RGBA')
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    if img.mode != 'RGB':
        return img.convert('RGB')
    return img


def convert_folder(input_dir, output_dir, quality=85, reencode=False):
    input_path = Path(input_dir).resolve()
    output_path = Path(output_dir).resolve()

    if not input_path.is_dir():
        print(f"错误：输入目录 '{input_path}' 不存在。")
        return

    if input_path == output_path:
        print("错误：输入目录与输出目录相同，已中止。")
        return

    converted = 0
    copied = 0
    skipped = 0
    errors = 0

    for file_path in input_path.rglob('*'):
        if not file_path.is_file():
            continue

        if output_path == file_path or output_path in file_path.parents:
            continue

        # 第一层：扩展名筛选，.gif / .ico 在此被静默忽略
        if file_path.suffix.lower() not in CANDIDATE_EXTS:
            continue

        relative_path = file_path.relative_to(input_path)
        output_file_path = output_path / relative_path.with_suffix('.jpg')

        try:
            with Image.open(file_path) as img:
                real_format = img.format

                # 真实格式是 GIF / ICO 也跳过
                if real_format in SKIP_FORMATS:
                    print(f"跳过 ({real_format}): {relative_path}")
                    skipped += 1
                    continue

                if real_format not in SUPPORTED_FORMATS:
                    print(f"跳过 (不支持的格式 {real_format}): {relative_path}")
                    skipped += 1
                    continue

                # 已经是 JPG：默认直接复制，避免二次有损压缩
                if real_format == 'JPEG' and not reencode:
                    output_file_path.parent.mkdir(parents=True, exist_ok=True)
                    if not output_file_path.exists():
                        shutil.copy2(file_path, output_file_path)
                        print(f"复制 (已是 JPG): {relative_path}")
                    copied += 1
                    continue

                if img.width * img.height > MAX_PIXELS:
                    print(f"跳过 (像素数过大 {img.width}x{img.height}): {relative_path}")
                    skipped += 1
                    continue

                img.load()
                # 应用 EXIF 方向，避免手机照片转出来方向错乱
                img = ImageOps.exif_transpose(img)
                rgb = prepare_rgb(img)

                output_file_path.parent.mkdir(parents=True, exist_ok=True)
                rgb.save(
                    output_file_path, 'JPEG',
                    quality=quality, optimize=True, progressive=True,
                )
                print(f"转换: {relative_path} -> {output_file_path.relative_to(output_path)}")
                converted += 1

        except UnidentifiedImageError:
            print(f"跳过 (不是有效图片): {relative_path}")
            skipped += 1
        except Image.DecompressionBombError:
            print(f"跳过 (图片尺寸异常过大): {relative_path}")
            skipped += 1
        except (OSError, ValueError) as e:
            print(f"错误: 无法处理 {relative_path} - {e}", file=sys.stderr)
            errors += 1

    print("\n" + "=" * 40)
    print(f"处理完成。转换: {converted}, 复制(已是JPG): {copied}, "
          f"跳过: {skipped}, 错误: {errors}")
    print(f"输出目录: {output_path}")


def main():
    double_click_mode = len(sys.argv) == 1

    quality_val = 85
    reencode = False

    if double_click_mode:
        input_folder = Path(__file__).resolve().parent
    else:
        input_folder = Path.cwd()
        args = sys.argv[1:]
        if '--reencode' in args:
            reencode = True
            args.remove('--reencode')
        if args:
            try:
                quality_val = int(args[0])
            except ValueError:
                print("错误：质量参数必须是 0-100 之间的整数。")
                sys.exit(1)
            if not 0 <= quality_val <= 100:
                print("错误：质量参数必须在 0-100 之间。")
                sys.exit(1)

    output_folder = input_folder.parent / f"{input_folder.name}-jpg"
    print(f"质量: {quality_val}")
    if reencode:
        print("模式: 已是 JPG 的文件也会重新编码")
    convert_folder(input_folder, output_folder, quality=quality_val, reencode=reencode)

    if double_click_mode:
        input("\n按回车键退出...")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n已中断。")
        sys.exit(130)
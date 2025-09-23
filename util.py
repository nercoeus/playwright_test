
import io
from PIL import Image

def low_quality(screenshot):
    # 使用PIL降低图片分辨率，保持尺寸不变
    image = Image.open(io.BytesIO(screenshot))
    
    # 如果图片是RGBA模式，转换为RGB模式以支持JPEG格式
    if image.mode == 'RGBA':
        # 创建白色背景
        rgb_image = Image.new('RGB', image.size, (255, 255, 255))
        # 将RGBA图片粘贴到白色背景上，使用alpha通道作为蒙版
        rgb_image.paste(image, mask=image.split()[-1])  # 使用alpha通道作为蒙版
        image = rgb_image
    elif image.mode not in ['RGB', 'L']:
        # 如果不是RGB或灰度模式，转换为RGB
        image = image.convert('RGB')
    
    # 获取原始尺寸
    original_width, original_height = image.size
    # 降低分辨率到原来的70%，但保持显示尺寸不变
    reduced_width = int(original_width * 0.7)
    reduced_height = int(original_height * 0.7)
    # 先缩小再放大回原尺寸，实现降低分辨率的效果
    image_reduced = image.resize((reduced_width, reduced_height), Image.Resampling.LANCZOS)
    image_final = image_reduced.resize((original_width, original_height), Image.Resampling.LANCZOS)
    
    # 将处理后的图片转换回字节
    output_buffer = io.BytesIO()
    image_final.save(output_buffer, format='JPEG', quality=30, optimize=True)
    screenshot = output_buffer.getvalue()
    return screenshot
                
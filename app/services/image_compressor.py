from PIL import Image
import io

def compress_image(image_bytes: bytes, target_kb: int):
    target_bytes = target_kb * 1024

    img = Image.open(io.BytesIO(image_bytes))

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    img.thumbnail((1500, 1500))

    quality = 95

    while quality > 10:
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        size = buffer.tell()

        if size <= target_bytes:
            buffer.seek(0)
            return buffer

        quality -= 5

    return None

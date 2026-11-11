import os
import io
from fastapi import APIRouter, UploadFile, File, Form
from PIL import Image
from pathlib import Path

router = APIRouter(tags=["Image Compress and save"])

BASE_DIR = Path(os.getcwd())
SAVE_FOLDER = BASE_DIR / "photo" / "updatedphoto"
SAVE_FOLDER.mkdir(parents=True, exist_ok=True)


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


@router.post("/compress-and-save")
async def compress_and_save(
    file: UploadFile = File(...),
    target_kb: int = Form(100)
):

    image_bytes = await file.read()

    compressed = compress_image(image_bytes, target_kb)

    if not compressed:
        return {"error": "Compression failed"}

    save_path = SAVE_FOLDER / file.filename

    with open(save_path, "wb") as f:
        f.write(compressed.read())

    return {
        "message": "Compressed & Saved successfully",
        "saved_path": str(save_path),
        "target_kb": target_kb
    }
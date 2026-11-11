from fastapi import APIRouter, UploadFile, File
import shutil
import os

from app.services.pan_service import extract_pan_data
from app.schemas.pan_schema import PanResponse

router = APIRouter(tags=["PAN Card"])

@router.post("/pan-read/", response_model=PanResponse)
async def read_pan(file: UploadFile = File(...)):

    file_path = f"temp_{file.filename}"

    print("📂 FILENAME:", file.filename)
    print("📦 CONTENT TYPE:", file.content_type)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    print("📏 FILE SIZE:", os.path.getsize(file_path))

    try:
        data = extract_pan_data(file_path)
        return data

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
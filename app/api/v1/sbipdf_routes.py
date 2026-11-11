from fastapi import APIRouter, UploadFile, File
import shutil
import os

from app.services.sbipdfservice import process_sbi_pdf

router = APIRouter()

UPLOAD_FOLDER = "uploads"

@router.post("/sbi-pdf")

async def upload_sbi_pdf(file: UploadFile = File(...)):

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = process_sbi_pdf(file_path)

    return result
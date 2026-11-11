from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import pdfplumber
import pikepdf
import uuid
import shutil
import os

# ❌ prefix हटाया
router = APIRouter(tags=["PDF Splitter"])

BASE_DIR = Path(os.getcwd())
OUTPUT_DIR = BASE_DIR / "ab" / "split_output"
TEMP_DIR = BASE_DIR / "temp"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/split")
async def split_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF allowed")

    temp_id = str(uuid.uuid4())
    temp_path = TEMP_DIR / temp_id
    temp_path.mkdir(parents=True, exist_ok=True)

    result = []

    try:
        input_pdf_path = temp_path / file.filename

        with open(input_pdf_path, "wb") as f:
            f.write(await file.read())

        with pdfplumber.open(input_pdf_path) as text_pdf, pikepdf.open(input_pdf_path) as pdf:
            for i in range(len(text_pdf.pages)):
                file_name = f"page_{i+1}.pdf"
                final_path = OUTPUT_DIR / file_name

                new_pdf = pikepdf.Pdf.new()
                new_pdf.pages.append(pdf.pages[i])
                new_pdf.save(final_path)

                result.append({
                    "page_no": i + 1,
                    "file_name": file_name,
                    "file_path": str(final_path)
                })

    finally:
        shutil.rmtree(temp_path, ignore_errors=True)

    return {
        "total_pages": len(result),
        "data": result
    }
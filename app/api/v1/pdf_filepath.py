from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import zipfile
import shutil
import uuid
import os

router = APIRouter(prefix="/pdf", tags=["PDF Filepath"])

BASE_DIR = Path(os.getcwd())

BASE_OUTPUT_DIR = BASE_DIR / "ab" / "split_output"
TEMP_DIR = BASE_DIR / "temp"

BASE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/read-invoice-with-path")
async def read_invoice_with_path(file: UploadFile = File(...)):

    temp_id = str(uuid.uuid4())
    extract_path = TEMP_DIR / temp_id
    extract_path.mkdir(parents=True, exist_ok=True)

    upload_path = extract_path / file.filename

    with open(upload_path, "wb") as f:
        f.write(await file.read())

    result = []

    if file.filename.lower().endswith(".zip"):
        with zipfile.ZipFile(upload_path, "r") as zip_ref:
            zip_ref.extractall(extract_path)

        pdf_files = extract_path.glob("**/*.pdf")

    elif file.filename.lower().endswith(".pdf"):
        pdf_files = [upload_path]

    else:
        raise HTTPException(status_code=400, detail="Only PDF or ZIP allowed")

    for pdf in pdf_files:
        parts = pdf.stem.split("_")
        invoice_no = (
            f"{parts[0]}/{parts[1]}/{parts[2]}/{parts[3]}"
            if len(parts) >= 4 else ""
        )

        final_path = BASE_OUTPUT_DIR / pdf.name

        # ensure folder exists
        final_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(pdf), final_path)

        result.append({
            "file_name": pdf.name,
            "file_path": str(final_path),
            "invoice_no": invoice_no
        })

    shutil.rmtree(extract_path)

    return {
        "total_files": len(result),
        "data": result
    }
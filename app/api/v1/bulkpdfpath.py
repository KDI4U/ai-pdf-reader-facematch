from fastapi import APIRouter, UploadFile, File
from pathlib import Path
import zipfile
import shutil
import uuid
import os

router = APIRouter(prefix="/pdf", tags=["BULK Filepath"])

BASE_DIR = Path(os.getcwd())

BASE_OUTPUT_DIR = BASE_DIR / "ab" / "split_output"
TEMP_DIR = BASE_DIR / "temp"

BASE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/read-bulk-invoices")
async def read_bulk_invoices(files: list[UploadFile] = File(...)):

    temp_id = str(uuid.uuid4())
    base_temp = TEMP_DIR / temp_id
    base_temp.mkdir(parents=True, exist_ok=True)

    result = []

    for file in files:
        upload_path = base_temp / file.filename

        with open(upload_path, "wb") as f:
            f.write(await file.read())

        if file.filename.lower().endswith(".zip"):
            with zipfile.ZipFile(upload_path, "r") as zip_ref:
                zip_ref.extractall(base_temp)
            pdf_files = base_temp.glob("**/*.pdf")

        elif file.filename.lower().endswith(".pdf"):
            pdf_files = [upload_path]

        else:
            continue

        for pdf in pdf_files:
            parts = pdf.stem.split("_")
            invoice_no = (
                f"{parts[0]}/{parts[1]}/{parts[2]}/{parts[3]}"
                if len(parts) >= 4 else ""
            )

            final_path = BASE_OUTPUT_DIR / pdf.name

            # 🔥 ensure folder exists
            final_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.move(str(pdf), final_path)

            result.append({
                "file_name": pdf.name,
                "file_path": str(final_path),
                "invoice_no": invoice_no
            })

    shutil.rmtree(base_temp)

    return {
        "total_files": len(result),
        "data": result
    }
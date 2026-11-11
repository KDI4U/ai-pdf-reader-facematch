from fastapi import APIRouter, UploadFile, File
from app.services.agreement_service import process_agreement

router = APIRouter(
    prefix="/agreement",
    tags=["Agreement OCR"]
)

@router.post("/extract")
async def extract_agreement(file: UploadFile = File(...)):

    file_path = f"uploads/{file.filename}"

    with open(file_path, "wb") as f:
        f.write(await file.read())

    result = process_agreement(file_path)

    return result
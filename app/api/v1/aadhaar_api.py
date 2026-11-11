from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
import uuid
from typing import Optional

from app.services.aadhaar_service import process, clean_address
from app.schemas.aadhaar_schema import AadhaarResponse, AddressRequest, AddressResponse

router = APIRouter(
    prefix="/aadhaar",
    tags=["Aadhaar"]
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/extract", response_model=AadhaarResponse)
async def extract_aadhaar(
    front_pdf: Optional[UploadFile] = File(None),
    back_pdf: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None)
):
    """
    Extract details from Aadhaar Card.
    Supports:
    - Both front and back files (PDF or Images like JPG/PNG)
    - Single file (e-Aadhaar PDF or combined front+back image) passed as front_pdf or file
    """
    # Identify front and back files
    primary_file = front_pdf or file
    secondary_file = back_pdf

    if not primary_file:
        raise HTTPException(
            status_code=400,
            detail="Please provide at least one file (front_pdf or file) containing the Aadhaar document."
        )

    front_path = None
    back_path = None

    try:
        # Save primary file with unique ID
        ext_front = os.path.splitext(primary_file.filename)[1]
        front_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{ext_front}")
        with open(front_path, "wb") as f:
            shutil.copyfileobj(primary_file.file, f)

        # Save secondary file if provided
        if secondary_file and secondary_file.filename:
            ext_back = os.path.splitext(secondary_file.filename)[1]
            back_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{ext_back}")
            with open(back_path, "wb") as f:
                shutil.copyfileobj(secondary_file.file, f)

        result = process(front_path, back_path)
        return result

    finally:
        # Clean up temporary uploaded files
        if front_path and os.path.exists(front_path):
            try:
                os.remove(front_path)
            except Exception:
                pass
        if back_path and os.path.exists(back_path):
            try:
                os.remove(back_path)
            except Exception:
                pass


@router.post("/clean-address", response_model=AddressResponse)
def clean_address_api(req: AddressRequest):
    """Clean and format raw address text."""
    cleaned = clean_address(req.raw_text)
    return {"cleaned_address": cleaned}
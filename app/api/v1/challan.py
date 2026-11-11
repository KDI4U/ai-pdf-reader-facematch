from fastapi import APIRouter, UploadFile, File
from app.services.pdf_extractor import extract_pf_data

router = APIRouter()

@router.post("/extract-pf-challan")
async def extract_pf_challan(file: UploadFile = File(...)):
    return extract_pf_data(file)

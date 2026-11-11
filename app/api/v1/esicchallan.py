from fastapi import APIRouter, UploadFile, File
from app.services.esic_extractor import extract_pf_data

router = APIRouter(tags=["ESIC Challan"])

@router.post("/extract-esic-challan")
async def extract_esic_challan(file: UploadFile = File(...)):
    return extract_pf_data(file)

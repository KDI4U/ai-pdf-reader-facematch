from fastapi import APIRouter, UploadFile, File
import shutil
import os

# service import
from app.services.rojgaar_snagampdf_service import extract_pdf_data

# schema import
from app.schemas.rojgaar_snagampdf_schema import RojgaarSnagampdfResponse

router = APIRouter(
    prefix="",
    tags=["Rojgaar_Snagam_pdf"]
)


@router.post("/rojgaar-upload/", response_model=RojgaarSnagampdfResponse)
async def upload_rojgaar_pdf(file: UploadFile = File(...)):

    file_path = f"temp_{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        data = extract_pdf_data(file_path)
        return data

    except Exception as e:
        return {"error": str(e)}

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
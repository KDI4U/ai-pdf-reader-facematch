from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os
from app.api.v1.pan_api import router as pan_router
from app.api.v1.aadhaar_api import router as aadhaar_router
from app.api.v1.routes import router as api_router
from app.core.config import setup_cors
from app.api.v1.rojgaar_snagampdf_api import router as rojgaar_router
from app.api.v1.sbipdf_routes import router as sbipdf_routes
from app.api.v1.agreement_route import router as agreement_router
from app.api.v1.face_match_api import router as face_match_router

# Environment check (development / production)
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
is_production = ENVIRONMENT == "production"

app = FastAPI(
    title="HRMS Support Services API",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
)

# CORS
setup_cors(app)

# Upload folder
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Photo folder - use environment variable with fallback
LOCAL_SAVE_FOLDER = os.getenv("PHOTO_FOLDER", "uploads/updatedphoto")
os.makedirs(LOCAL_SAVE_FOLDER, exist_ok=True)

app.mount(
    "/updatedphoto", StaticFiles(directory=LOCAL_SAVE_FOLDER), name="updatedphoto"
)


app.include_router(api_router, prefix="/api/v1")
app.include_router(aadhaar_router, prefix="/api/v1")
app.include_router(rojgaar_router, prefix="/api/v1")
app.include_router(pan_router, prefix="/api/v1")
app.include_router(sbipdf_routes, prefix="/api/v1")
app.include_router(agreement_router)
app.include_router(face_match_router, prefix="/api/v1")

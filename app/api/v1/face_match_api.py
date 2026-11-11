from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import Optional

from app.schemas.face_match_schema import FaceMatchResponse
from app.services.face_match_service import compare_two_images

router = APIRouter(
    prefix="/face-match",
    tags=["Face Match & Verification"]
)


@router.post(
    "/compare-images",
    response_model=FaceMatchResponse,
    summary="Directly compare any two face images",
    description="""
    Upload two face images (e.g. captured photo and profile photo) to detect faces 
    and compare their similarity percentage.
    
    - **file1**: First image file (e.g. captured live photo).
    - **file2**: Second image file (e.g. reference / profile photo).
    - **user_id**: (Optional) Employee ID or Code to include in the output.
    - **threshold**: (Optional) Cosine similarity threshold (default: 0.38).
    """
)
async def compare_images(
    file1: UploadFile = File(..., description="First image file"),
    file2: UploadFile = File(..., description="Second image file"),
    user_id: Optional[str] = Form(None, description="Optional: Employee Id or Code to include in response"),
    threshold: Optional[float] = Form(None, description="Matching threshold (default: 0.38)")
):
    try:
        bytes1 = await file1.read()
        bytes2 = await file2.read()

        if len(bytes1) == 0 or len(bytes2) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both images must be non-empty."
            )

        result = compare_two_images(bytes1, bytes2, user_id=user_id, threshold=threshold)
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error comparing images: {str(e)}"
        )

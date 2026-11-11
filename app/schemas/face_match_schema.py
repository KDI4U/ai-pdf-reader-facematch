from pydantic import BaseModel, Field
from typing import Optional


class FaceMatchDetails(BaseModel):
    uploaded_face_detected: bool = Field(..., description="Whether a face was detected in the uploaded photo")
    profile_face_detected: bool = Field(..., description="Whether a face was detected in the reference profile photo")
    cosine_similarity: Optional[float] = Field(None, description="Cosine similarity score (range -1 to 1, higher is more similar)")
    l2_distance: Optional[float] = Field(None, description="L2 norm distance (lower is more similar)")
    threshold_used: float = Field(..., description="Cosine similarity threshold used for matching")


class FaceMatchResponse(BaseModel):
    status: str = Field(..., description="'success' if faces match, 'unsuccess' if they do not match or detection fails")
    matched: bool = Field(..., description="True if matched, False otherwise")
    user_id: Optional[str] = Field(None, description="User or Employee ID / Code")
    employee_code: Optional[str] = Field(None, description="Employee Code from DB if available (e.g. UIS_PAT_004130)")
    similarity_score: float = Field(..., description="Similarity score normalized between 0.0 and 1.0")
    match_percentage: float = Field(..., description="Match confidence percentage (0.0 to 100.0%)")
    threshold: float = Field(..., description="Cosine similarity threshold applied")
    confidence_level: Optional[str] = Field("HIGH", description="Confidence tier: 'HIGH' (exact match) or 'MEDIUM' (matched with variations like glasses/cap/beard/lighting)")
    variation_note: Optional[str] = Field(None, description="Note on detected variations (e.g. glasses, cap, lighting)")
    message: str = Field(..., description="Result message")
    profile_image_url: Optional[str] = Field(None, description="Azure Blob / reference URL of the stored profile image")
    details: Optional[FaceMatchDetails] = Field(None, description="Detailed detection & metric diagnostics")


# Alias for backward compatibility
EmployeeFaceMatchResponse = FaceMatchResponse

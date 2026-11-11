from pydantic import BaseModel
from typing import Optional


class AadhaarResponse(BaseModel):
    name: Optional[str] = ""
    dob: Optional[str] = ""
    aadhaar: Optional[str] = ""
    gender: Optional[str] = ""
    address: Optional[str] = ""
    pincode: Optional[str] = ""
    father_name: Optional[str] = ""


class AddressRequest(BaseModel):
    raw_text: str


class AddressResponse(BaseModel):
    cleaned_address: str
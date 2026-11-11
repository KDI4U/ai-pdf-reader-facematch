from pydantic import BaseModel

class PanResponse(BaseModel):
    Name: str
    Father_Name: str
    DOB: str
    PAN_Number: str
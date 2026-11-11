from pydantic import BaseModel
from typing import List

# ===== Candidate Model =====
class Candidate(BaseModel):
    Name: str
    Mobile: str
    Email: str
    Father_Name: str
    DOB: str
    Gender: str
    Address: str
    Education: str
    Experience: str
    Applied_Date: str


# ===== Header Model =====
class Header(BaseModel):
    Department: str
    Post: str
    Total_Vacancy: int
    Fresh_Vacancy: int
    Required_Candidate: int


# ===== Final Response Model =====
class RojgaarSnagampdfResponse(BaseModel):
    header: Header
    candidates: List[Candidate]
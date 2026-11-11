from pydantic import BaseModel
from typing import List

class TaxInvoiceResponse(BaseModel):
    reference_numbers: List[str]

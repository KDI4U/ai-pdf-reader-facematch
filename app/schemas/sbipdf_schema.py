from pydantic import BaseModel
from typing import Optional

class SBIPdfSchema(BaseModel):

    Debit_Account_Number: Optional[str]
    Credit_Account_Number: Optional[str]
    Beneficiary_IFSC_Code: Optional[str]
    Product_Type: Optional[str]
    Credit_Amount: Optional[str]
    Beneficiary_Name: Optional[str]
    Customer_Ref_No: Optional[str]
    Date_of_Processing: Optional[str]
    Status: Optional[str]
    UTR_Number: Optional[str]
    Reason: Optional[str]
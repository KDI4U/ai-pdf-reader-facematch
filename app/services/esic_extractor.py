import pdfplumber
import re

def extract_pf_data(file):

    esic_challan_data = {
        "Employer's_Code_No": "",
        "Challan_Period": "",
        "Challan_Number": "",
        "Challan_Created_Date": "",
        "Challan_Submitted_Date": "",
        "Amount_Paid": "",
        "Transaction_Number": ""
    }

    text = ""
    with pdfplumber.open(file.file) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"

    # Employer Code
    m = re.search(r"Employer's Code No.*?(\d+)", text, re.IGNORECASE)
    if m:
        esic_challan_data["Employer's_Code_No"] = m.group(1)

    # Challan Period
    m = re.search(r"Challan Period.*?([A-Za-z]{3}-\d{4})", text, re.IGNORECASE)
    if m:
        esic_challan_data["Challan_Period"] = m.group(1)

    # Challan Number
    m = re.search(r"Challan Number.*?(\d+)", text, re.IGNORECASE)
    if m:
        esic_challan_data["Challan_Number"] = m.group(1)

    # Created Date (remove time)
    m = re.search(r"Challan Created Date.*?(\d{2}-\d{2}-\d{4})", text, re.IGNORECASE)
    if m:
        esic_challan_data["Challan_Created_Date"] = m.group(1)

    # Submitted Date (remove time)
    m = re.search(r"Challan Submitted Date.*?(\d{2}-\d{2}-\d{4})", text, re.IGNORECASE)
    if m:
        esic_challan_data["Challan_Submitted_Date"] = m.group(1)

    # Amount Paid
    m = re.search(r"Amount Paid.*?([\d]+\.\d{2})", text, re.IGNORECASE)
    if m:
        esic_challan_data["Amount_Paid"] = m.group(1)

    # Transaction Number (alphanumeric)
    m = re.search(r"Transaction Number.*?([A-Z0-9]+)", text, re.IGNORECASE)
    if m:
        esic_challan_data["Transaction_Number"] = m.group(1)

    return {"esic_challan_data": esic_challan_data}

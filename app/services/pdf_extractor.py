import pdfplumber
import re

def extract_pf_data(file):
    result = {
        "TRRN": "",
        "CRN": "",
        "Challan_Generated_On": "",
        "Total_Amount": ""
    }

    text = ""
    with pdfplumber.open(file.file) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"

    for line in text.split("\n"):
        line = line.strip()

        # 🔹 TRRN
        if not result["TRRN"] and "TRRN" in line:
            m = re.search(r"\b\d{12,18}\b", line)
            if m:
                result["TRRN"] = m.group()

        # 🔹 Challan Date (DD-MMM-YYYY)
        if not result["Challan_Generated_On"] and "Challan Generated On" in line:
            m = re.search(r"\d{2}-[A-Z]{3}-\d{4}", line)
            if m:
                result["Challan_Generated_On"] = m.group()

        # 🔹 Total Amount (Rs)
        if not result["Total_Amount"] and "Total Amount" in line:
            m = re.search(r"([\d,]+)", line)
            if m:
                result["Total_Amount"] = m.group(1)

        # 🔹 CRN
        if not result["CRN"] and "CRN" in line:
            m = re.search(r"\b\d{12,18}\b", line)
            if m:
                result["CRN"] = m.group()

    return result

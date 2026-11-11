import pdfplumber
import pandas as pd
import json
import os

def process_sbi_pdf(pdf_path):

    all_data = []

    with pdfplumber.open(pdf_path) as pdf:

        for page in pdf.pages:

            tables = page.extract_tables()

            for table in tables:

                if not table:
                    continue

                for row in table[1:]:

                    if not row:
                        continue

                    row = [
                        str(x).replace("\n", " ").strip()
                        if x else ""
                        for x in row
                    ]

                    if len(row) < 10:
                        continue

                    data = {
                        "Debit_Account_Number": row[0],
                        "Credit_Account_Number": row[1],
                        "Beneficiary_IFSC_Code": row[2],
                        "Product_Type": row[3],
                        "Credit_Amount": row[4],
                        "Beneficiary_Name": row[5],
                        "Customer_Ref_No": row[6],
                        "Date_of_Processing": row[7],
                        "Status": row[8],
                        "UTR_Number": row[9],
                        "Reason": row[10] if len(row) > 10 else ""
                    }

                    all_data.append(data)

    # ==========================
    # OUTPUT FOLDER
    # ==========================

    os.makedirs("uploads/output", exist_ok=True)

    # ==========================
    # SAVE EXCEL
    # ==========================

    excel_path = "uploads/output/sbi_output.xlsx"

    df = pd.DataFrame(all_data)

    df.to_excel(excel_path, index=False)

    # ==========================
    # SAVE JSON
    # ==========================

    json_path = "uploads/output/sbi_output.json"

    with open(json_path, "w", encoding="utf-8") as f:

        json.dump(all_data, f, indent=4, ensure_ascii=False)

    return {
        "status": True,
        "total_records": len(all_data),
        "excel_file": excel_path,
        "json_file": json_path,
        "data": all_data
    }
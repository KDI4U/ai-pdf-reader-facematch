import pdfplumber
import re

def extract_pdf_data(pdf_path):

    all_rows = []
    header_data = {}

    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text()

        # ===== HEADER =====
        header_data["Department"] = re.search(r"Department\s*:\s*(.*)", text)
        header_data["Post"] = re.search(r"Post\s*:\s*(.*)", text)
        header_data["Total Vacancy"] = re.search(r"Total Vacancy\s*:\s*(\d+)", text)
        header_data["Fresh Vacancy"] = re.search(r"Fresh Vacancy\s*:\s*(\d+)", text)
        header_data["Required Candidate"] = re.search(r"Required Candidate\s*:\s*(\d+)", text)

        for k in header_data:
            header_data[k] = header_data[k].group(1) if header_data[k] else ""

        # ===== TABLE =====
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table[1:]:
                    all_rows.append(row)

    candidates = []

    for row in all_rows:
        try:
            name_block = str(row[1])

            name = re.search(r"नाम[:\- ]*(.*)", name_block)
            name = name.group(1).strip() if name else ""

            mobile = re.search(r"\d{10}", name_block)
            mobile = mobile.group(0) if mobile else ""

            email = re.search(r"[\w\.-]+@[\w\.-]+", name_block)
            email = email.group(0) if email else ""

            father = str(row[2]).replace("\n", " ").strip()

            candidates.append({
                "Name": name,
                "Mobile": mobile,
                "Email": email,
                "Father_Name": father,
                "DOB": str(row[3]),
                "Gender": str(row[4]),
                "Address": str(row[5]).replace("\n", " "),
                "Education": str(row[6]).replace("\n", " "),
                "Experience": str(row[7]).replace("\n", " "),
                "Applied_Date": str(row[8])
            })

        except:
            continue

    return {
        "header": {
            "Department": header_data["Department"],
            "Post": header_data["Post"],
            "Total_Vacancy": int(header_data["Total Vacancy"] or 0),
            "Fresh_Vacancy": int(header_data["Fresh Vacancy"] or 0),
            "Required_Candidate": int(header_data["Required Candidate"] or 0)
        },
        "candidates": candidates
    }
from fastapi import APIRouter, UploadFile, File
import pdfplumber
import re
import io

router = APIRouter(prefix="/invoice", tags=["Invoice"])


# 🔥 DATE FORMAT (100% safe)
def format_date(d):
    try:
        d = d.upper()
        d = d.replace("/", "-").replace(" ", "-")

        match = re.search(r"(\d{1,2})-?([A-Z]{3})-?(\d{2,4})", d)
        if not match:
            return d

        day = int(match.group(1))
        month_str = match.group(2)
        year = match.group(3)

        months = {
            "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
            "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
            "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"
        }

        month = months.get(month_str, "01")

        if len(year) == 2:
            year = "20" + year

        return f"{day:02d}-{month}-{year}"

    except:
        return d


@router.post("/read")
async def invoice_read(file: UploadFile = File(...)):

    invoice_details = []

    pdf_bytes = await file.read()

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):

            text = page.extract_text() or ""

            # 🔥 CLEAN TEXT
            text = text.replace("\n", " ")
            text = re.sub(r'\(cid:\d+\)', '', text)
            text = re.sub(r'\s+', ' ', text)

            print("\n===== PAGE TEXT =====\n", text[:500])  # 🔥 DEBUG

            # ✅ STEP 1: Find ALL invoice numbers
            invoices = re.findall(r"UIS/[A-Z]+/\d{2}-\d{2}/\d+", text)

            if not invoices:
                continue

            invoice_no = invoices[0]
            reference_no = invoices[1] if len(invoices) > 1 else None

            # ✅ STEP 2: Find ALL dates
            dates = re.findall(r"\d{1,2}[-/ ]?[A-Za-z]{3}[-/ ]?\d{2,4}", text)

            invoice_date = format_date(dates[0]) if len(dates) > 0 else None
            reference_date = format_date(dates[1]) if len(dates) > 1 else None

            # ✅ STEP 3: Amount
            amount_match = re.search(
                r'Total.*?(-?[\d,]+\.\d{2})',
                text,
                re.IGNORECASE
            )

            amount = float(amount_match.group(1).replace(",", "")) if amount_match else None

            invoice_details.append({
                "page": page_no,
                "invoice_no": invoice_no,
                "invoice_date": invoice_date,
                "reference_no": reference_no,
                "reference_date": reference_date,
                "amount": amount
            })

    return {
        "status": "success",
        "data": invoice_details
    }
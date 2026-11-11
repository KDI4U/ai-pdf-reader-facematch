from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import pdfplumber
import pikepdf
import re
import uuid
import shutil
import os
import platform
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from datetime import datetime

# OCR
from pdf2image import convert_from_path
import pytesseract
import cv2
import numpy as np

# 🔥 Tesseract path
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

router = APIRouter(tags=["PDF Splitter"])

BASE_DIR = Path(os.getcwd())
OUTPUT_DIR = BASE_DIR / "ab" / "split_output"
TEMP_DIR = BASE_DIR / "temp"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# 🔥 DATE FORMAT
# =========================
def format_date(date_str):
    try:
        if not date_str:
            return None

        print("RAW DATE:", date_str)

        date_str = date_str.upper().strip()

        # 🔥 OCR FIXES
        date_str = date_str.replace("O", "0")
        date_str = date_str.replace("I", "1")
        date_str = date_str.replace("L", "1")

        # 🔥 CLEAN
        date_str = date_str.replace("/", "-").replace(" ", "-")

        # 🔥 VALID DATE MATCH ONLY
        match = re.search(r"(\d{1,2})-([A-Z]{3})-(\d{2})", date_str)

        if not match:
            return None

        day = int(match.group(1))
        mon = match.group(2)
        year = int(match.group(3))

        # 🔥 VALIDATION (MOST IMPORTANT)
        if day > 31 or year > 50:
            print("❌ INVALID DATE DETECTED")
            return None

        month_map = {
            "JAN":"01","FEB":"02","MAR":"03","APR":"04",
            "MAY":"05","JUN":"06","JUL":"07","AUG":"08",
            "SEP":"09","OCT":"10","NOV":"11","DEC":"12"
        }

        month = month_map.get(mon)

        return f"{day:02d}-{month}-20{year}"

    except Exception as e:
        print("DATE ERROR:", e)
        return None


# =========================
# 🔥 OCR FUNCTION
# =========================
def ocr_page(pdf_path, page_no):
    images = convert_from_path(pdf_path, first_page=page_no, last_page=page_no, dpi=300)
    img = np.array(images[0])

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 2
    )

    text = pytesseract.image_to_string(thresh, config='--oem 3 --psm 6')
    return text


# =========================
# 🔥 EXTRACT DATA (FINAL FIXED)
# =========================
def extract_invoice_data(text):
    if not text:
        return None, None, None, None, None

    text = text.upper().replace("|", "/")
    text = re.sub(r'\s+', ' ', text)

    # 🔥 INVOICE (FIRST)
    invoice_blocks = re.findall(
        r"(UIS/[A-Z0-9]{1,5}/\d{2}-\d{2}/\d+)\s+(\d{1,2}-[A-Z]{3}-\d{2})",
        text
    )

    invoice_no = None
    invoice_date = None

    if invoice_blocks:
        invoice_no = invoice_blocks[0][0]
        invoice_date = format_date(invoice_blocks[0][1])

    # 🔥 REFERENCE (LAST)
    ref_blocks = re.findall(
        r"(UIS/[A-Z0-9]{1,5}/\d{2}-\d{2}/\d+)\s*DT\.?\s*(\d{1,2}-[A-Z]{3}-\d{2})",
        text
    )

    reference_no = None
    reference_date = None

    if ref_blocks:
        reference_no = ref_blocks[-1][0]
        reference_date = format_date(ref_blocks[-1][1])

    # 🔥 AMOUNT
    total_match = re.search(r"TOTAL.*?([\d,]+\.\d{2})", text)

    if total_match:
        amount = float(total_match.group(1).replace(",", ""))
    else:
        fallback = re.findall(r"[\d,]+\.\d{2}", text)
        amount = float(fallback[-1].replace(",", "")) if fallback else None

    return invoice_no, reference_no, invoice_date, reference_date, amount


# =========================
# 🔥 PROCESS PAGE
# =========================
def process_page(data):
    i, text, pdf_path = data

    if not text or not text.strip():
        text = ocr_page(pdf_path, i + 1)

    inv, ref, inv_dt, ref_dt, amt = extract_invoice_data(text)

    if not inv:
        return None

    return (i, inv, ref, inv_dt, ref_dt, amt)


# =========================
# 🔥 MAIN API
# =========================
@router.post("/split-and-rename")
async def split_and_rename_pdf(file: UploadFile = File(...)):

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF allowed")

    temp_id = str(uuid.uuid4())
    temp_path = TEMP_DIR / temp_id
    temp_path.mkdir(parents=True, exist_ok=True)

    result = []

    try:
        input_pdf_path = temp_path / file.filename

        # save file
        content = await file.read()
        with open(input_pdf_path, "wb") as f:
            f.write(content)

        # extract text
        with pdfplumber.open(input_pdf_path) as pdf:
            page_texts = [
                (i, page.extract_text() or "", input_pdf_path)
                for i, page in enumerate(pdf.pages)
            ]

        # process pages
        with ThreadPoolExecutor() as executor:
            valid_pages = [r for r in executor.map(process_page, page_texts) if r]

        # split pages
        with pikepdf.open(input_pdf_path) as pdf:
            for i, inv, ref, inv_dt, ref_dt, amt in valid_pages:
                new_pdf = pikepdf.Pdf.new()
                new_pdf.pages.append(pdf.pages[i])

                buf = BytesIO()
                new_pdf.save(buf)
                pdf_bytes = buf.getvalue()

                filename = (ref or inv).replace("/", "_") + ".pdf"

                file_path = OUTPUT_DIR / filename
                with open(file_path, "wb") as f:
                    f.write(pdf_bytes)

                item = {
                    "page_no": i + 1,
                    "invoice_no": inv,
                    "reference_no": ref,
                    "invoice_date": inv_dt,
                    "reference_date": ref_dt,
                    "amount": amt,
                    "file_name": filename,
                    "file_path": str(file_path)
                }

                result.append(item)

    finally:
        shutil.rmtree(temp_path, ignore_errors=True)

    return {
        "total_pages": len(result),
        "data": result
    }
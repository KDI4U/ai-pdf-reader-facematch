from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pathlib import Path
import pdfplumber
import pikepdf
import re
import uuid
import shutil
import base64
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

router = APIRouter(tags=["PDF Splitter Base64"])

BASE_DIR = Path(os.getcwd())
OUTPUT_DIR = BASE_DIR / "ab" / "split_output"
TEMP_DIR = BASE_DIR / "temp"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# 🔥 PATTERNS
# =========================
UIS_PATTERN = re.compile(r"UIS/[A-Z0-9]{1,5}/\d{2}-\d{2}/\d+", re.IGNORECASE)
DATE_PATTERN = re.compile(r"\d{1,2}[-/][A-Za-z]{3,}[-/]\d{2,4}", re.IGNORECASE)


# =========================
# 🔥 DATE FORMAT
# =========================
def format_date(date_str):
    try:
        date_str = date_str.replace("/", "-").strip()
        dt = datetime.strptime(date_str, "%d-%b-%y")
        return dt.strftime("%d-%m-%Y")
    except:
        return date_str


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
# 🔥 EXTRACT DATA
# =========================
def extract_invoice_data(text):
    if not text:
        return None, None, None

    text = text.upper().replace("|", "/")
    text = re.sub(r'\s+', ' ', text)

    all_uis = UIS_PATTERN.findall(text)

    invoice_no = None
    reference_no = None

    if len(all_uis) >= 2:
        invoice_no = all_uis[0]
        reference_no = all_uis[1]
    elif len(all_uis) == 1:
        invoice_no = all_uis[0]
        reference_no = all_uis[0]

    date_match = DATE_PATTERN.search(text)
    date = format_date(date_match.group()) if date_match else None

    return invoice_no, reference_no, date


# =========================
# 🔥 PROCESS PAGE
# =========================
def process_page(data):
    i, text, pdf_path = data

    if not text or not text.strip():
        text = ocr_page(pdf_path, i + 1)

    inv, ref, dt = extract_invoice_data(text)

    if not inv:
        return None

    return (i, inv, ref, dt)


# =========================
# 🔥 MAIN API
# =========================
@router.post("/split-and-rename")
async def split_and_rename_pdf(
    file: UploadFile = File(...),
    include_base64: bool = Query(False)
):
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

        # extract text using pdfplumber
        with pdfplumber.open(input_pdf_path) as pdf:
            page_texts = [
                (i, page.extract_text() or "", input_pdf_path)
                for i, page in enumerate(pdf.pages)
            ]

        # process pages (parallel)
        with ThreadPoolExecutor() as executor:
            valid_pages = [r for r in executor.map(process_page, page_texts) if r]

        # split pages
        with pikepdf.open(input_pdf_path) as pdf:
            for i, inv, ref, dt in valid_pages:
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
                    "invoice_date": dt,
                    "file_name": filename,
                    "file_path": str(file_path)
                }

                if include_base64:
                    item["pdf_base64"] = base64.b64encode(pdf_bytes).decode()

                result.append(item)

    finally:
        shutil.rmtree(temp_path, ignore_errors=True)

    return {
        "total_pages": len(result),
        "data": result
    }
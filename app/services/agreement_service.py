from pdf2image import convert_from_path
import pytesseract
import numpy as np
import cv2
import re
import os
import platform

# Cross-platform poppler path
POPPLER_PATH = None
if platform.system() == "Windows":
    POPPLER_PATH = os.getenv("POPPLER_PATH", r"C:\poppler-25.07.0\Library\bin")
# On Linux/Docker, poppler-utils is in PATH, so no path needed

# Tesseract path (Windows only; on Linux/Docker tesseract is in PATH)
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )


def process_agreement(pdf_path):

    # ==========================
    # PDF TO IMAGE
    # ==========================
    pages = convert_from_path(
        pdf_path,
        dpi=300,
        poppler_path=POPPLER_PATH
    )

    # ==========================
    # OCR
    # ==========================
    all_text = ""

    for page in pages:

        img = np.array(page)

        text = pytesseract.image_to_string(
            img,
            lang="eng"
        )

        all_text += "\n" + text

    # Debug
    print("=" * 100)
    print(all_text[:5000])
    print("=" * 100)

    # ==========================
    # AGREEMENT DETAILS
    # ==========================
    result = {}

    # Certificate No



    m = re.search(
        r'Certificate\s*No\..*?:\s*([^\s]+)',
        all_text,
        re.I
    )

    certificate_no = m.group(1).strip() if m else ""

        # Remove leading junk
    certificate_no = re.sub(r'^[^A-Z0-9]+', '', certificate_no)

        # Fix common OCR mistakes around IN-DL
    certificate_no = re.sub(
            r'^IN[-_\s]*S?D?L',
            'IN-DL',
            certificate_no,
            flags=re.I
        )

    result["certificate_no"] = certificate_no












    # Certificate Issued Date
    m = re.search(
        r'Certificate Issued Date\s*.*?(\d{2}-[A-Za-z]{3}-\d{4}.*?[AP]M)',
        all_text,
        re.I
    )
    result["certificate_issued_date"] = m.group(1) if m else ""

 

    # Account Reference
    m = re.search(
        r'Account Reference\s*:?(.+)',
        all_text,
        re.I
    )
    result["account_reference"] = (
        m.group(1).replace("'", "").strip()
        if m else ""
    )

    # Description
    m = re.search(
        r'Description of Document\s*=?\s*:(.+)',
        all_text,
        re.I
    )
    result["description"] = (
        m.group(1).replace(":", "").strip()
        if m else ""
    )

    # Consideration Price
    m = re.search(
        r'Consideration Price.*?:\s*([\d,]+)',
        all_text,
        re.I
    )
    result["consideration_price"] = (
        m.group(1)
        if m else ""
    )

    # First Party
    m = re.search(
        r'First Party.*?:\s*(.+)',
        all_text,
        re.I
    )

    result["first_party"] = (
        m.group(1)
        .replace("-", " ")
        .replace(" eu", "")
        .strip()
        if m else ""
    )

    # Second Party
    m = re.search(
        r'Second Party.*?:\s*(.+)',
        all_text,
        re.I
    )

    result["second_party"] = (
        m.group(1).strip()
        if m else ""
    )

    # Stamp Duty Paid By
    m = re.search(
        r'Stamp Duty Paid By.*?:\s*(.+)',
        all_text,
        re.I
    )

    result["stamp_duty_paid_by"] = (
        m.group(1).strip()
        if m else ""
    )

    # Stamp Duty Amount
    m = re.search(
        r'Stamp Duty Amount.*?:\s*(\d+)',
        all_text,
        re.I
    )

    result["stamp_duty_amount"] = (
        m.group(1)
        if m else ""
    )

    # Agreement Date
    m = re.search(
        r'entered on this\s*(\d+).*?day of\s*([A-Za-z]+).*?(\d{4})',
        all_text,
        re.I | re.S
    )

    if m:
        result["agreement_date"] = (
            f"{m.group(1)} {m.group(2)} {m.group(3)}"
        )
    else:
        result["agreement_date"] = ""

    # Agreement Place
    m = re.search(
        r'entered on this.*?at\s*([A-Za-z ,]+)',
        all_text,
        re.I | re.S
    )

    result["agreement_place"] = (
        m.group(1).strip()
        if m else ""
    )

    # Model Type
    m = re.search(
        r'(collect\s*&\s*pay\s*model)',
        all_text,
        re.I
    )

    result["model_type"] = (
        m.group(1).lower()
        if m else ""
    )

    # Service Fee
    m = re.search(
        r'Service Fee.*?(\d+%)',
        all_text,
        re.I | re.S
    )

    result["service_fee"] = (
        m.group(1)
        if m else ""
    )

    # Expense Processing Fee
    m = re.search(
        r'charge Service Fee\s*@\s*(\d+%)',
        all_text,
        re.I | re.S
    )

    result["expense_processing_fee"] = (
        m.group(1)
        if m else ""
    )

    # ==========================
    # SIGNATURE DETECTION
    # ==========================
    signature_details = []

    def detect_signature(region):

        hsv = cv2.cvtColor(
            region,
            cv2.COLOR_RGB2HSV
        )

        lower_blue = np.array([90, 40, 40])
        upper_blue = np.array([140, 255, 255])

        mask = cv2.inRange(
            hsv,
            lower_blue,
            upper_blue
        )

        blue_pixels = cv2.countNonZero(mask)

        return blue_pixels > 500

    for page_no, page in enumerate(pages, start=1):

        img = np.array(page)

        h, w = img.shape[:2]

        footer = img[int(h * 0.80):h, :]

        left_region = footer[:, :int(w * 0.35)]
        right_region = footer[:, int(w * 0.65):]

        left_sign = detect_signature(left_region)
        right_sign = detect_signature(right_region)

        if left_sign and right_sign:
            status = "Both Present"
        elif left_sign:
            status = "Right Missing"
        elif right_sign:
            status = "Left Missing"
        else:
            status = "Both Missing"

        signature_details.append({
            "page_no": page_no,
            "left_signature": "Yes" if left_sign else "No",
            "right_signature": "Yes" if right_sign else "No",
            "status": status
        })

    # ==========================
    # FINAL RESULT
    # ==========================
    final_result = {
        "agreement_details": result,
        "signature_details": signature_details
    }

    return final_result
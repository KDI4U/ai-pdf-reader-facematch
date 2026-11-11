import pytesseract
import cv2
import re
import numpy as np
import fitz  # PyMuPDF
import os
import platform
import shutil
import xml.etree.ElementTree as ET
from PIL import Image

# =========================================================
# 1. Cross-platform Tesseract Configuration
# =========================================================
def configure_tesseract():
    if platform.system() == "Windows":
        # 1. Environment variable
        env_path = os.getenv("TESSERACT_PATH")
        if env_path and os.path.exists(env_path):
            pytesseract.pytesseract.tesseract_cmd = env_path
            return

        # 2. Which in PATH
        which_path = shutil.which("tesseract")
        if which_path:
            pytesseract.pytesseract.tesseract_cmd = which_path
            return

        # 3. Common Windows install locations
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        ]
        for p in common_paths:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
                return

configure_tesseract()

# =========================================================
# 2. EasyOCR Lazy Loader
# =========================================================
_easyocr_reader = None

def get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        try:
            import easyocr
            _easyocr_reader = easyocr.Reader(['en'], gpu=False)
        except Exception as e:
            print(f"[AadhaarService] Warning: Could not initialize EasyOCR: {e}")
    return _easyocr_reader

# =========================================================
# 3. Stop Words & Regex Patterns
# =========================================================
STOP_WORDS = {
    'government', 'govt', 'india', 'bharat', 'sarkar', 'aadhaar', 'uidai',
    'unique', 'identification', 'authority', 'enrolment', 'enrollment',
    'mera', 'meri', 'pehchan', 'help', '1947', 'www', 'signature',
    'valid', 'digitally', 'signed', 'download', 'issue', 'date', 'male',
    'female', 'transgender', 'dob', 'birth', 'yob', 'year', 'address',
    'father', 'mother', 'husband', 'wife', 'vid', 'electronically', 'verified',
    'proof', 'identity', 'citizenship', 'card', 'resident', 'tax', 'department',
    'house', 'flat', 'floor', 'street', 'road', 'sector', 'block', 'nagar',
    'colony', 'village', 'district', 'state', 'pincode', 'pin', 'near', 'post',
    'office', 'tehsil', 'lane', 'marg', 'care', 'hno', 'w/o', 's/o', 'd/o', 'c/o',
    'order', 'court', 'validity', 'issued', 'information', 'online', 'portal',
    'mera', 'meri', 'aam', 'aadmi', 'adhikar'
}

# =========================================================
# 4. QR Code Extractor
# =========================================================
def extract_qr_data(img_bgr):
    """Attempt to detect and decode UIDAI XML QR code from an image."""
    try:
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(img_bgr)
        if data and ("<PrintLetterBarcodeData" in data or "<?xml" in data):
            # Parse XML
            xml_start = data.find("<PrintLetterBarcodeData")
            if xml_start != -1:
                xml_str = data[xml_start:]
                xml_end = xml_str.find("/>")
                if xml_end != -1:
                    xml_str = xml_str[:xml_end + 2]
                root = ET.fromstring(xml_str)
                uid = root.attrib.get('uid', '')
                if len(uid) == 12:
                    uid = f"{uid[:4]} {uid[4:8]} {uid[8:]}"

                raw_gender = root.attrib.get('gender', '')
                gender = "Male" if raw_gender.upper() == "M" else ("Female" if raw_gender.upper() == "F" else raw_gender)

                dob = root.attrib.get('dob') or root.attrib.get('yob', '')

                # Build address
                addr_parts = []
                for k in ['co', 'house', 'street', 'lm', 'loc', 'vtc', 'po', 'dist', 'subdist', 'state', 'pc']:
                    v = root.attrib.get(k)
                    if v:
                        addr_parts.append(v)
                address = ", ".join(addr_parts)
                pincode = root.attrib.get('pc', '')
                father_name = root.attrib.get('co', '').replace('S/O:', '').replace('C/O:', '').replace('W/O:', '').replace('D/O:', '').strip()

                return {
                    "Name": root.attrib.get('name', ''),
                    "DOB": dob,
                    "Gender": gender,
                    "Aadhaar": uid,
                    "Address": address,
                    "Pincode": pincode,
                    "Father_Name": father_name
                }
    except Exception as e:
        print(f"[AadhaarService] QR decode exception: {e}")
    return None

# =========================================================
# 5. Image & PDF OCR Loading
# =========================================================
def enhance_image(img_bgr):
    """Preprocess image with CLAHE contrast enhancement for OCR."""
    h, w = img_bgr.shape[:2]
    # Resize small images to standard width for OCR
    if w < 1200:
        scale = 1600 / max(w, 1)
        img_bgr = cv2.resize(img_bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    return enhanced

def run_tesseract_with_rotations(img_bgr):
    """Run Tesseract with rotation fallback (0, 90, 180, 270) to handle sideways images."""
    best_text = ""
    rotations = [
        (0, img_bgr),
        (90, lambda img: cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)),
        (180, lambda img: cv2.rotate(img, cv2.ROTATE_180)),
        (270, lambda img: cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE))
    ]

    for angle, rot_func in rotations:
        cur_img = img_bgr if angle == 0 else rot_func(img_bgr)
        enhanced = enhance_image(cur_img)
        t = pytesseract.image_to_string(enhanced, config='--oem 3 --psm 3')

        if not best_text or len(t) > len(best_text):
            best_text = t

        # If we found an Aadhaar number or DOB, this orientation is definitely correct
        if re.search(r'\b\d{4}\s\d{4}\s\d{4}\b', t) or re.search(r'\b\d{2}/\d{2}/\d{4}\b', t):
            return t

    return best_text

def run_easyocr(img_bgr):
    """Fallback OCR using EasyOCR deep learning model."""
    reader = get_easyocr_reader()
    if not reader:
        return ""
    try:
        results = reader.readtext(img_bgr)
        lines = []
        for (_, text, prob) in results:
            if prob > 0.3:
                lines.append(text)
        return "\n".join(lines)
    except Exception as e:
        print(f"[AadhaarService] EasyOCR exception: {e}")
        return ""

def ocr_pdf(file_path):
    """
    Extracts text from PDF or Image file.
    Supports digital text, high-resolution rendering, Tesseract, and EasyOCR fallback.
    """
    if not os.path.exists(file_path):
        return ""

    text = ""
    is_pdf = file_path.lower().endswith(".pdf")

    # Step 1: If it's a PDF, first check for embedded digital text
    if is_pdf:
        try:
            doc = fitz.open(file_path)
            digital_text = ""
            for page in doc:
                digital_text += page.get_text() + "\n"

            # Check if digital text contains meaningful Aadhaar information
            if len(digital_text.strip()) > 50 and any(k in digital_text.lower() for k in ["government", "india", "aadhaar", "dob", "birth", "address", "uidai"]):
                return digital_text
        except Exception as e:
            print(f"[AadhaarService] Digital text check failed: {e}")

    # Step 2: Render pages or load images for OCR
    images = []
    if is_pdf:
        try:
            doc = fitz.open(file_path)
            for page in doc:
                # 300 DPI high resolution rendering
                pix = page.get_pixmap(dpi=300, colorspace=fitz.csRGB)
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
                img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                images.append(img_bgr)
        except Exception as e:
            print(f"[AadhaarService] PyMuPDF render failed: {e}")
    else:
        # Image file
        try:
            img = cv2.imread(file_path)
            if img is None:
                pil_img = Image.open(file_path).convert('RGB')
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            if img is not None:
                images.append(img)
        except Exception as e:
            print(f"[AadhaarService] Image load failed: {e}")

    # Step 3: Run OCR on extracted image(s)
    for img_bgr in images:
        ocr_out = run_tesseract_with_rotations(img_bgr)
        text += ocr_out + "\n"

        # If Tesseract didn't find Aadhaar number or DOB, run EasyOCR as complementary source
        if not re.search(r'\b(?:\d{4}|[Xx\*]{4})\s(?:\d{4}|[Xx\*]{4})\s\d{4}\b', ocr_out):
            easy_out = run_easyocr(img_bgr)
            text += "\n" + easy_out + "\n"

    return text

# =========================================================
# 6. Entity Extractors
# =========================================================
def extract_aadhaar_number(text):
    """Extract standard or masked 12-digit Aadhaar number, ignoring 16-digit VIDs."""
    # Remove Virtual ID (VID) patterns
    text_cleaned = re.sub(r'VID\s*[:\-]?\s*\d{4}\s?\d{4}\s?\d{4}\s?\d{4}', '', text, flags=re.IGNORECASE)
    text_cleaned = re.sub(r'\b\d{4}\s\d{4}\s\d{4}\s\d{4}\b', '', text_cleaned)

    # 1. Standard 12-digit: 1234 5678 9012 or 1234-5678-9012
    matches = re.findall(r'\b\d{4}[\s\-]\d{4}[\s\-]\d{4}\b', text_cleaned)
    if matches:
        return matches[0].replace('-', ' ')

    # 2. Masked Aadhaar: XXXX XXXX 1234, **** **** 1234
    masked = re.findall(r'\b[Xx\*\.]{4}[\s\-][Xx\*\.]{4}[\s\-]\d{4}\b', text_cleaned)
    if masked:
        return masked[0].replace('-', ' ')

    # 3. Continuous 12 digits: 123456789012
    cont = re.findall(r'\b\d{12}\b', text_cleaned)
    if cont:
        d = cont[0]
        return f"{d[:4]} {d[4:8]} {d[8:]}"

    # 4. OCR 0 vs O confusion: e.g. 1234 5678 9O12
    ocr_m = re.findall(r'\b[0-9O]{4}[\s\-][0-9O]{4}[\s\-][0-9O]{4}\b', text_cleaned)
    for m in ocr_m:
        cleaned = m.replace('O', '0').replace('-', ' ')
        digits = re.sub(r'\D', '', cleaned)
        if len(digits) == 12:
            return f"{digits[:4]} {digits[4:8]} {digits[8:]}"

    return ""

def extract_dob(text):
    """Extract Date of Birth (DD/MM/YYYY) or Year of Birth."""
    # 1. Explicit DOB / Birth / Janm Tithi
    m = re.search(r'(?:DOB|D\.O\.B|Birth|जन्म\s*तिथि|जन्म\s*तारीख)[\s\:\/\.\-]*([0-3]?\d[\/\.\-][0-1]?\d[\/\.\-]\d{4})', text, re.IGNORECASE)
    if m:
        return m.group(1).replace('-', '/').replace('.', '/')

    # 2. General date pattern anywhere
    date_matches = re.findall(r'\b([0-3]\d[\/\.\-][0-1]\d[\/\.\-]\d{4})\b', text)
    if date_matches:
        for d in date_matches:
            parts = re.split(r'[\/\.\-]', d)
            if len(parts) == 3:
                try:
                    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                    if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2030:
                        return f"{day:02d}/{month:02d}/{year}"
                except:
                    pass

    # 3. Year of birth (YOB) pattern
    yob_m = re.search(r'(?:Year\s*of\s*Birth|YOB|जन्म\s*वर्ष)[\s\:\/\.\-]*([12]\d{3})\b', text, re.IGNORECASE)
    if yob_m:
        return yob_m.group(1)

    return ""

def extract_gender(text):
    """Extract gender from text (Male / Female / Transgender)."""
    text_lower = text.lower()
    if re.search(r'\b(female|महिला)\b', text_lower):
        return "Female"
    elif re.search(r'\b(transgender)\b', text_lower):
        return "Transgender"
    elif re.search(r'\b(male|पुरुष)\b', text_lower):
        return "Male"
    return ""

def clean_name_candidate(line):
    line = re.sub(r'[^A-Za-z\s\.]', ' ', line)
    words = [w for w in line.split() if len(w) > 1]
    return ' '.join(words)

def is_valid_name(candidate):
    if not candidate or len(candidate) < 3 or len(candidate) > 40:
        return False
    words = candidate.lower().split()
    if not words or len(words) > 5:
        return False
    for w in words:
        if w in STOP_WORDS:
            return False
        if not re.match(r'^[A-Za-z\.]+$', w):
            return False
    if not any(len(w) >= 3 for w in words):
        return False
    return True

def extract_name(text):
    """Extract resident's name using multi-anchor strategies."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Strategy 1: Look at lines right above DOB / Birth
    for i, line in enumerate(lines):
        if re.search(r'\b(DOB|D\.O\.B|Birth|जन्म|YOB|Year\s*of\s*Birth)\b', line, re.IGNORECASE):
            for j in range(i - 1, max(i - 6, -1), -1):
                cleaned = clean_name_candidate(lines[j])
                if is_valid_name(cleaned):
                    return cleaned

    # Strategy 2: Look at lines right above Gender
    for i, line in enumerate(lines):
        if re.search(r'\b(Male|Female|Transgender|पुरुष|महिला)\b', line, re.IGNORECASE):
            for j in range(i - 1, max(i - 6, -1), -1):
                cleaned = clean_name_candidate(lines[j])
                if is_valid_name(cleaned):
                    return cleaned

    # Strategy 3: Look after 'To' (in e-Aadhaar top section)
    for i, line in enumerate(lines):
        if re.match(r'^To\b[:\s]*$', line, re.IGNORECASE):
            for j in range(i + 1, min(i + 4, len(lines))):
                cleaned = clean_name_candidate(lines[j])
                if is_valid_name(cleaned):
                    return cleaned

    # Strategy 4: Look after 'Government of India' header
    for i, line in enumerate(lines):
        if re.search(r'Government\s*of\s*India|GOVERNMENT|BHARAT', line, re.IGNORECASE):
            for j in range(i + 1, min(i + 5, len(lines))):
                cleaned = clean_name_candidate(lines[j])
                if is_valid_name(cleaned):
                    return cleaned

    return ""

def clean_address(text):
    """Clean and normalize address string without mangling relation prefixes."""
    # Fix relation prefixes properly
    text = re.sub(r'\bS[/|\\][oO0]\b', 'S/O', text)
    text = re.sub(r'\bC[/|\\][oO0]\b', 'C/O', text)
    text = re.sub(r'\bW[/|\\][oO0]\b', 'W/O', text)
    text = re.sub(r'\bD[/|\\][oO0]\b', 'D/O', text)
    text = re.sub(r'\bS\s*0\b', 'S/O', text)
    text = re.sub(r'\bC\s*0\b', 'C/O', text)
    text = re.sub(r'\bW\s*0\b', 'W/O', text)
    text = re.sub(r'\bD\s*0\b', 'D/O', text)

    # Remove scanner app watermarks
    text = re.sub(r'Scanned by.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'CamScanner.*', '', text, flags=re.IGNORECASE)

    # Retain address characters
    text = re.sub(r'[^A-Za-z0-9,/\-\.\:\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_address_details(text):
    """
    Extracts address, pincode, and father/spouse name.
    Stops cleanly when PIN code, Aadhaar number, or UIDAI footer is reached.
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    address_lines = []
    capture = False
    pincode = ""
    father_name = ""

    all_pins = re.findall(r'\b([1-9]\d{5})\b', text)

    for i, line in enumerate(lines):
        if not capture:
            match_addr = re.search(r'\bAddress\b[\s\:]*(.*)', line, re.IGNORECASE)
            if match_addr:
                capture = True
                content = match_addr.group(1).strip()
                if content and len(content) > 3:
                    address_lines.append(content)
                continue
            if not capture and re.search(r'^(?:C/O|S/O|W/O|D/O)[\s\:]', line, re.IGNORECASE):
                capture = True
                address_lines.append(line)
                continue

        if capture:
            # Stop condition 1: 12-digit Aadhaar number
            if re.search(r'\b(?:\d{4}|[Xx\*]{4})\s(?:\d{4}|[Xx\*]{4})\s\d{4}\b', line):
                break
            # Stop condition 2: UIDAI footer boilerplate
            if any(k in line.lower() for k in ['help@uidai', '1947', 'www.uidai', 'unique identification']):
                break

            address_lines.append(line)

            # Stop condition 3: PIN code line ends address
            pin_m = re.search(r'\b([1-9]\d{5})\b', line)
            if pin_m:
                pincode = pin_m.group(1)
                break

    full_addr = ' '.join(address_lines)
    cleaned_addr = clean_address(full_addr)

    if not pincode and all_pins:
        pincode = all_pins[-1]

    # Extract Care of / Father / Spouse name if present
    co_match = re.search(
        r'\b(?:C/O|S/O|W/O|D/O)[\s\:\.\-]+([A-Za-z\s\.]+?)(?:,|(?:\b(?:House|H\.No|HNo|Flat|Vill|Ward|Plot|Near|Road|Street|Sector|Block|Post|PO)\b)|$)',
        cleaned_addr,
        re.IGNORECASE
    )
    if co_match:
        f_cand = co_match.group(1).strip()
        f_words = [w for w in f_cand.split() if len(w) > 1]
        if f_words and len(f_words) <= 5:
            father_name = ' '.join(f_words)

    return cleaned_addr, pincode, father_name

# Backward compatibility functions
def extract_front(text):
    """Backward compatible extract_front."""
    return {
        "Name": extract_name(text),
        "DOB": extract_dob(text),
        "Gender": extract_gender(text),
        "Aadhaar": extract_aadhaar_number(text)
    }

def extract_address(text):
    """Backward compatible extract_address."""
    addr, _, _ = extract_address_details(text)
    return addr

# =========================================================
# 7. Main Process Entry Point
# =========================================================
def process(front_path, back_path=None):
    """
    Universal Aadhaar processor.
    Handles both two-file (front + back) and single-file (e-Aadhaar/combined) uploads.
    Supports PDF, JPG, PNG, and other standard formats.
    """
    front_text = ocr_pdf(front_path) if front_path else ""
    back_text = ocr_pdf(back_path) if (back_path and back_path != front_path) else ""

    combined_text = front_text + "\n" + back_text

    # Extract Front Details
    name = extract_name(front_text) or extract_name(combined_text)
    dob = extract_dob(front_text) or extract_dob(combined_text)
    gender = extract_gender(front_text) or extract_gender(combined_text)
    aadhaar = extract_aadhaar_number(front_text) or extract_aadhaar_number(combined_text)

    # Extract Back / Address Details
    if back_text:
        addr, pincode, father_name = extract_address_details(back_text)
        if not addr:
            addr, pincode, father_name = extract_address_details(combined_text)
    else:
        addr, pincode, father_name = extract_address_details(combined_text)

    # Check for QR code in images if available
    for path in [front_path, back_path]:
        if path and os.path.exists(path):
            try:
                img = cv2.imread(path)
                if img is not None:
                    qr_data = extract_qr_data(img)
                    if qr_data:
                        name = name or qr_data["Name"]
                        dob = dob or qr_data["DOB"]
                        gender = gender or qr_data["Gender"]
                        aadhaar = aadhaar or qr_data["Aadhaar"]
                        addr = addr or qr_data["Address"]
                        pincode = pincode or qr_data["Pincode"]
                        father_name = father_name or qr_data["Father_Name"]
            except Exception:
                pass

    return {
        "name": name,
        "dob": dob,
        "gender": gender,
        "aadhaar": aadhaar,
        "address": addr,
        "pincode": pincode,
        "father_name": father_name
    }
import easyocr
from pdf2image import convert_from_path
from PIL import Image
import numpy as np
import re
import os
import platform

# Cross-platform poppler path
POPPLER_PATH = None
if platform.system() == "Windows":
    POPPLER_PATH = os.getenv("POPPLER_PATH", r"C:\poppler-25.07.0\Library\bin")
# On Linux/Docker, poppler-utils is in PATH, so no path needed

reader = easyocr.Reader(['en'], gpu=False)


# 🔥 MISSING FUNCTION (IMPORTANT)
def extract_pan_data(file_path):
    images = []

    if file_path.lower().endswith(".pdf"):
        images = convert_from_path(file_path, dpi=300, poppler_path=POPPLER_PATH)
    else:
        images = [Image.open(file_path)]

    full_text = ""

    for img in images:
        img = np.array(img)
        results = reader.readtext(img)

        for (_, text, prob) in results:
            if prob > 0.5:
                full_text += text + " "

    print("OCR TEXT:", full_text)

    return parse_pan_details(full_text)


# =========================
# 🔥 CLEAN WORDS
# =========================
def clean_words(words):
    ignore = {
        "INCOME","TAX","DEPARTMENT","GOVT","INDIA",
        "PERMANENT","ACCOUNT","NUMBER","CARD",
        "SIGNATURE","PHOTO","OF"
    }
    return [w for w in words if w.isalpha() and len(w) > 2 and w not in ignore]


# =========================
# 🔥 UNIVERSAL PARSER
# =========================
def parse_pan_details(text):
    data = {
        "Name": "",
        "Father_Name": "",
        "DOB": "",
        "PAN_Number": ""
    }

    text = text.upper()
    words = text.split()

    # ✅ PAN
    pan_match = re.search(r"[A-Z]{5}[0-9O]{4}[A-Z]", text)
    if pan_match:
        data["PAN_Number"] = pan_match.group().replace("O", "0")
        

    # ✅ DOB
    dob_match = re.search(r"\d{2}/\d{2}/\d{4}", text)
    if dob_match:
        data["DOB"] = dob_match.group()

    # 🔥 STRATEGY 1: NAME keyword
    name_indexes = [i for i, w in enumerate(words) if w == "NAME"]

    if len(name_indexes) >= 2:
     name_words = clean_words(words[name_indexes[0]+1:name_indexes[0]+5])
     data["Name"] = " ".join(name_words[:2])

    father_words = clean_words(words[name_indexes[1]+1:name_indexes[1]+10])
    data["Father_Name"] = " ".join(father_words)

    # ✅ FIX HERE
    data["Name"] = re.sub(r"\bNAME\b", "", data["Name"]).strip()

    return data

    # 🔥 STRATEGY 2: INDIA anchor
    if "INDIA" in words:
        idx = words.index("INDIA")
        clean = clean_words(words[idx+1:])

        clean = [w for w in clean if w not in ["TRT","CDT","FGT","FAM"]]

        if len(clean) >= 6:
            data["Name"] = " ".join(clean[0:3])
            data["Father_Name"] = " ".join(clean[3:6])
            return data

    # 🔥 STRATEGY 3: DOB anchor
    if data["DOB"]:
        try:
            dob_index = words.index(data["DOB"])
        except:
            dob_index = -1

        if dob_index > 5:
            before = clean_words(words[dob_index-10:dob_index])

            if len(before) >= 5:
                data["Name"] = " ".join(before[0:2])
                data["Father_Name"] = " ".join(before[2:6])
                return data

    # 🔥 STRATEGY 4: fallback
    clean = clean_words(words)

    if len(clean) >= 6:
        data["Name"] = " ".join(clean[0:2])
        data["Father_Name"] = " ".join(clean[2:6])

        # cleanup
        data["Name"] = data["Name"].replace("NAME", "").strip()



    return data
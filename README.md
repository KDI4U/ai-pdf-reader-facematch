# 👁️ AI Document Intelligence & Biometric Face Match API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-Face_Match-5C3EE8?logo=opencv&logoColor=white)](https://opencv.org/)
[![ONNX](https://img.shields.io/badge/ONNX_Runtime-SFace_&_YuNet-005CED?logo=onnx&logoColor=white)](https://onnxruntime.ai/)
[![EasyOCR](https://img.shields.io/badge/EasyOCR-Deep_Learning_OCR-green)](https://github.com/JaidedAI/EasyOCR)
[![Tesseract](https://img.shields.io/badge/Tesseract-OCR_Engine-blue)](https://github.com/tesseract-ocr/tesseract)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An enterprise-grade **Document AI and Biometric Verification Platform** engineered with **FastAPI**, **OpenCV**, and **PyTorch**. The service provides automated data extraction for identity documents (Aadhaar, PAN), financial statements (SBI, Banking PDFs), and agreements, combined with high-accuracy biometric facial detection and verification powered by pre-trained ONNX deep learning models (`YuNet` and `SFace`).

---

## 🌟 Core Capabilities

- **🪪 Aadhaar & PAN Card Intelligence**: Automated text extraction, format validation, and field parsing (Name, DOB, Gender, ID numbers) with adaptive image preprocessing.
- **👤 Biometric Face Match & Verification**: High-precision 1:1 facial verification using OpenCV DNN with **YuNet** (ultra-fast face detector) and **SFace** (deep feature embedding extractor) generating cosine similarity scores.
- **📑 Financial & Agreement PDF Parsing**: High-fidelity structured tabular extraction from banking statements (e.g., SBI) and legal agreement PDFs using **PyMuPDF**, **pdfplumber**, and **pikepdf**.
- **🔤 Dual-Engine OCR Pipeline**: Hybrid OCR combining **Tesseract** (for fast alphanumeric reading) and **EasyOCR** (for complex backgrounds and orientation variations).
- **🐳 Production Ready**: Fully containerized with a production multi-stage Dockerfile and automated CI/CD GitHub Actions workflow.

---

## 📂 Project Architecture

```
PdfReader/
├── app/
│   ├── api/v1/                        # Endpoint routers
│   │   ├── face_match_api.py          # Biometric 1:1 Face Match & Verification API
│   │   ├── aadhaar_api.py             # Aadhaar card extraction & validation
│   │   ├── pan_api.py                 # PAN card extraction & parsing
│   │   ├── sbipdf_routes.py           # Bank statement parsing routes
│   │   ├── rojgaar_snagampdf_api.py   # Rojgaar Sangam document parsing
│   │   └── agreement_route.py         # Agreement PDF parsing
│   │
│   ├── core/                          # App configuration, logging & CORS setup
│   ├── db/                            # Database connection & persistence layer
│   ├── models/                        # Internal data models
│   ├── schemas/                       # Pydantic request/response schemas
│   ├── services/                      # Deep learning & extraction business logic
│   │   ├── face_match_service.py      # YuNet & SFace ONNX inference engine
│   │   ├── aadhaar_service.py         # Aadhaar text processing & OCR
│   │   └── pan_service.py             # PAN validation & regex extraction
│   └── main.py                        # FastAPI application entrypoint
│
├── models/                            # Pre-trained Deep Learning ONNX Models
│   ├── face_detection_yunet_2023mar.onnx   # Real-time face detection model
│   └── face_recognition_sface_2021dec.onnx # Deep facial embedding extraction model
│
├── .github/workflows/                 # Automated deployment & CI/CD workflow
├── .dockerignore                      # Docker ignore rules
├── .env.example                       # Environment configuration template
├── .gitignore                         # Security rules ignoring identity uploads & cache
├── Dockerfile                         # Container build specification
├── requirements.txt                   # Project dependencies
└── README.md                          # Project documentation
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10 or higher
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed on your system
- Poppler (for `pdf2image` conversions)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/KDI4U/ai-pdf-reader-facematch.git
cd ai-pdf-reader-facematch

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
```ini
ENVIRONMENT=development
PHOTO_FOLDER=uploads/updatedphoto
TESSERACT_CMD=
CORS_ORIGINS=*
```

### 4. Run the API Server
```bash
uvicorn app.main:app --reload --port 8000
```
Interactive Swagger documentation will be available at: `http://localhost:8000/docs`

---

## 🔌 Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/face-match/` | Compares two facial images and returns similarity score & verification boolean |
| `POST` | `/api/v1/aadhaar/` | Ingests Aadhaar card image/PDF and returns extracted JSON fields |
| `POST` | `/api/v1/pan/` | Ingests PAN card image/PDF and returns verified cardholder data |
| `POST` | `/api/v1/sbi-statement/` | Parses tabular financial transactions from bank statement PDFs |
| `POST` | `/api/v1/agreement/` | Extracts contractual metadata and signatories from legal agreement PDFs |

---

## 🐳 Docker Deployment

```bash
# Build the Docker image
docker build -t ai-pdf-reader .

# Run the container
docker run -p 8000:8000 --env-file .env ai-pdf-reader
```

---

## 🔒 Security & Compliance
All user-uploaded identification documents, facial photographs, and temporary parsing files are excluded via `.gitignore` to guarantee complete privacy and zero data persistence.

---

## 📄 License
This project is licensed under the MIT License.

---

<div align="center">
  <b>Developed & Maintained by <a href="https://github.com/KDI4U">Kundan Kumar</a></b>
</div>

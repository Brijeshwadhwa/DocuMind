# DocuMind — Document Intelligence & Question Extraction Service

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg?logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg?logo=postgresql)](https://www.postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7+-DC382D.svg?logo=redis)](https://redis.io)
[![Celery](https://img.shields.io/badge/Celery-5+-37814A.svg?logo=celery)](https://docs.celeryq.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker)](https://www.docker.com)
[![Tests](https://img.shields.io/badge/Tests-30%20Passed%20(100%25)-success)](https://pytest.org)

**Engineering Assignment — Full Stack Developer — Round 2**  
*Pragati Bharati: Document Processing & Question Extraction Service*

---

## 1. Project Overview

The **Document Intelligence & Question Extraction Service** is a production-oriented, scalable backend service that ingests examination question papers in PDF or image format and transforms them into structured, machine-readable question banks.

The service is engineered to handle real-world, imperfect inputs:
- **Digitally Generated PDFs**: Fast, lossless native vector text extraction with page preservation.
- **Scanned & Low-Quality PDFs**: Automatic fallback to 300 DPI page rendering, OpenCV deskewing, binarization, and Tesseract OCR.
- **High-Resolution Examination Images**: JPEG and PNG support with image contrast enhancement.
- **Complex Multi-Page Questions**: Detection and stitching of questions that begin on one page and conclude on subsequent pages.
- **Structured Option Parsing**: Flexible extraction of options formatted as `A-D`, `(a)-(d)`, `[A]-[D]`, or inline horizontal rows.
- **Embedded & Separate Answer Keys**: Ingestion of answer key tables within the document or linked from separate official answer key documents via document relationships.
- **Transparent Confidence Engine**: Multi-factor confidence evaluation (0.00 to 1.00) that generates actionable `ReviewItem` records for human verification rather than silently inventing answers.

---

## 2. Architecture & Tech Stack

```
Client / Swagger / Postman
         │
         ▼
    FastAPI (REST API Layer)
    ├── Security & RBAC (JWT + Bcrypt)
    ├── File Ingestion & Magic-Bytes Validation
    └── Database & Jobs Service
         │
         ├──► PostgreSQL (Relational Persistence & Metadata)
         │
         └──► Redis (Distributed Task Broker)
                  │
                  ▼
         Celery Background Worker
         ├── DocumentExtractor (PyMuPDF / pypdf)
         ├── ImagePreprocessor (OpenCV deskew, denoise, Otsu threshold)
         ├── Modular OCR Engine (Tesseract / Vision AI fallback)
         ├── QuestionSegmenter (State machine & regex parser)
         ├── AnswerKeyParser (Answer extraction & option validation)
         └── ConfidenceEvaluator & ReviewItem Generator
```

### Core Technologies
- **API Framework**: FastAPI, Pydantic v2, Uvicorn
- **Database**: PostgreSQL with SQLAlchemy 2.0 ORM & Alembic migrations (with zero-dependency SQLite fallback for standalone local test environments)
- **Asynchronous Queue**: Redis 7 & Celery 5 (with synchronous eager execution mode support)
- **Document & Image Processing**: PyMuPDF (`pymupdf`), `pypdf`, Pillow, OpenCV (`opencv-python-headless`)
- **OCR Engine**: Tesseract OCR via `pytesseract` with pluggable `BaseOCRService` abstraction
- **Testing**: `pytest`, `pytest-asyncio`, FastAPI `TestClient`, `httpx`

---

## 3. Quickstart Guide

### Prerequisites
- **Docker & Docker Compose** (recommended for production deployment), OR
- **Python 3.10+** (for standalone local development)

### Option A: Run with Docker Compose (Recommended)

```bash
# 1. Clone repository
git clone <repository-url>
cd PBNC

# 2. Build and start all services (API, Celery Worker, PostgreSQL, Redis)
docker compose up --build
```

The services will initialize:
- **FastAPI Application**: `http://localhost:8000`
- **Swagger Documentation**: `http://localhost:8000/docs`
- **PostgreSQL**: `localhost:5432`
- **Redis**: `localhost:6379`

### Option B: Run Standalone Locally (Zero-Friction Local Mode)

The project includes an automatic standalone local mode using SQLite and in-process Celery task execution (`CELERY_TASK_ALWAYS_EAGER=True`):

```bash
# 1. Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply database migrations
alembic upgrade head

# 4. Generate sample documents
python scripts/generate_sample_documents.py

# 5. Start the FastAPI development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 4. Environment Variables Reference

Copy `.env.example` to `.env` and customize as required:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `APP_NAME` | `Document Intelligence & Question Extraction Service` | Application display name |
| `APP_ENV` | `development` | Runtime environment (`development`, `production`) |
| `DEBUG` | `True` | Enable debug logs |
| `DATABASE_URL` | `sqlite:///./document_intelligence.db` | PostgreSQL or SQLite connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis broker URI |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker URL |
| `CELERY_RESULT_BACKEND`| `redis://localhost:6379/0` | Celery result backend |
| `CELERY_TASK_ALWAYS_EAGER` | `True` | If `True`, tasks execute in-process without needing Redis daemon |
| `SECRET_KEY` | `dev_secret_key...` | Cryptographic secret for signing JWT tokens |
| `ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Token expiration time (24 hours) |
| `UPLOAD_DIR` | `./storage/uploads` | Safe persistent storage directory for uploads |
| `MAX_FILE_SIZE_MB` | `15` | Maximum upload file size limit |
| `TESSERACT_CMD` | `tesseract` | Path to Tesseract binary on system PATH |
| `OCR_FALLBACK_ENABLED`| `True` | Enable automatic OCR fallback for scanned pages |
| `OCR_DPI` | `300` | Rendering resolution for PDF page pixmaps |
| `EXTERNAL_AI_ENABLED` | `False` | Enable optional cloud AI OCR provider |

---

## 5. API Reference & Swagger UI

Interactive Swagger documentation is available at:  
👉 **`http://localhost:8000/docs`**  
ReDoc documentation is available at:  
👉 **`http://localhost:8000/redoc`**

### Summary of Core Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/auth/register` | Register a new user account |
| `POST` | `/auth/login` | Authenticate and obtain JWT Bearer token |
| `GET` | `/auth/me` | Fetch authenticated user profile |
| `POST` | `/documents/upload` | Upload PDF or image (returns immediately with 202 Accepted) |
| `GET` | `/documents` | List uploaded documents with pagination |
| `GET` | `/documents/{id}` | Get document metadata |
| `GET` | `/documents/{id}/status` | Poll real-time background processing status and progress |
| `GET` | `/documents/{id}/questions` | Retrieve extracted questions with options and source pages |
| `GET` | `/documents/{id}/questions/{qid}`| Retrieve individual question details |
| `GET` | `/documents/{id}/answers` | Retrieve summary of matched answer keys |
| `GET` | `/documents/{id}/review-items` | Retrieve items flagged for human verification |
| `POST` | `/documents/{id}/relationships` | Link a separate Answer Key document to a Question Paper |
| `GET` | `/documents/{id}/relationships` | List relationships for a document |

---

## 6. Testing & Validation

The project includes an exhaustive automated test suite using `pytest`:

```bash
python -m pytest -v
```

### Actual Test Execution Output
```
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0
collected 30 items

tests/test_auth.py::test_register_user_success PASSED                    [  3%]
tests/test_auth.py::test_register_duplicate_email PASSED                 [  6%]
tests/test_auth.py::test_register_invalid_email PASSED                   [ 10%]
tests/test_auth.py::test_login_success PASSED                            [ 13%]
tests/test_auth.py::test_login_invalid_password PASSED                   [ 16%]
tests/test_auth.py::test_login_nonexistent_user PASSED                   [ 20%]
tests/test_auth.py::test_get_current_user_me PASSED                      [ 23%]
tests/test_auth.py::test_get_me_unauthorized PASSED                      [ 26%]
tests/test_auth.py::test_get_me_invalid_token PASSED                     [ 30%]
tests/test_confidence_and_review.py::test_confidence_and_review_items_generation PASSED [ 33%]
tests/test_confidence_and_review.py::test_clean_document_has_zero_critical_review_items PASSED [ 36%]
tests/test_documents.py::test_upload_valid_pdf PASSED                    [ 40%]
tests/test_documents.py::test_upload_valid_image PASSED                  [ 43%]
tests/test_documents.py::test_upload_unsupported_file_extension PASSED   [ 46%]
tests/test_documents.py::test_upload_corrupted_pdf_header PASSED         [ 50%]
tests/test_documents.py::test_upload_empty_file PASSED                   [ 53%]
tests/test_documents.py::test_upload_unauthorized PASSED                 [ 56%]
tests/test_documents.py::test_list_documents PASSED                      [ 60%]
tests/test_documents.py::test_get_document_details PASSED                [ 63%]
tests/test_documents.py::test_document_ownership_isolation PASSED        [ 66%]
tests/test_processing.py::test_document_status_polling PASSED            [ 70%]
tests/test_processing.py::test_document_status_unauthorized PASSED       [ 73%]
tests/test_processing.py::test_document_status_forbidden PASSED          [ 76%]
tests/test_questions.py::test_list_and_get_questions PASSED              [ 80%]
tests/test_questions.py::test_multipage_question_continuity PASSED       [ 83%]
tests/test_questions.py::test_get_answers_endpoint PASSED                [ 86%]
tests/test_questions.py::test_questions_isolation_forbidden PASSED       [ 90%]
tests/test_relationships.py::test_document_relationship_and_answer_key_association PASSED [ 93%]
tests/test_relationships.py::test_cannot_relate_document_to_itself PASSED [ 96%]
tests/test_relationships.py::test_cannot_relate_to_another_users_document PASSED [100%]

============================= 30 passed in 13.59s =============================
```

---

## 7. Sample Documents & Expected Outputs

Realistic test documents are located in `sample_documents/` and can be regenerated at any time using `python scripts/generate_sample_documents.py`:

| Sample File | Characteristics Demonstrated |
| :--- | :--- |
| `01_clean_digital_exam.pdf` | Clean digital PDF with 4 MCQs and embedded answer key table |
| `02_image_question_paper.png` | Image question paper processed through the OCR pipeline |
| `03_scanned_noisy_exam.pdf` | Scanned/noisy PDF containing an incomplete question and mismatched answer key `Z` |
| `04_multipage_continuation.pdf`| Question 2 starts on Page 1 and continues options onto Page 2 (`source_pages: [1, 2]`) |
| `05a_question_paper_only.pdf` | Question paper without answers (for multi-document relationship demonstration) |
| `05b_separate_answer_key.pdf` | Standalone official answer key document to link with `05a` |
| `06_invalid_format.txt` | Unsupported text file rejected with HTTP 400 |
| `07_corrupted_file.pdf` | Corrupted PDF header rejected with HTTP 400 |

Extracted JSON outputs for all sample documents are available in `sample_outputs/`.

---

## 8. Postman Collection

Import `postman/Document-Intelligence.postman_collection.json` into Postman.

### Pre-configured Automated Scripts
The collection includes automated test scripts that:
- Save `access_token` automatically upon login into collection variables.
- Save `document_id` upon upload.
- Save `question_id` upon listing questions.
- Save `answer_key_document_id` when uploading separate answer keys.

---

## 9. Demonstration Script

For a complete walkthrough covering all 10 required evaluation scenarios with exact curl commands, parameters, and explanations of results to highlight, refer to:  
👉 **[DEMO_SCRIPT.md](file:///c:/Users/Hp/Desktop/PBNC/DEMO_SCRIPT.md)**

---

## 10. AI/OCR Usage Disclosure

In compliance with Round 2 assignment instructions:
1. **OCR Technology**:
   - Primary local OCR is executed using **Tesseract OCR** via `pytesseract`.
   - Native digital PDF parsing is executed using **PyMuPDF (`pymupdf`)** and **`pypdf`**.
   - Image preprocessing (deskewing, denoise, adaptive binarization) is performed locally using **OpenCV** and **Pillow**.
2. **External AI Services**:
   - No third-party commercial AI/LLM API is required to run the service. The service is completely self-contained and deterministic.
   - An extensible `ExternalAIOCRService` abstraction is implemented in `app/processors/ocr_engine.py` for optional integration with cloud vision APIs (OpenAI / Google Gemini Vision). Credentials are loaded strictly from environment variables (`EXTERNAL_AI_API_KEY`) and are disabled by default (`EXTERNAL_AI_ENABLED=False`).
3. **Data Privacy**: No documents, questions, or user data are transmitted to external APIs during execution.

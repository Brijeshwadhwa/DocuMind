# Evaluation Demonstration Script

**Document Intelligence & Question Extraction Service**  
*Pragati Bharati — Round 2 Full Stack Developer Engineering Assignment*

This document provides exact, step-by-step instructions for demonstrating all 10 required evaluation scenarios using either **curl commands**, **FastAPI Swagger UI (`http://localhost:8000/docs`)**, or the **Postman Collection (`postman/Document-Intelligence.postman_collection.json`)**.

---

## Prerequisites & Server Startup

Start the service locally or with Docker Compose:

```bash
# Option A: Local Run
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Option B: Docker Compose
docker compose up --build
```

Base URL: `http://localhost:8000`  
Interactive Swagger UI: `http://localhost:8000/docs`

---

## Initial Setup: Register & Login to Obtain JWT Token

### 1. Register Candidate Account
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "candidate@pragatibharti.in", "password": "SecurePassword2026!"}'
```
**Expected Response (`201 Created`):**
```json
{
  "id": "e8d32b80-1a2b-4c5d-9e6f-7a8b9c0d1e2f",
  "email": "candidate@pragatibharti.in",
  "created_at": "2026-09-19T12:00:00Z"
}
```

### 2. Login to Obtain Access Token
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "candidate@pragatibharti.in", "password": "SecurePassword2026!"}'
```
**Expected Response (`200 OK`):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

> **Note**: Save the `access_token` into an environment variable for the subsequent commands:
> - On Linux / Mac: `export TOKEN="<your_token>"`
> - On Windows PowerShell: `$TOKEN = "<your_token>"`

---

## Scenario 1: Uploading a PDF Document

**Goal**: Demonstrate valid PDF upload, magic byte validation, non-blocking asynchronous queuing, and immediate `HTTP 202` response.

### Action
Upload sample file: `sample_documents/01_clean_digital_exam.pdf`

```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample_documents/01_clean_digital_exam.pdf"
```

### Expected Response (`202 Accepted`)
```json
{
  "document_id": "86622b8c-b592-47be-b450-9d75e6b16fd1",
  "job_id": "3a7b9c1d-2e3f-4a5b-6c7d-8e9f0a1b2c3d",
  "filename": "01_clean_digital_exam.pdf",
  "content_type": "application/pdf",
  "file_size": 2035,
  "status": "PENDING",
  "message": "Document uploaded successfully and queued for background processing."
}
```

### What to Point Out
- The request returns immediately without blocking on processing.
- Returns a unique `document_id` and background `job_id`.
- The document filename is sanitized and stored in a secure isolated storage path.

---

## Scenario 2: Uploading an Image

**Goal**: Demonstrate processing of an image question paper (`PNG` or `JPEG`).

### Action
Upload sample file: `sample_documents/02_image_question_paper.png`

```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample_documents/02_image_question_paper.png"
```

### Expected Response (`202 Accepted`)
```json
{
  "document_id": "08ed2280-d7f8-4e41-aa20-7f95a919dac2",
  "job_id": "4b8c0d2e-3f4a-5b6c-7d8e-9f0a1b2c3d4e",
  "filename": "02_image_question_paper.png",
  "content_type": "image/png",
  "file_size": 28410,
  "status": "PENDING",
  "message": "Document uploaded successfully and queued for background processing."
}
```

### What to Point Out
- The service validates image media types (`image/png`, `image/jpeg`).
- Dispatches image through the OCR and image preprocessing pipeline.

---

## Scenario 3: Processing Scanned / Low-Quality Document

**Goal**: Demonstrate handling of imperfect scans, noisy backgrounds, and OCR uncertainty.

### Action
Upload sample file: `sample_documents/03_scanned_noisy_exam.pdf`

```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample_documents/03_scanned_noisy_exam.pdf"
```

### Expected Response (`202 Accepted`)
```json
{
  "document_id": "bda20343-19eb-40b0-a268-422bebca39c4",
  "filename": "03_scanned_noisy_exam.pdf",
  "status": "PENDING"
}
```

### Check Processing Status
```bash
curl -X GET "http://localhost:8000/documents/bda20343-19eb-40b0-a268-422bebca39c4/status" \
  -H "Authorization: Bearer $TOKEN"
```
**Response (`200 OK`):**
```json
{
  "document_id": "bda20343-19eb-40b0-a268-422bebca39c4",
  "status": "COMPLETED",
  "progress": 100.0,
  "total_questions": 2,
  "total_review_items": 2
}
```

### What to Point Out
- Notice `total_review_items: 2`.
- The system gracefully processed the noisy scan, detected that Question 2 had missing options and an ambiguous answer key, and flagged review items instead of crashing.

---

## Scenario 4: Extracting Multiple Questions

**Goal**: Demonstrate segmentation and extraction of multiple questions from a document.

### Action
Fetch questions extracted from Scenario 1 (`01_clean_digital_exam.pdf`):

```bash
curl -X GET "http://localhost:8000/documents/86622b8c-b592-47be-b450-9d75e6b16fd1/questions" \
  -H "Authorization: Bearer $TOKEN"
```

### Expected Response Snippet (`200 OK`)
```json
{
  "total": 4,
  "document_id": "86622b8c-b592-47be-b450-9d75e6b16fd1",
  "questions": [
    {
      "id": "18f9780a-9d62-4bc9-8809-7a3c3065da47",
      "question_number": "1",
      "question": "What is the chemical symbol for Gold?",
      "question_type": "MCQ",
      "options": {
        "A": "Ag",
        "B": "Au",
        "C": "Fe",
        "D": "Pb"
      },
      "answer": "B",
      "answer_confidence": 0.96,
      "extraction_confidence": 1.0,
      "status": "SUCCESS",
      "source_pages": [1]
    },
    {
      "id": "c85012a6-2bd0-4226-928d-195c866d98c2",
      "question_number": "2",
      "question": "Which planet is known as the Red Planet?",
      "question_type": "MCQ",
      "options": {
        "A": "Venus",
        "B": "Mars",
        "C": "Jupiter",
        "D": "Saturn"
      },
      "answer": "B",
      "answer_confidence": 0.96,
      "extraction_confidence": 1.0,
      "status": "SUCCESS",
      "source_pages": [1]
    }
  ]
}
```

### What to Point Out
- All 4 questions are individually segmented.
- Question numbers are normalized (`"1"`, `"2"`, `"3"`, `"4"`).
- Clean separation between questions and the answer key table at the bottom.

---

## Scenario 5: Handling a Question Spanning Multiple Pages

**Goal**: Demonstrate continuity tracking across page transitions.

### Action
Upload sample file: `sample_documents/04_multipage_continuation.pdf`

```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample_documents/04_multipage_continuation.pdf"
```

Then fetch questions for the returned document ID:
```bash
curl -X GET "http://localhost:8000/documents/<doc_id>/questions" \
  -H "Authorization: Bearer $TOKEN"
```

### Expected Response Snippet (`200 OK`)
```json
{
  "question_number": "2",
  "question": "Which treaty signed in 1919 brought World War I to an official end, imposing significant reparations on Germany and establishing the League of Nations?",
  "question_type": "MCQ",
  "options": {
    "A": "Treaty of Paris",
    "B": "Treaty of Versailles",
    "C": "Treaty of Utrecht",
    "D": "Treaty of Ghent"
  },
  "answer": "B",
  "answer_confidence": 0.96,
  "extraction_confidence": 0.95,
  "status": "SUCCESS",
  "source_pages": [1, 2]
}
```

### What to Point Out
- Notice `"source_pages": [1, 2]`!
- Question 2 begins on Page 1 (with options A and B) and continues on Page 2 (with options C and D).
- The system merged the multi-page content while filtering out the Page 2 header (`History Final Examination - Part II`).

---

## Scenario 6: Extracting Question Options

**Goal**: Demonstrate structured key-value option extraction (`A-D`, `(a)-(d)`, `1-4`).

### Action
Inspect question options from Scenario 1 or Scenario 2:

```json
"options": {
  "A": "Ag",
  "B": "Au",
  "C": "Fe",
  "D": "Pb"
}
```

### What to Point Out
- Options are returned as clean key-value pairs (`{"A": "...", "B": "..."}`).
- Supported both multi-line option formats and horizontal inline options (`(A) Red (B) Green...`).
- Option labels are cleanly stripped from option text bodies.

---

## Scenario 7: Detecting & Associating Answer Keys

**Goal**: Demonstrate detection of answer keys and cross-document answer matching.

### Part A: In-Document Answer Key
In Scenario 1, the document had an embedded answer key table `1-B  2-B  3-C  4-A`.  
Call `GET /documents/{id}/answers`:
```bash
curl -X GET "http://localhost:8000/documents/86622b8c-b592-47be-b450-9d75e6b16fd1/answers" \
  -H "Authorization: Bearer $TOKEN"
```
**Response (`200 OK`):**
```json
{
  "document_id": "86622b8c-b592-47be-b450-9d75e6b16fd1",
  "total_questions": 4,
  "answered_count": 4,
  "unanswered_count": 0,
  "answers": [
    {"question_number": "1", "answer": "B", "answer_confidence": 0.96},
    {"question_number": "2", "answer": "B", "answer_confidence": 0.96},
    {"question_number": "3", "answer": "C", "answer_confidence": 0.96},
    {"question_number": "4", "answer": "A", "answer_confidence": 0.96}
  ]
}
```

### Part B: Separate Answer Key Document via Relationship
1. Upload Question Paper: `05a_question_paper_only.pdf`
2. Upload Answer Key: `05b_separate_answer_key.pdf`
3. Establish relationship:
```bash
curl -X POST "http://localhost:8000/documents/<doc_a_id>/relationships" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"related_document_id": "<doc_b_id>", "relationship_type": "ANSWER_KEY"}'
```
**Result**: `Doc A` questions are automatically populated with answers from `Doc B`!

---

## Scenario 8: Showing Uncertain / Low-Confidence Extraction

**Goal**: Demonstrate transparency when encountering malformed options or mismatching answer keys.

### Action
Inspect review items for Scenario 3 (`03_scanned_noisy_exam.pdf`):

```bash
curl -X GET "http://localhost:8000/documents/bda20343-19eb-40b0-a268-422bebca39c4/review-items" \
  -H "Authorization: Bearer $TOKEN"
```

### Expected Response (`200 OK`)
```json
{
  "total": 2,
  "document_id": "bda20343-19eb-40b0-a268-422bebca39c4",
  "review_items": [
    {
      "issue_type": "MALFORMED_OPTIONS",
      "message": "Question has only 1 option (options B, C, D missing or unparsed)",
      "confidence": 0.40,
      "status": "OPEN"
    },
    {
      "issue_type": "LOW_CONFIDENCE_ANSWER",
      "message": "Answer key entry 'Z' does not match available options (A) for Question 2",
      "confidence": 0.35,
      "status": "OPEN"
    }
  ]
}
```

### What to Point Out
- The system **never silently invents an answer**.
- Because the answer key said `Z` (which is not an available option), the system set `answer=null` and generated a descriptive review item.
- Question 2 status is downgraded to `PARTIAL` / `REVIEW_REQUIRED`.

---

## Scenario 9: Retrieving Final Structured Question Data

**Goal**: Demonstrate system-independent, rich structured JSON question retrieval.

### Action
Fetch single question detail:
```bash
curl -X GET "http://localhost:8000/documents/86622b8c-b592-47be-b450-9d75e6b16fd1/questions/18f9780a-9d62-4bc9-8809-7a3c3065da47" \
  -H "Authorization: Bearer $TOKEN"
```

### Expected Response (`200 OK`)
```json
{
  "id": "18f9780a-9d62-4bc9-8809-7a3c3065da47",
  "source_document_id": "86622b8c-b592-47be-b450-9d75e6b16fd1",
  "question_number": "1",
  "question": "What is the chemical symbol for Gold?",
  "question_type": "MCQ",
  "options": {
    "A": "Ag",
    "B": "Au",
    "C": "Fe",
    "D": "Pb"
  },
  "answer": "B",
  "answer_confidence": 0.96,
  "extraction_confidence": 1.0,
  "status": "SUCCESS",
  "source_pages": [1],
  "source_text": "1. What is the chemical symbol for Gold?\n(A) Ag    (B) Au\n(C) Fe    (D) Pb",
  "metadata": {
    "option_count": 4,
    "is_multipage": false,
    "character_length": 37
  },
  "created_at": "2026-09-19T12:00:00Z",
  "updated_at": "2026-09-19T12:00:00Z"
}
```

### What to Point Out
- Full source traceability: preserves `source_pages`, `source_text`, and original bounding context.
- System-independent JSON schema ready for downstream assessment platforms.

---

## Scenario 10: Handling Invalid or Unsupported Document

**Goal**: Demonstrate defensive validation against invalid file extensions, spoofed headers, and empty files.

### Test A: Unsupported Extension (`.txt`)
```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample_documents/06_invalid_format.txt"
```
**Expected Response (`400 Bad Request`):**
```json
{
  "detail": "Unsupported file extension 'txt'. Allowed extensions: pdf, png, jpg, jpeg"
}
```

### Test B: Corrupted File with Spoofed Extension (`.pdf`)
```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample_documents/07_corrupted_file.pdf"
```
**Expected Response (`400 Bad Request`):**
```json
{
  "detail": "Malformed file: file content header does not match declared format 'pdf'"
}
```

### What to Point Out
- Magic byte validation catches disguised files before they reach the worker.
- Returns explicit, actionable HTTP error messages without crashing the API or worker.

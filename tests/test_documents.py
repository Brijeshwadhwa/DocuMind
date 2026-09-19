import os
import io
import pytest
from fastapi.testclient import TestClient


def test_upload_valid_pdf(client: TestClient, auth_headers: dict):
    file_path = "sample_documents/01_clean_digital_exam.pdf"
    with open(file_path, "rb") as f:
        response = client.post(
            "/documents/upload",
            files={"file": ("01_clean_digital_exam.pdf", f, "application/pdf")},
            headers=auth_headers
        )
    assert response.status_code == 202
    data = response.json()
    assert "document_id" in data
    assert "job_id" in data
    assert data["filename"] == "01_clean_digital_exam.pdf"
    assert data["content_type"] == "application/pdf"
    assert data["status"] in ("PENDING", "PROCESSING", "COMPLETED")


def test_upload_valid_image(client: TestClient, auth_headers: dict):
    file_path = "sample_documents/02_image_question_paper.png"
    with open(file_path, "rb") as f:
        response = client.post(
            "/documents/upload",
            files={"file": ("02_image_question_paper.png", f, "image/png")},
            headers=auth_headers
        )
    assert response.status_code == 202
    data = response.json()
    assert "document_id" in data
    assert data["content_type"] == "image/png"


def test_upload_unsupported_file_extension(client: TestClient, auth_headers: dict):
    file_content = b"Simple plain text file contents"
    response = client.post(
        "/documents/upload",
        files={"file": ("notes.txt", io.BytesIO(file_content), "text/plain")},
        headers=auth_headers
    )
    assert response.status_code in (400, 415)


def test_upload_corrupted_pdf_header(client: TestClient, auth_headers: dict):
    corrupt_bytes = b"NOT_A_REAL_PDF_HEADER_12345"
    response = client.post(
        "/documents/upload",
        files={"file": ("corrupted.pdf", io.BytesIO(corrupt_bytes), "application/pdf")},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert "malformed" in response.json()["detail"].lower()


def test_upload_empty_file(client: TestClient, auth_headers: dict):
    response = client.post(
        "/documents/upload",
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_unauthorized(client: TestClient):
    with open("sample_documents/01_clean_digital_exam.pdf", "rb") as f:
        response = client.post(
            "/documents/upload",
            files={"file": ("exam.pdf", f, "application/pdf")}
        )
    assert response.status_code == 401


def test_list_documents(client: TestClient, auth_headers: dict):
    # Upload one doc
    with open("sample_documents/01_clean_digital_exam.pdf", "rb") as f:
        client.post(
            "/documents/upload",
            files={"file": ("exam.pdf", f, "application/pdf")},
            headers=auth_headers
        )

    response = client.get("/documents", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["documents"]) >= 1


def test_get_document_details(client: TestClient, auth_headers: dict):
    with open("sample_documents/01_clean_digital_exam.pdf", "rb") as f:
        up_res = client.post(
            "/documents/upload",
            files={"file": ("exam.pdf", f, "application/pdf")},
            headers=auth_headers
        )
    doc_id = up_res.json()["document_id"]

    response = client.get(f"/documents/{doc_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc_id


def test_document_ownership_isolation(client: TestClient, auth_headers: dict, second_user_headers: dict):
    # User 1 uploads document
    with open("sample_documents/01_clean_digital_exam.pdf", "rb") as f:
        up_res = client.post(
            "/documents/upload",
            files={"file": ("user1_exam.pdf", f, "application/pdf")},
            headers=auth_headers
        )
    doc_id = up_res.json()["document_id"]

    # User 2 tries to access User 1's document
    res_user2 = client.get(f"/documents/{doc_id}", headers=second_user_headers)
    assert res_user2.status_code == 403

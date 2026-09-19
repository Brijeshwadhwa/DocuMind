import pytest
from fastapi.testclient import TestClient


def test_document_status_polling(client: TestClient, auth_headers: dict):
    with open("sample_documents/01_clean_digital_exam.pdf", "rb") as f:
        up_res = client.post(
            "/documents/upload",
            files={"file": ("status_exam.pdf", f, "application/pdf")},
            headers=auth_headers
        )
    doc_id = up_res.json()["document_id"]

    response = client.get(f"/documents/{doc_id}/status", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == doc_id
    assert "status" in data
    assert "progress" in data
    assert data["status"] in ("PENDING", "PROCESSING", "COMPLETED")
    assert data["progress"] >= 0.0


def test_document_status_unauthorized(client: TestClient):
    response = client.get("/documents/fake-doc-id/status")
    assert response.status_code == 401


def test_document_status_forbidden(client: TestClient, auth_headers: dict, second_user_headers: dict):
    with open("sample_documents/01_clean_digital_exam.pdf", "rb") as f:
        up_res = client.post(
            "/documents/upload",
            files={"file": ("status_exam.pdf", f, "application/pdf")},
            headers=auth_headers
        )
    doc_id = up_res.json()["document_id"]

    response = client.get(f"/documents/{doc_id}/status", headers=second_user_headers)
    assert response.status_code == 403

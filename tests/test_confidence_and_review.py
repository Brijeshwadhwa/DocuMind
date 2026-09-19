import pytest
from fastapi.testclient import TestClient


def test_confidence_and_review_items_generation(client: TestClient, auth_headers: dict):
    # Upload noisy document with incomplete question and invalid answer key 'Z'
    with open("sample_documents/03_scanned_noisy_exam.pdf", "rb") as f:
        up_res = client.post(
            "/documents/upload",
            files={"file": ("03_scanned_noisy_exam.pdf", f, "application/pdf")},
            headers=auth_headers
        )
    doc_id = up_res.json()["document_id"]

    # Retrieve review items
    rev_res = client.get(f"/documents/{doc_id}/review-items", headers=auth_headers)
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    assert rev_data["total"] >= 1
    assert len(rev_data["review_items"]) >= 1

    issue_types = [item["issue_type"] for item in rev_data["review_items"]]
    # Should flag malformed options for Q2
    assert "MALFORMED_OPTIONS" in issue_types or "LOW_CONFIDENCE_ANSWER" in issue_types

    # Check question status
    q_res = client.get(f"/documents/{doc_id}/questions", headers=auth_headers)
    assert q_res.status_code == 200
    questions = q_res.json()["questions"]
    q2 = next(q for q in questions if q["question_number"] == "2")
    assert q2["status"] in ("PARTIAL", "REVIEW_REQUIRED")
    # Answer should not be falsely assigned to 'Z'
    assert q2["answer"] != "Z"


def test_clean_document_has_zero_critical_review_items(client: TestClient, auth_headers: dict):
    with open("sample_documents/01_clean_digital_exam.pdf", "rb") as f:
        up_res = client.post(
            "/documents/upload",
            files={"file": ("clean_exam.pdf", f, "application/pdf")},
            headers=auth_headers
        )
    doc_id = up_res.json()["document_id"]

    rev_res = client.get(f"/documents/{doc_id}/review-items", headers=auth_headers)
    assert rev_res.status_code == 200
    assert rev_res.json()["total"] == 0

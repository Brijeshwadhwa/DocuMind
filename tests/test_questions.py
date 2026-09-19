import pytest
from fastapi.testclient import TestClient


def test_list_and_get_questions(client: TestClient, auth_headers: dict):
    # Upload clean exam
    with open("sample_documents/01_clean_digital_exam.pdf", "rb") as f:
        up_res = client.post(
            "/documents/upload",
            files={"file": ("questions_exam.pdf", f, "application/pdf")},
            headers=auth_headers
        )
    doc_id = up_res.json()["document_id"]

    # Retrieve questions
    response = client.get(f"/documents/{doc_id}/questions", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == doc_id
    assert data["total"] == 4
    assert len(data["questions"]) == 4

    first_q = data["questions"][0]
    assert first_q["question_number"] == "1"
    assert "chemical symbol for Gold" in first_q["question"]
    assert first_q["question_type"] == "MCQ"
    assert first_q["options"] == {"A": "Ag", "B": "Au", "C": "Fe", "D": "Pb"}
    assert first_q["answer"] == "B"
    assert first_q["answer_confidence"] >= 0.90
    assert first_q["extraction_confidence"] >= 0.90
    assert first_q["source_pages"] == [1]

    # Test single question retrieval
    q_id = first_q["id"]
    single_res = client.get(f"/documents/{doc_id}/questions/{q_id}", headers=auth_headers)
    assert single_res.status_code == 200
    single_data = single_res.json()
    assert single_data["id"] == q_id
    assert single_data["question_number"] == "1"


def test_multipage_question_continuity(client: TestClient, auth_headers: dict):
    with open("sample_documents/04_multipage_continuation.pdf", "rb") as f:
        up_res = client.post(
            "/documents/upload",
            files={"file": ("multipage_exam.pdf", f, "application/pdf")},
            headers=auth_headers
        )
    doc_id = up_res.json()["document_id"]

    response = client.get(f"/documents/{doc_id}/questions", headers=auth_headers)
    assert response.status_code == 200
    questions = response.json()["questions"]
    assert len(questions) == 3

    # Question 2 spans across pages 1 and 2
    q2 = next(q for q in questions if q["question_number"] == "2")
    assert "treaty" in q2["question"].lower()
    assert q2["source_pages"] == [1, 2]
    assert "A" in q2["options"] and "D" in q2["options"]


def test_get_answers_endpoint(client: TestClient, auth_headers: dict):
    with open("sample_documents/01_clean_digital_exam.pdf", "rb") as f:
        up_res = client.post(
            "/documents/upload",
            files={"file": ("answers_exam.pdf", f, "application/pdf")},
            headers=auth_headers
        )
    doc_id = up_res.json()["document_id"]

    response = client.get(f"/documents/{doc_id}/answers", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_questions"] == 4
    assert data["answered_count"] == 4
    assert data["unanswered_count"] == 0
    assert len(data["answers"]) == 4


def test_questions_isolation_forbidden(client: TestClient, auth_headers: dict, second_user_headers: dict):
    with open("sample_documents/01_clean_digital_exam.pdf", "rb") as f:
        up_res = client.post(
            "/documents/upload",
            files={"file": ("answers_exam.pdf", f, "application/pdf")},
            headers=auth_headers
        )
    doc_id = up_res.json()["document_id"]

    res_user2 = client.get(f"/documents/{doc_id}/questions", headers=second_user_headers)
    assert res_user2.status_code == 403

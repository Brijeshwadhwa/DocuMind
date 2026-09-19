import pytest
from fastapi.testclient import TestClient


def test_document_relationship_and_answer_key_association(client: TestClient, auth_headers: dict):
    # 1. Upload Question Paper (has no answers initially)
    with open("sample_documents/05a_question_paper_only.pdf", "rb") as f:
        up_a = client.post(
            "/documents/upload",
            files={"file": ("05a_question_paper_only.pdf", f, "application/pdf")},
            headers=auth_headers
        )
    doc_a_id = up_a.json()["document_id"]

    # Verify answers are None before relationship
    q_res = client.get(f"/documents/{doc_a_id}/questions", headers=auth_headers)
    assert q_res.status_code == 200
    questions = q_res.json()["questions"]
    assert len(questions) == 2
    assert all(q["answer"] is None for q in questions)

    # 2. Upload Separate Answer Key
    with open("sample_documents/05b_separate_answer_key.pdf", "rb") as f:
        up_b = client.post(
            "/documents/upload",
            files={"file": ("05b_separate_answer_key.pdf", f, "application/pdf")},
            headers=auth_headers
        )
    doc_b_id = up_b.json()["document_id"]

    # 3. Establish ANSWER_KEY relationship
    rel_res = client.post(
        f"/documents/{doc_a_id}/relationships",
        json={"related_document_id": doc_b_id, "relationship_type": "ANSWER_KEY"},
        headers=auth_headers
    )
    assert rel_res.status_code == 201
    rel_data = rel_res.json()
    assert rel_data["source_document_id"] == doc_a_id
    assert rel_data["related_document_id"] == doc_b_id
    assert rel_data["relationship_type"] == "ANSWER_KEY"

    # 4. List relationships
    list_rel = client.get(f"/documents/{doc_a_id}/relationships", headers=auth_headers)
    assert list_rel.status_code == 200
    assert len(list_rel.json()) >= 1

    # 5. Verify that questions on Doc A now have associated answers!
    updated_q_res = client.get(f"/documents/{doc_a_id}/questions", headers=auth_headers)
    assert updated_q_res.status_code == 200
    updated_questions = updated_q_res.json()["questions"]
    assert updated_questions[0]["answer"] == "C"
    assert updated_questions[1]["answer"] == "C"
    assert updated_questions[0]["answer_confidence"] >= 0.85


def test_cannot_relate_document_to_itself(client: TestClient, auth_headers: dict):
    with open("sample_documents/01_clean_digital_exam.pdf", "rb") as f:
        up = client.post(
            "/documents/upload",
            files={"file": ("self_rel.pdf", f, "application/pdf")},
            headers=auth_headers
        )
    doc_id = up.json()["document_id"]

    rel_res = client.post(
        f"/documents/{doc_id}/relationships",
        json={"related_document_id": doc_id, "relationship_type": "ANSWER_KEY"},
        headers=auth_headers
    )
    assert rel_res.status_code == 400


def test_cannot_relate_to_another_users_document(
    client: TestClient,
    auth_headers: dict,
    second_user_headers: dict
):
    # User 1 doc
    with open("sample_documents/01_clean_digital_exam.pdf", "rb") as f:
        up1 = client.post(
            "/documents/upload",
            files={"file": ("u1.pdf", f, "application/pdf")},
            headers=auth_headers
        )
    doc1_id = up1.json()["document_id"]

    # User 2 doc
    with open("sample_documents/01_clean_digital_exam.pdf", "rb") as f:
        up2 = client.post(
            "/documents/upload",
            files={"file": ("u2.pdf", f, "application/pdf")},
            headers=second_user_headers
        )
    doc2_id = up2.json()["document_id"]

    # User 1 attempts to link User 2's document
    rel_res = client.post(
        f"/documents/{doc1_id}/relationships",
        json={"related_document_id": doc2_id, "relationship_type": "ANSWER_KEY"},
        headers=auth_headers
    )
    assert rel_res.status_code == 403

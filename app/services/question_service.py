from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.document import Document
from app.models.question import Question
from app.schemas.question import (
    QuestionResponse,
    QuestionListResponse,
    AnswerItemResponse,
    DocumentAnswersResponse
)
from app.schemas.review_item import ReviewItemResponse, ReviewItemListResponse
from app.repositories.document_repo import DocumentRepository
from app.repositories.question_repo import QuestionRepository


class QuestionService:
    def __init__(self, db: Session):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.question_repo = QuestionRepository(db)

    def _verify_document_access(self, document_id: str, owner_id: str) -> Document:
        doc = self.doc_repo.get_by_id(document_id)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        if doc.owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Not document owner")
        return doc

    def list_questions(self, document_id: str, owner_id: str) -> QuestionListResponse:
        self._verify_document_access(document_id, owner_id)
        questions = self.question_repo.list_by_document(document_id)

        return QuestionListResponse(
            total=len(questions),
            document_id=document_id,
            questions=[QuestionResponse.model_validate(q) for q in questions]
        )

    def get_question(self, document_id: str, question_id: str, owner_id: str) -> QuestionResponse:
        self._verify_document_access(document_id, owner_id)
        q = self.question_repo.get_by_id_and_doc(question_id, document_id)
        if not q:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        return QuestionResponse.model_validate(q)

    def get_answers(self, document_id: str, owner_id: str) -> DocumentAnswersResponse:
        self._verify_document_access(document_id, owner_id)
        questions = self.question_repo.list_by_document(document_id)

        answers: List[AnswerItemResponse] = []
        answered = 0
        unanswered = 0

        for q in questions:
            if q.answer:
                answered += 1
            else:
                unanswered += 1

            answers.append(AnswerItemResponse(
                question_id=q.id,
                question_number=q.question_number,
                question_type=q.question_type,
                answer=q.answer,
                answer_confidence=q.answer_confidence,
                status=q.status,
                source_pages=q.source_pages or []
            ))

        return DocumentAnswersResponse(
            document_id=document_id,
            total_questions=len(questions),
            answered_count=answered,
            unanswered_count=unanswered,
            answers=answers
        )

    def get_review_items(self, document_id: str, owner_id: str) -> ReviewItemListResponse:
        self._verify_document_access(document_id, owner_id)
        items = self.question_repo.list_review_items(document_id)

        return ReviewItemListResponse(
            total=len(items),
            document_id=document_id,
            review_items=[ReviewItemResponse.model_validate(item) for item in items]
        )

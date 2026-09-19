from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.question import Question
from app.models.review_item import ReviewItem


class QuestionRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_questions(self, questions: List[Question]) -> List[Question]:
        for q in questions:
            self.db.add(q)
        self.db.commit()
        for q in questions:
            self.db.refresh(q)
        return questions

    def get_by_id(self, question_id: str) -> Optional[Question]:
        return self.db.query(Question).filter(Question.id == question_id).first()

    def get_by_id_and_doc(self, question_id: str, document_id: str) -> Optional[Question]:
        return self.db.query(Question).filter(
            Question.id == question_id,
            Question.document_id == document_id
        ).first()

    def list_by_document(self, document_id: str) -> List[Question]:
        return self.db.query(Question).filter(
            Question.document_id == document_id
        ).order_by(Question.created_at.asc()).all()

    def save_review_items(self, review_items: List[ReviewItem]) -> List[ReviewItem]:
        for item in review_items:
            self.db.add(item)
        self.db.commit()
        for item in review_items:
            self.db.refresh(item)
        return review_items

    def list_review_items(self, document_id: str) -> List[ReviewItem]:
        return self.db.query(ReviewItem).filter(
            ReviewItem.document_id == document_id
        ).order_by(ReviewItem.created_at.asc()).all()

    def update_question_answer(
        self,
        question: Question,
        answer: str,
        answer_confidence: float,
        status: str = "SUCCESS"
    ) -> Question:
        question.answer = answer
        question.answer_confidence = answer_confidence
        question.status = status
        self.db.commit()
        self.db.refresh(question)
        return question

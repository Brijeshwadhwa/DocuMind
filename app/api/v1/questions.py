from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.question import QuestionResponse, QuestionListResponse
from app.services.question_service import QuestionService

router = APIRouter(tags=["Questions"])


@router.get(
    "/documents/{document_id}/questions",
    response_model=QuestionListResponse,
    summary="Retrieve all extracted questions for a document",
    description=(
        "Returns all questions extracted from the document, including question number, "
        "parsed options, question type, answer, confidence scores, and source pages."
    )
)
def list_document_questions(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = QuestionService(db)
    return service.list_questions(document_id=document_id, owner_id=current_user.id)


@router.get(
    "/documents/{document_id}/questions/{question_id}",
    response_model=QuestionResponse,
    summary="Retrieve a single extracted question",
    description="Returns detailed information for a specific question, including full source traceability."
)
def get_single_question(
    document_id: str,
    question_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = QuestionService(db)
    return service.get_question(
        document_id=document_id,
        question_id=question_id,
        owner_id=current_user.id
    )

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.question import DocumentAnswersResponse
from app.services.question_service import QuestionService

router = APIRouter(tags=["Answers"])


@router.get(
    "/documents/{document_id}/answers",
    response_model=DocumentAnswersResponse,
    summary="Retrieve extracted answer keys and matched answers",
    description="Returns an aggregated summary of answers associated with the document's questions."
)
def get_document_answers(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = QuestionService(db)
    return service.get_answers(document_id=document_id, owner_id=current_user.id)

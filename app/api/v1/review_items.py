from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.review_item import ReviewItemListResponse
from app.services.question_service import QuestionService

router = APIRouter(tags=["Review"])


@router.get(
    "/documents/{document_id}/review-items",
    response_model=ReviewItemListResponse,
    summary="Retrieve extraction warnings and human-review items",
    description=(
        "Returns all items flagged for human review, including low extraction confidence, "
        "malformed options, multi-page question continuations, OCR ambiguities, and answer mismatches."
    )
)
def get_document_review_items(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = QuestionService(db)
    return service.get_review_items(document_id=document_id, owner_id=current_user.id)

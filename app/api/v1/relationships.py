from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.document import DocumentRelationshipCreate, DocumentRelationshipResponse
from app.services.relationship_service import RelationshipService

router = APIRouter(tags=["Relationships"])


@router.post(
    "/documents/{document_id}/relationships",
    response_model=DocumentRelationshipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Establish a relationship between two documents",
    description=(
        "Links a related document (e.g. separate Answer Key PDF) to a primary question paper document. "
        "When an ANSWER_KEY relationship is created, the system triggers answer key parsing "
        "and associates the answers directly into the source document's questions."
    )
)
def create_relationship(
    document_id: str,
    payload: DocumentRelationshipCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = RelationshipService(db)
    return service.create_relationship(
        source_document_id=document_id,
        payload=payload,
        owner_id=current_user.id
    )


@router.get(
    "/documents/{document_id}/relationships",
    response_model=List[DocumentRelationshipResponse],
    summary="List document relationships",
    description="Retrieves all relationships established for the specified document."
)
def list_relationships(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = RelationshipService(db)
    return service.list_relationships(
        document_id=document_id,
        owner_id=current_user.id
    )

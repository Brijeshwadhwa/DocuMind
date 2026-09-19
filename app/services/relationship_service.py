from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.document import Document, DocumentRelationship
from app.schemas.document import DocumentRelationshipCreate, DocumentRelationshipResponse
from app.repositories.document_repo import DocumentRepository
from app.processors.pipeline import DocumentPipeline
from app.core.logging import logger


class RelationshipService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DocumentRepository(db)

    def create_relationship(
        self,
        source_document_id: str,
        payload: DocumentRelationshipCreate,
        owner_id: str
    ) -> DocumentRelationshipResponse:
        # Validate source document
        source_doc = self.repo.get_by_id(source_document_id)
        if not source_doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source document not found")
        if source_doc.owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        # Validate related document
        related_doc = self.repo.get_by_id(payload.related_document_id)
        if not related_doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Related document not found")
        if related_doc.owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Related document belongs to another user")

        if source_document_id == payload.related_document_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A document cannot be related to itself"
            )

        # Check if relationship already exists
        existing = self.db.query(DocumentRelationship).filter(
            DocumentRelationship.source_document_id == source_document_id,
            DocumentRelationship.related_document_id == payload.related_document_id,
            DocumentRelationship.relationship_type == payload.relationship_type
        ).first()
        if existing:
            return DocumentRelationshipResponse.model_validate(existing)

        rel = self.repo.create_relationship(
            source_document_id=source_document_id,
            related_document_id=payload.related_document_id,
            relationship_type=payload.relationship_type
        )

        # If relationship is ANSWER_KEY, trigger re-processing / answer association for source document!
        if payload.relationship_type == "ANSWER_KEY":
            logger.info(
                f"Relationship ANSWER_KEY established between {source_document_id} and {payload.related_document_id}. "
                "Triggering source document re-association..."
            )
            pipeline = DocumentPipeline(db=self.db)
            pipeline.process_document(source_document_id)

        return DocumentRelationshipResponse.model_validate(rel)

    def list_relationships(self, document_id: str, owner_id: str) -> List[DocumentRelationshipResponse]:
        doc = self.repo.get_by_id(document_id)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        if doc.owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        rels = self.repo.get_relationships(document_id)
        return [DocumentRelationshipResponse.model_validate(r) for r in rels]

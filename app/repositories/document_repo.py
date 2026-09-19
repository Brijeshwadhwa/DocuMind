from typing import Optional, List, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.document import Document, DocumentRelationship
from app.models.processing_job import ProcessingJob
from app.models.question import Question
from app.models.review_item import ReviewItem


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_document(
        self,
        owner_id: str,
        filename: str,
        content_type: str,
        file_size: int,
        storage_path: str
    ) -> Document:
        doc = Document(
            owner_id=owner_id,
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            storage_path=storage_path,
            status="PENDING"
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_by_id(self, document_id: str) -> Optional[Document]:
        return self.db.query(Document).filter(Document.id == document_id).first()

    def get_by_id_and_owner(self, document_id: str, owner_id: str) -> Optional[Document]:
        return self.db.query(Document).filter(
            Document.id == document_id,
            Document.owner_id == owner_id
        ).first()

    def list_by_owner(
        self,
        owner_id: str,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None
    ) -> Tuple[List[Document], int]:
        query = self.db.query(Document).filter(Document.owner_id == owner_id)
        if status:
            query = query.filter(Document.status == status)

        total = query.count()
        offset = (page - 1) * limit
        items = query.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()
        return items, total

    def update_status(
        self,
        document_id: str,
        status: str,
        error: Optional[str] = None
    ) -> Optional[Document]:
        doc = self.get_by_id(document_id)
        if doc:
            doc.status = status
            doc.processing_error = error
            doc.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(doc)
        return doc

    def create_processing_job(self, document_id: str) -> ProcessingJob:
        job = ProcessingJob(
            document_id=document_id,
            status="PENDING",
            progress=0.0
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_job_by_document(self, document_id: str) -> Optional[ProcessingJob]:
        return self.db.query(ProcessingJob).filter(
            ProcessingJob.document_id == document_id
        ).order_by(ProcessingJob.started_at.desc().nullslast()).first()

    def update_job_progress(
        self,
        job_id: str,
        status: str,
        progress: float,
        error: Optional[str] = None
    ) -> Optional[ProcessingJob]:
        job = self.db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if job:
            job.status = status
            job.progress = progress
            if error:
                job.error = error
            if status == "PROCESSING" and not job.started_at:
                job.started_at = datetime.now(timezone.utc)
            elif status in ("COMPLETED", "FAILED"):
                job.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(job)
        return job

    def get_document_counts(self, document_id: str) -> Tuple[int, int]:
        total_questions = self.db.query(Question).filter(Question.document_id == document_id).count()
        total_review_items = self.db.query(ReviewItem).filter(ReviewItem.document_id == document_id).count()
        return total_questions, total_review_items

    def create_relationship(
        self,
        source_document_id: str,
        related_document_id: str,
        relationship_type: str = "ANSWER_KEY"
    ) -> DocumentRelationship:
        rel = DocumentRelationship(
            source_document_id=source_document_id,
            related_document_id=related_document_id,
            relationship_type=relationship_type
        )
        self.db.add(rel)
        self.db.commit()
        self.db.refresh(rel)
        return rel

    def get_relationships(self, document_id: str) -> List[DocumentRelationship]:
        return self.db.query(DocumentRelationship).filter(
            (DocumentRelationship.source_document_id == document_id) |
            (DocumentRelationship.related_document_id == document_id)
        ).all()

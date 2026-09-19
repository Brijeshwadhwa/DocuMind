import os
import uuid
import re
from typing import Tuple, List, Optional
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentStatusResponse,
    DocumentListResponse
)
from app.repositories.document_repo import DocumentRepository
from app.workers.celery_tasks import dispatch_document_processing


class DocumentService:
    # Magic bytes signatures for file validation
    MAGIC_BYTES = {
        "pdf": b"%PDF-",
        "png": b"\x89PNG\r\n\x1a\n",
        "jpg": b"\xff\xd8\xff",
        "jpeg": b"\xff\xd8\xff",
    }

    ALLOWED_MIME_TYPES = {
        "application/pdf": "pdf",
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
    }

    def __init__(self, db: Session):
        self.db = db
        self.repo = DocumentRepository(db)

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize filename to prevent directory traversal or invalid characters."""
        clean = os.path.basename(filename)
        clean = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", clean)
        return clean or "uploaded_document"

    def upload_document(self, file: UploadFile, owner_id: str) -> DocumentUploadResponse:
        """
        Validates, securely stores, and enqueues document for asynchronous processing.
        """
        # 1. Validate file content type and extension
        original_filename = self.sanitize_filename(file.filename or "unknown.pdf")
        extension = os.path.splitext(original_filename)[1].lstrip(".").lower()

        if extension not in settings.allowed_extensions_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file extension '{extension}'. Allowed extensions: {', '.join(settings.allowed_extensions_list)}"
            )

        content_type = (file.content_type or "").lower()
        if content_type not in self.ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported media type '{content_type}'. Must be application/pdf, image/png, or image/jpeg"
            )

        # 2. Read file contents and validate file size
        file_bytes = file.file.read()
        file_size = len(file_bytes)

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes)"
            )

        if file_size > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB"
            )

        # 3. Magic bytes validation to prevent disguised file formats
        expected_sig = self.MAGIC_BYTES.get(extension)
        if expected_sig and not file_bytes.startswith(expected_sig):
            # For JPEG, check prefix bytes
            if extension in ("jpg", "jpeg") and file_bytes[:3] == b"\xff\xd8\xff":
                pass
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Malformed file: file content header does not match declared format '{extension}'"
                )

        # 4. Save to disk using safe UUID storage path
        storage_filename = f"{uuid.uuid4().hex}_{original_filename}"
        storage_path = os.path.abspath(os.path.join(settings.UPLOAD_DIR, storage_filename))

        with open(storage_path, "wb") as f:
            f.write(file_bytes)

        # 5. Persist document metadata and job record in DB
        doc = self.repo.create_document(
            owner_id=owner_id,
            filename=original_filename,
            content_type=content_type,
            file_size=file_size,
            storage_path=storage_path
        )
        job = self.repo.create_processing_job(document_id=doc.id)

        # 6. Queue background worker task (non-blocking)
        dispatch_document_processing(doc.id, db=self.db)

        logger.info(f"Document {doc.id} uploaded by user {owner_id} ({doc.filename}, {file_size} bytes)")

        return DocumentUploadResponse(
            document_id=doc.id,
            job_id=job.id,
            filename=doc.filename,
            content_type=doc.content_type,
            file_size=doc.file_size,
            status=doc.status,
            message="Document uploaded successfully and queued for background processing."
        )

    def get_document(self, document_id: str, owner_id: str) -> DocumentResponse:
        doc = self.repo.get_by_id(document_id)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        if doc.owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access to document forbidden")
        return DocumentResponse.model_validate(doc)

    def list_documents(
        self,
        owner_id: str,
        page: int = 1,
        limit: int = 20,
        status_filter: Optional[str] = None
    ) -> DocumentListResponse:
        docs, total = self.repo.list_by_owner(
            owner_id=owner_id,
            page=page,
            limit=limit,
            status=status_filter
        )
        return DocumentListResponse(
            total=total,
            page=page,
            limit=limit,
            documents=[DocumentResponse.model_validate(d) for d in docs]
        )

    def get_document_status(self, document_id: str, owner_id: str) -> DocumentStatusResponse:
        doc = self.repo.get_by_id(document_id)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        if doc.owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access to document forbidden")

        job = self.repo.get_job_by_document(document_id)
        progress = job.progress if job else (100.0 if doc.status == "COMPLETED" else 0.0)
        q_count, r_count = self.repo.get_document_counts(document_id)

        return DocumentStatusResponse(
            document_id=doc.id,
            status=doc.status,
            progress=progress,
            processing_error=doc.processing_error,
            total_questions=q_count,
            total_review_items=r_count,
            created_at=doc.created_at,
            updated_at=doc.updated_at
        )

from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentListResponse,
    DocumentStatusResponse
)
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload an examination document or image",
    description=(
        "Accepts PDF, PNG, or JPEG documents containing question papers. "
        "Validates magic bytes and file size, saves securely, creates background job, "
        "and immediately returns document metadata and job ID for polling."
    )
)
def upload_document(
    file: UploadFile = File(..., description="PDF or Image examination document"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = DocumentService(db)
    return service.upload_document(file=file, owner_id=current_user.id)


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List uploaded documents",
    description="Returns a paginated list of documents uploaded by the authenticated user."
)
def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status: PENDING, PROCESSING, COMPLETED, FAILED"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = DocumentService(db)
    return service.list_documents(
        owner_id=current_user.id,
        page=page,
        limit=limit,
        status_filter=status
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
    description="Retrieves metadata for a specific document owned by the authenticated user."
)
def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = DocumentService(db)
    return service.get_document(document_id=document_id, owner_id=current_user.id)


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    summary="Poll document processing status",
    description=(
        "Allows polling the real-time background processing status, progress percentage (0-100%), "
        "and extracted item counts."
    )
)
def get_document_status(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = DocumentService(db)
    return service.get_document_status(document_id=document_id, owner_id=current_user.id)

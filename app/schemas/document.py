from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class DocumentUploadResponse(BaseModel):
    document_id: str
    job_id: str
    filename: str
    content_type: str
    file_size: int
    status: str
    message: str = "Document uploaded successfully and queued for processing."


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    filename: str
    content_type: str
    file_size: int
    status: str
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    total: int
    page: int
    limit: int
    documents: List[DocumentResponse]


class DocumentStatusResponse(BaseModel):
    document_id: str
    status: str
    progress: float
    processing_error: Optional[str] = None
    total_questions: int = 0
    total_review_items: int = 0
    created_at: datetime
    updated_at: datetime


class DocumentRelationshipCreate(BaseModel):
    related_document_id: str = Field(..., description="UUID of the related document (e.g., answer key document)")
    relationship_type: str = Field(default="ANSWER_KEY", description="Relationship type: ANSWER_KEY, SUPPLEMENTARY")


class DocumentRelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_document_id: str
    related_document_id: str
    relationship_type: str
    created_at: datetime

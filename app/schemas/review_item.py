from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ReviewItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    question_id: Optional[str] = None
    issue_type: str
    message: str
    confidence: Optional[float] = None
    status: str
    created_at: datetime


class ReviewItemListResponse(BaseModel):
    total: int
    document_id: str
    review_items: List[ReviewItemResponse]

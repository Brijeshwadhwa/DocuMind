import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class ReviewItem(Base):
    __tablename__ = "review_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(String(36), ForeignKey("questions.id", ondelete="SET NULL"), nullable=True, index=True)
    issue_type = Column(String(100), nullable=False, index=True)
    # Types: LOW_EXTRACTION_CONFIDENCE, LOW_CONFIDENCE_ANSWER, MALFORMED_OPTIONS,
    #        MULTI_PAGE_SPAN, UNMATCHED_ANSWER_KEY, MISSING_QUESTION_NUMBER, OCR_UNCERTAINTY
    message = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)
    status = Column(String(50), default="OPEN", nullable=False)  # OPEN, RESOLVED, DISMISSED
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document", back_populates="review_items")
    question = relationship("Question", back_populates="review_items")

    def __repr__(self) -> str:
        return f"<ReviewItem id={self.id} type={self.issue_type} status={self.status}>"

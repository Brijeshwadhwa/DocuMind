import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class Question(Base):
    __tablename__ = "questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    question_number = Column(String(50), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), default="MCQ", nullable=False)  # MCQ, TRUE_FALSE, SHORT_ANSWER, UNKNOWN
    options = Column(JSON, nullable=True, default=dict)  # {"A": "...", "B": "..."}
    answer = Column(String(255), nullable=True)
    answer_confidence = Column(Float, nullable=True)
    extraction_confidence = Column(Float, default=1.0, nullable=False)
    status = Column(String(50), default="SUCCESS", nullable=False)  # SUCCESS, REVIEW_REQUIRED, PARTIAL
    source_pages = Column(JSON, nullable=False, default=list)  # [1] or [1, 2]
    source_text = Column(Text, nullable=True)
    metadata_info = Column("metadata", JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    document = relationship("Document", back_populates="questions")
    review_items = relationship("ReviewItem", back_populates="question", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Question id={self.id} num={self.question_number} type={self.question_type} status={self.status}>"

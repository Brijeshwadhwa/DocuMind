import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default="PENDING", index=True, nullable=False)  # PENDING, PROCESSING, COMPLETED, FAILED
    progress = Column(Float, default=0.0, nullable=False)  # 0.0 - 100.0
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    document = relationship("Document", back_populates="jobs")

    def __repr__(self) -> str:
        return f"<ProcessingJob id={self.id} doc={self.document_id} status={self.status} progress={self.progress}%>"

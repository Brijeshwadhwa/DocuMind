import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_path = Column(String(500), nullable=False)
    status = Column(String(50), default="PENDING", index=True, nullable=False)  # PENDING, PROCESSING, COMPLETED, FAILED
    processing_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    owner = relationship("User", back_populates="documents")
    questions = relationship("Question", back_populates="document", cascade="all, delete-orphan")
    review_items = relationship("ReviewItem", back_populates="document", cascade="all, delete-orphan")
    jobs = relationship("ProcessingJob", back_populates="document", cascade="all, delete-orphan")

    related_sources = relationship(
        "DocumentRelationship",
        foreign_keys="DocumentRelationship.source_document_id",
        back_populates="source_document",
        cascade="all, delete-orphan"
    )
    related_targets = relationship(
        "DocumentRelationship",
        foreign_keys="DocumentRelationship.related_document_id",
        back_populates="related_document",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename} status={self.status}>"


class DocumentRelationship(Base):
    __tablename__ = "document_relationships"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    source_document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    related_document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String(50), default="ANSWER_KEY", nullable=False)  # ANSWER_KEY, SUPPLEMENTARY, etc.
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    source_document = relationship("Document", foreign_keys=[source_document_id], back_populates="related_sources")
    related_document = relationship("Document", foreign_keys=[related_document_id], back_populates="related_targets")

    def __repr__(self) -> str:
        return f"<DocumentRelationship source={self.source_document_id} related={self.related_document_id} type={self.relationship_type}>"

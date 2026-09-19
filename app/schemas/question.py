from typing import Optional, Dict, List, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    source_document_id: str = Field(..., validation_alias="document_id")
    document_id: str = Field(..., validation_alias="document_id")
    question_number: str
    question: str = Field(..., validation_alias="question_text")
    question_text: str = Field(..., validation_alias="question_text")
    question_type: str  # MCQ, TRUE_FALSE, SHORT_ANSWER, UNKNOWN
    options: Optional[Dict[str, str]] = None
    answer: Optional[str] = None
    answer_confidence: Optional[float] = None
    solution: Optional[str] = None
    explanation: Optional[str] = None
    extraction_confidence: float
    status: str  # SUCCESS, REVIEW_REQUIRED, PARTIAL
    source_pages: List[int]
    source_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, validation_alias="metadata_info")
    created_at: datetime
    updated_at: datetime

    @classmethod
    def model_validate(cls, obj: Any, *args, **kwargs) -> "QuestionResponse":
        instance = super().model_validate(obj, *args, **kwargs)
        meta = instance.metadata or {}
        if not instance.solution:
            instance.solution = meta.get("solution") or meta.get("explanation")
        if not instance.explanation:
            instance.explanation = instance.solution
        return instance


class QuestionListResponse(BaseModel):
    total: int
    document_id: str
    questions: List[QuestionResponse]


class AnswerItemResponse(BaseModel):
    question_id: str
    question_number: str
    question_type: str
    answer: Optional[str]
    answer_confidence: Optional[float]
    status: str
    source_pages: List[int]


class DocumentAnswersResponse(BaseModel):
    document_id: str
    total_questions: int
    answered_count: int
    unanswered_count: int
    answers: List[AnswerItemResponse]

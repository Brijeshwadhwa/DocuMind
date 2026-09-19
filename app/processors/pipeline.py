import os
import traceback
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.logging import logger
from app.models.document import Document, DocumentRelationship
from app.models.processing_job import ProcessingJob
from app.models.question import Question
from app.models.review_item import ReviewItem
from app.processors.pdf_processor import DocumentExtractor, PageData
from app.processors.question_segmenter import QuestionSegmenter, RawQuestion
from app.processors.answer_key_parser import AnswerKeyParser, AnswerMatch
from app.processors.confidence_scorer import ConfidenceEvaluator, QuestionEvaluation


class DocumentPipeline:
    """
    End-to-end document processing pipeline:
    Validates file -> Preprocesses & Extracts pages -> Runs OCR fallback ->
    Segments questions -> Extracts options -> Parses & Associates answer keys ->
    Calculates multi-factor confidence -> Generates ReviewItems -> Persists results.
    """

    def __init__(self, db: Optional[Session] = None):
        self._db = db
        self.extractor = DocumentExtractor()

    def process_document(self, document_id: str) -> bool:
        """
        Executes the processing pipeline for a single document.
        Can be called by Celery workers or synchronously.
        """
        db = self._db or SessionLocal()
        should_close_db = self._db is None

        try:
            logger.info(f"Starting processing pipeline for document_id={document_id}")

            # 1. Fetch document and processing job
            doc: Optional[Document] = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                logger.error(f"Document {document_id} not found in database")
                return False

            job: Optional[ProcessingJob] = db.query(ProcessingJob).filter(
                ProcessingJob.document_id == document_id
            ).order_by(ProcessingJob.started_at.desc().nullslast()).first()

            if not job:
                job = ProcessingJob(document_id=document_id)
                db.add(job)
                db.commit()
                db.refresh(job)

            # Update status to PROCESSING (10%)
            doc.status = "PROCESSING"
            job.status = "PROCESSING"
            job.progress = 10.0
            db.commit()

            # 2. Validate file on disk
            if not os.path.exists(doc.storage_path):
                raise FileNotFoundError(f"Stored file does not exist at {doc.storage_path}")

            # 3. Extract text per page (Native + OCR fallback) (30%)
            logger.info(f"Extracting pages from {doc.filename} ({doc.content_type})")
            if doc.content_type == "application/pdf" or doc.filename.lower().endswith(".pdf"):
                pages = self.extractor.process_pdf(doc.storage_path)
            else:
                pages = self.extractor.process_image(doc.storage_path)

            pages_map = {p.page_number: p for p in pages}
            job.progress = 40.0
            db.commit()

            # 4. Check for related answer key documents
            related_rels = db.query(DocumentRelationship).filter(
                DocumentRelationship.source_document_id == document_id,
                DocumentRelationship.relationship_type == "ANSWER_KEY"
            ).all()

            external_answer_key_text = ""
            for rel in related_rels:
                rel_doc = db.query(Document).filter(Document.id == rel.related_document_id).first()
                if rel_doc and os.path.exists(rel_doc.storage_path):
                    logger.info(f"Found related answer key document {rel_doc.filename}")
                    if rel_doc.content_type == "application/pdf" or rel_doc.filename.lower().endswith(".pdf"):
                        rel_pages = self.extractor.process_pdf(rel_doc.storage_path)
                    else:
                        rel_pages = self.extractor.process_image(rel_doc.storage_path)
                    external_answer_key_text += "\n" + "\n".join(p.text for p in rel_pages)

            # 5. Question Segmentation (60%)
            raw_questions, internal_answer_key_text = QuestionSegmenter.segment_questions(pages)
            logger.info(f"Segmented {len(raw_questions)} questions from {doc.filename}")
            job.progress = 65.0
            db.commit()

            # 6. Parse and match answer key (75%)
            combined_answer_key_text = f"{internal_answer_key_text}\n{external_answer_key_text}".strip()
            answer_map = AnswerKeyParser.parse_answer_key(combined_answer_key_text)
            answer_matches = AnswerKeyParser.associate_answers(raw_questions, answer_map)
            match_dict = {m.question_number: m for m in answer_matches}

            job.progress = 80.0
            db.commit()

            # 7. Evaluate confidence & generate ReviewItems (90%)
            # Delete any existing questions and review items for this doc (for re-processing)
            db.query(Question).filter(Question.document_id == document_id).delete()
            db.query(ReviewItem).filter(ReviewItem.document_id == document_id).delete()
            db.commit()

            saved_questions = []
            for raw_q in raw_questions:
                match = match_dict.get(raw_q.question_number)
                evaluation: QuestionEvaluation = ConfidenceEvaluator.evaluate_question(
                    raw_q, match, pages_map
                )

                q_model = Question(
                    document_id=document_id,
                    question_number=raw_q.question_number,
                    question_text=raw_q.question_text,
                    question_type=raw_q.question_type,
                    options=raw_q.options,
                    answer=match.answer if match else None,
                    answer_confidence=match.confidence if match else None,
                    extraction_confidence=evaluation.extraction_confidence,
                    status=evaluation.status,
                    source_pages=raw_q.source_pages,
                    source_text=raw_q.source_text,
                    metadata_info=raw_q.metadata
                )
                db.add(q_model)
                db.flush()  # Flush to generate q_model.id

                # Create ReviewItems for any flagged issues
                for issue in evaluation.review_issues:
                    rev_item = ReviewItem(
                        document_id=document_id,
                        question_id=q_model.id,
                        issue_type=issue["issue_type"],
                        message=issue["message"],
                        confidence=issue.get("confidence"),
                        status="OPEN"
                    )
                    db.add(rev_item)

                saved_questions.append(q_model)

            # If no questions were found at all in a non-empty document, create a document-level review item
            if not saved_questions:
                total_text_len = sum(len(p.text.strip()) for p in pages)
                rev_item = ReviewItem(
                    document_id=document_id,
                    question_id=None,
                    issue_type="NO_QUESTIONS_FOUND",
                    message=(
                        f"No structured questions could be extracted. "
                        f"Extracted {total_text_len} characters across {len(pages)} pages."
                    ),
                    confidence=0.10,
                    status="OPEN"
                )
                db.add(rev_item)

            # Check if this document is an answer key for another source document
            # If so, re-trigger the source document's association!
            inverse_rels = db.query(DocumentRelationship).filter(
                DocumentRelationship.related_document_id == document_id,
                DocumentRelationship.relationship_type == "ANSWER_KEY"
            ).all()
            for inv_rel in inverse_rels:
                self._reassociate_source_document_answers(db, inv_rel.source_document_id, doc.storage_path)

            # 8. Mark COMPLETED (100%)
            doc.status = "COMPLETED"
            doc.processing_error = None
            job.status = "COMPLETED"
            job.progress = 100.0
            db.commit()
            logger.info(f"Successfully finished processing document_id={document_id}")
            return True

        except Exception as e:
            db.rollback()
            err_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Pipeline error processing document {document_id}: {err_msg}\n{traceback.format_exc()}")

            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = "FAILED"
                doc.processing_error = err_msg

            job = db.query(ProcessingJob).filter(
                ProcessingJob.document_id == document_id
            ).order_by(ProcessingJob.started_at.desc().nullslast()).first()
            if job:
                job.status = "FAILED"
                job.error = err_msg

            # Create document level review item for the failure
            fail_item = ReviewItem(
                document_id=document_id,
                question_id=None,
                issue_type="PROCESSING_ERROR",
                message=f"Document processing failed: {err_msg}",
                confidence=0.0,
                status="OPEN"
            )
            db.add(fail_item)
            db.commit()
            return False

        finally:
            if should_close_db:
                db.close()

    def _reassociate_source_document_answers(
        self,
        db: Session,
        source_doc_id: str,
        answer_key_path: str
    ) -> None:
        """
        When an answer key document finishes processing, this updates the source document's
        existing questions with the newly parsed answer keys.
        """
        try:
            logger.info(f"Re-associating answers for source document {source_doc_id} from answer key {answer_key_path}")
            if answer_key_path.lower().endswith(".pdf"):
                ak_pages = self.extractor.process_pdf(answer_key_path)
            else:
                ak_pages = self.extractor.process_image(answer_key_path)

            ak_text = "\n".join(p.text for p in ak_pages)
            answer_map = AnswerKeyParser.parse_answer_key(ak_text)

            questions = db.query(Question).filter(Question.document_id == source_doc_id).all()
            for q in questions:
                q_num = str(q.question_number)
                if q_num in answer_map:
                    ans_val = answer_map[q_num]
                    # Check options
                    if q.options and ans_val in [k.upper() for k in q.options.keys()]:
                        q.answer = ans_val
                        q.answer_confidence = 0.95
                        q.status = "SUCCESS"
                    else:
                        q.answer = ans_val
                        q.answer_confidence = 0.85
            db.commit()
            logger.info(f"Re-associated {len(answer_map)} answers for document {source_doc_id}")
        except Exception as e:
            logger.warning(f"Failed to re-associate answers for source document {source_doc_id}: {e}")

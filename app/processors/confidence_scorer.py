from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
from app.processors.question_segmenter import RawQuestion
from app.processors.answer_key_parser import AnswerMatch
from app.processors.pdf_processor import PageData


@dataclass
class QuestionEvaluation:
    extraction_confidence: float
    status: str  # SUCCESS, REVIEW_REQUIRED, PARTIAL
    review_issues: List[Dict[str, Any]]


class ConfidenceEvaluator:
    """
    Transparent confidence calculation engine and ReviewItem generator.
    Evaluates extraction fidelity, option structure, OCR clarity, and answer matching.
    """

    @classmethod
    def evaluate_question(
        cls,
        q: RawQuestion,
        answer_match: Optional[AnswerMatch],
        pages_map: Dict[int, PageData]
    ) -> QuestionEvaluation:
        issues: List[Dict[str, Any]] = []

        # 1. Question number presence & validity (0.20 max)
        score_qnum = 0.20 if q.question_number and q.question_number.isdigit() else 0.10
        if not q.question_number:
            issues.append({
                "issue_type": "MISSING_QUESTION_NUMBER",
                "message": "Question lacks a clear numeric identifier",
                "confidence": 0.40
            })

        # 2. Question text length and completeness (0.25 max)
        text_len = len(q.question_text.strip())
        if text_len >= 25:
            score_text = 0.25
        elif text_len >= 10:
            score_text = 0.15
        else:
            score_text = 0.05
            issues.append({
                "issue_type": "INCOMPLETE_QUESTION",
                "message": f"Question text is unusually short ({text_len} characters)",
                "confidence": 0.50
            })

        # 3. Options structure (0.30 max)
        if q.question_type == "MCQ":
            num_opts = len(q.options)
            if num_opts >= 4:
                score_opts = 0.30
            elif num_opts == 3:
                score_opts = 0.22
                issues.append({
                    "issue_type": "MALFORMED_OPTIONS",
                    "message": f"Question has only {num_opts} options instead of standard 4",
                    "confidence": 0.75
                })
            elif num_opts == 2:
                score_opts = 0.15
                issues.append({
                    "issue_type": "MALFORMED_OPTIONS",
                    "message": "Question has only 2 options",
                    "confidence": 0.65
                })
            elif num_opts == 1:
                score_opts = 0.05
                issues.append({
                    "issue_type": "MALFORMED_OPTIONS",
                    "message": "Question has only 1 option (options B, C, D missing or unparsed)",
                    "confidence": 0.40
                })
            else:
                score_opts = 0.0
                issues.append({
                    "issue_type": "MALFORMED_OPTIONS",
                    "message": "MCQ has insufficient options (< 2)",
                    "confidence": 0.30
                })
        elif q.question_type == "TRUE_FALSE":
            score_opts = 0.30
        elif q.question_type == "SHORT_ANSWER":
            # Ends with punctuation or question mark
            if q.question_text.rstrip().endswith(("?", ".", ":")):
                score_opts = 0.30
            else:
                score_opts = 0.20
        else:
            score_opts = 0.10

        # 4. OCR / Page quality (0.25 max)
        # Average OCR confidence across question's source pages
        page_confs = [
            pages_map[p].ocr_confidence
            for p in q.source_pages
            if p in pages_map
        ]
        avg_page_conf = (sum(page_confs) / len(page_confs)) if page_confs else 1.0
        score_ocr = round(0.25 * avg_page_conf, 3)

        has_scanned_page = any(pages_map[p].is_scanned for p in q.source_pages if p in pages_map)
        if has_scanned_page and avg_page_conf < 0.75:
            issues.append({
                "issue_type": "OCR_UNCERTAINTY",
                "message": f"Question extracted from scanned page with low OCR fidelity ({avg_page_conf:.2f})",
                "confidence": round(avg_page_conf, 2)
            })

        # 5. Multi-page spanning check
        if q.is_multipage:
            issues.append({
                "issue_type": "MULTI_PAGE_SPAN",
                "message": f"Question spans across multiple pages: {q.source_pages}",
                "confidence": 0.85
            })

        # Calculate final extraction confidence (capped between 0.05 and 1.0)
        total_confidence = round(min(max(score_qnum + score_text + score_opts + score_ocr, 0.05), 1.0), 2)

        # 6. Answer key checks
        if answer_match:
            if not answer_match.is_matched and answer_match.issue_message:
                issues.append({
                    "issue_type": "LOW_CONFIDENCE_ANSWER",
                    "message": answer_match.issue_message,
                    "confidence": answer_match.confidence or 0.40
                })

        # Determine question status
        if total_confidence >= 0.90 and not any(i["issue_type"] in ("MALFORMED_OPTIONS", "INCOMPLETE_QUESTION") for i in issues):
            status = "SUCCESS"
        elif total_confidence >= 0.70:
            status = "PARTIAL" if any(i["issue_type"] == "MALFORMED_OPTIONS" for i in issues) else "SUCCESS"
        else:
            status = "REVIEW_REQUIRED"
            issues.append({
                "issue_type": "LOW_EXTRACTION_CONFIDENCE",
                "message": f"Extraction confidence ({total_confidence:.2f}) falls below 0.70 threshold",
                "confidence": total_confidence
            })

        return QuestionEvaluation(
            extraction_confidence=total_confidence,
            status=status,
            review_issues=issues
        )

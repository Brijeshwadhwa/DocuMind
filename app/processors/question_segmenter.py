import re
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from app.processors.pdf_processor import PageData
from app.core.logging import logger


@dataclass
class RawQuestion:
    question_number: str
    question_text: str
    question_type: str  # MCQ, TRUE_FALSE, SHORT_ANSWER, UNKNOWN
    options: Dict[str, str] = field(default_factory=dict)
    source_pages: List[int] = field(default_factory=list)
    source_text: str = ""
    is_multipage: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class QuestionSegmenter:
    """
    Robust question segmentation engine supporting various question numbering formats,
    multi-page spanning, option extraction, and type classification.
    """

    # Regex to detect question starts:
    # 1. 1. text
    # 2. 1) text
    # 3. Q1. text, Q. 1 text, Question 1: text, Question 1. text
    # 4. (1) text, [1] text
    QUESTION_START_REGEX = re.compile(
        r"^(?:(?:Q(?:uestion)?[\.\s]*(\d+))|(\d+)[\.\)]|\((\d+)\)|\[(\d+)\])(?:[\.\:\-\s]+)(.*)$",
        re.IGNORECASE
    )

    # Regex for finding multiple inline options on a line or a single option start:
    # Matches (A), [A], A., A)
    OPTION_TOKEN_REGEX = re.compile(
        r"(?:^|\s+)(?:\(?([A-Da-d1-4])[\.\)]|\[([A-Da-d1-4])\]|\(([A-Da-d1-4])\))\s*"
    )

    # Detect Answer Key section header
    ANSWER_KEY_HEADER_REGEX = re.compile(
        r"^(?:answer\s*keys?|answers?|solutions?|key\s*answers?)\b[\s\:\-]*$",
        re.IGNORECASE
    )

    # Common document header/footer patterns to avoid polluting multi-page questions
    HEADER_FOOTER_REGEX = re.compile(
        r"^(?:.*examination.*|.*assessment.*|.*part\s+[iIvVxX]+.*|page\s+\d+.*|.*quiz.*|subject\s*\:.*)$",
        re.IGNORECASE
    )

    @classmethod
    def segment_questions(cls, pages: List[PageData]) -> Tuple[List[RawQuestion], str]:
        """
        Segment questions across pages.
        Returns:
            - List of extracted RawQuestion objects
            - Isolated answer-key text block (if present in document)
        """
        questions: List[RawQuestion] = []
        answer_key_text_accum = []

        current_q_num: Optional[str] = None
        current_q_lines: List[str] = []
        current_options: Dict[str, str] = {}
        current_opt_key: Optional[str] = None
        current_pages: List[int] = []
        current_source_lines: List[str] = []

        in_answer_key_section = False

        for page in pages:
            page_num = page.page_number
            lines = page.text.splitlines()

            for line_idx, line in enumerate(lines):
                raw_line = line
                line = line.strip()
                if not line:
                    continue

                # Check if we reached the answer key section
                if cls.ANSWER_KEY_HEADER_REGEX.match(line):
                    in_answer_key_section = True
                    # Close current question if open
                    if current_q_num:
                        cls._finalize_question(
                            questions, current_q_num, current_q_lines,
                            current_options, current_pages, current_source_lines
                        )
                        current_q_num = None
                        current_q_lines, current_options, current_pages, current_source_lines = [], {}, [], []
                        current_opt_key = None
                    answer_key_text_accum.append(line)
                    continue

                if in_answer_key_section:
                    answer_key_text_accum.append(line)
                    continue

                # Check if line is a page header/footer on subsequent pages and ignore it
                if current_q_num and page_num > current_pages[0] and line_idx < 3:
                    if cls.HEADER_FOOTER_REGEX.match(line):
                        logger.debug(f"Ignoring page header line on page {page_num}: {line}")
                        continue

                # Check if line is a new Question start
                q_match = cls.QUESTION_START_REGEX.match(line)
                if q_match:
                    # Finalize previous question if open
                    if current_q_num:
                        cls._finalize_question(
                            questions, current_q_num, current_q_lines,
                            current_options, current_pages, current_source_lines
                        )

                    # Extract question number
                    q_num = (
                        q_match.group(1) or
                        q_match.group(2) or
                        q_match.group(3) or
                        q_match.group(4)
                    )
                    remainder = q_match.group(5).strip()

                    current_q_num = q_num
                    current_q_lines = [remainder] if remainder else []
                    current_options = {}
                    current_opt_key = None
                    current_pages = [page_num]
                    current_source_lines = [raw_line]
                    continue

                # If no question is active yet, ignore document header lines
                if not current_q_num:
                    continue

                # Track current page for open question (multi-page continuation)
                if page_num not in current_pages:
                    current_pages.append(page_num)
                current_source_lines.append(raw_line)

                # Check for options on this line (supports single or multiple inline options)
                extracted_opts = cls._extract_options_from_line(line)
                if extracted_opts:
                    current_options.update(extracted_opts)
                    # The active option key becomes the last option extracted
                    current_opt_key = list(extracted_opts.keys())[-1]
                    continue

                # Continuation line
                if current_opt_key:
                    # Append line to currently active option
                    current_options[current_opt_key] += " " + line
                else:
                    # Append line to active question prompt
                    current_q_lines.append(line)

        # Finalize last active question
        if current_q_num:
            cls._finalize_question(
                questions, current_q_num, current_q_lines,
                current_options, current_pages, current_source_lines
            )

        answer_key_text = "\n".join(answer_key_text_accum)
        return questions, answer_key_text

    @classmethod
    def _extract_options_from_line(cls, line: str) -> Optional[Dict[str, str]]:
        """
        Extract options from a line, handling:
        - Single option: 'A. Delhi' or '(A) Delhi'
        - Multiple inline options: 'A. 1965  B. 1969  C. 1972  D. 1975'
        """
        matches = list(cls.OPTION_TOKEN_REGEX.finditer(line))
        if not matches:
            return None

        # Verify that the first match starts near the beginning of the line or after whitespace
        if matches[0].start() > 5 and not line[:matches[0].start()].isspace():
            # Match is embedded inside regular sentence, not an option label
            return None

        options: Dict[str, str] = {}
        for i, m in enumerate(matches):
            raw_key = m.group(1) or m.group(2) or m.group(3)
            if not raw_key:
                continue

            opt_key = raw_key.upper()
            norm_key = {"1": "A", "2": "B", "3": "C", "4": "D"}.get(opt_key, opt_key)

            start = m.end()
            end = matches[i + 1].start() if (i + 1) < len(matches) else len(line)
            opt_val = line[start:end].strip()

            options[norm_key] = opt_val

        return options if options else None

    @classmethod
    def _finalize_question(
        cls,
        questions: List[RawQuestion],
        q_num: str,
        q_lines: List[str],
        options: Dict[str, str],
        pages: List[int],
        source_lines: List[str]
    ) -> None:
        q_text = " ".join(q_lines).strip()
        source_text = "\n".join(source_lines).strip()

        # Clean option texts
        cleaned_options = {k: v.strip() for k, v in options.items() if v.strip()}

        # Classify question type
        q_type = cls._classify_question_type(q_text, cleaned_options)

        raw_q = RawQuestion(
            question_number=str(q_num),
            question_text=q_text if q_text else f"Question {q_num}",
            question_type=q_type,
            options=cleaned_options,
            source_pages=sorted(list(set(pages))),
            source_text=source_text,
            is_multipage=len(set(pages)) > 1,
            metadata={
                "option_count": len(cleaned_options),
                "is_multipage": len(set(pages)) > 1,
                "character_length": len(q_text)
            }
        )
        questions.append(raw_q)

    @classmethod
    def _classify_question_type(cls, question_text: str, options: Dict[str, str]) -> str:
        """Classify question into MCQ, TRUE_FALSE, SHORT_ANSWER, or UNKNOWN."""
        lower_text = question_text.lower()
        opt_values = [v.lower().strip() for v in options.values()]

        # Check for True/False
        if set(opt_values) == {"true", "false"} or "true or false" in lower_text or "state whether true" in lower_text:
            return "TRUE_FALSE"

        # Check for MCQ (has options)
        if len(options) >= 1:
            return "MCQ"

        # Check for Short Answer / Essay / Fill-in-the-blank
        if len(options) == 0:
            if any(term in lower_text for term in ["what", "why", "how", "explain", "describe", "define", "calculate", "fill in", "?"]):
                return "SHORT_ANSWER"
            return "UNKNOWN"

        return "UNKNOWN"

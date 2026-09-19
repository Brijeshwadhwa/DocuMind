import re
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from app.processors.question_segmenter import RawQuestion
from app.core.logging import logger


@dataclass
class AnswerMatch:
    question_number: str
    answer: Optional[str]
    confidence: Optional[float]
    is_matched: bool
    issue_message: Optional[str] = None


class AnswerKeyParser:
    """
    Parses answer keys from document text or separate answer-key documents
    and associates them with extracted questions.
    """

    # Answer patterns:
    # 1. 1-A, 1 - B, 1 - (C)
    # 2. 1. A, 1. (A), 1. [A]
    # 3. Q1: A, Q. 1: B, Q1 - C
    # 4. 1: A, 2: B
    # 5. 1 (A), 2 (B)
    ANSWER_PAIR_REGEXES = [
        re.compile(r"(?:Q(?:uestion)?[\.\s]*)?(\d+)[\s\.\:\-]+(?:\(?([A-Za-z]|True|False)\)?)", re.IGNORECASE),
        re.compile(r"(\d+)\s*\((([A-Za-z]|True|False))\)", re.IGNORECASE),
        re.compile(r"(\d+)\s*\|\s*([A-Za-z]|True|False)", re.IGNORECASE),
    ]

    @classmethod
    def parse_answer_key(cls, text: str) -> Dict[str, str]:
        """
        Parse answer key mappings {question_number: answer} from given text.
        """
        answers: Dict[str, str] = {}
        if not text:
            return answers

        lines = text.splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Try each regex pattern
            for pattern in cls.ANSWER_PAIR_REGEXES:
                matches = pattern.findall(line)
                for q_num, ans in matches:
                    norm_num = str(q_num).strip()
                    norm_ans = ans.strip().upper()
                    # If multiple entries appear, keep the first or consistent
                    if norm_num not in answers:
                        answers[norm_num] = norm_ans

        logger.debug(f"Extracted {len(answers)} answer key entries: {answers}")
        return answers

    @classmethod
    def associate_answers(
        cls,
        questions: List[RawQuestion],
        answer_key: Dict[str, str]
    ) -> List[AnswerMatch]:
        """
        Associate parsed answer key entries with question list.
        Validates answer feasibility against question options and computes confidence.
        """
        matches: List[AnswerMatch] = []

        for q in questions:
            q_num = str(q.question_number)
            if q_num not in answer_key:
                matches.append(AnswerMatch(
                    question_number=q_num,
                    answer=None,
                    confidence=None,
                    is_matched=False,
                    issue_message=f"No answer key entry found for Question {q_num}"
                ))
                continue

            raw_ans = answer_key[q_num]

            # Validation for MCQ questions: check if answer is a valid option key
            if q.question_type == "MCQ" and q.options:
                upper_keys = [k.upper() for k in q.options.keys()]
                if raw_ans in upper_keys:
                    matches.append(AnswerMatch(
                        question_number=q_num,
                        answer=raw_ans,
                        confidence=0.96,
                        is_matched=True
                    ))
                else:
                    # Answer key has value not in options (e.g. key says "E", options are A-D)
                    logger.warning(
                        f"Answer key mismatch for Q{q_num}: '{raw_ans}' not among options {upper_keys}"
                    )
                    matches.append(AnswerMatch(
                        question_number=q_num,
                        answer=None,  # Do not invent or assign false answer
                        confidence=0.35,
                        is_matched=False,
                        issue_message=(
                            f"Answer key entry '{raw_ans}' does not match available options "
                            f"({', '.join(upper_keys)}) for Question {q_num}"
                        )
                    ))
            elif q.question_type == "TRUE_FALSE":
                if raw_ans in ("TRUE", "FALSE", "A", "B"):
                    matches.append(AnswerMatch(
                        question_number=q_num,
                        answer=raw_ans,
                        confidence=0.95,
                        is_matched=True
                    ))
                else:
                    matches.append(AnswerMatch(
                        question_number=q_num,
                        answer=None,
                        confidence=0.40,
                        is_matched=False,
                        issue_message=f"Uncertain True/False answer key value: {raw_ans}"
                    ))
            else:
                # Short answer or unknown
                matches.append(AnswerMatch(
                    question_number=q_num,
                    answer=raw_ans,
                    confidence=0.85,
                    is_matched=True
                ))

        return matches

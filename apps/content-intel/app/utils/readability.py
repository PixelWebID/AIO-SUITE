"""Very small readability helpers used until textstat integration lands."""

import math
from typing import Dict


def score_readability(text: str) -> Dict[str, float]:
    """
    Calculate heuristic readability metrics for generated content.

    We avoid heavy dependencies in the skeleton and rely on a simple average
    sentence length calculation as a placeholder.
    """

    words = text.split()
    sentences = [segment for segment in text.replace("!", ".").replace("?", ".").split(".") if segment]
    word_count = max(len(words), 1)
    sentence_count = max(len(sentences), 1)

    avg_sentence_length = word_count / sentence_count
    flesch_like = max(0.0, 100.0 - avg_sentence_length * 3.2)
    fk_grade = max(0.0, avg_sentence_length / 1.8)

    return {
        "word_count": float(word_count),
        "avg_sentence_length": round(avg_sentence_length, 2),
        "flesch_estimate": round(flesch_like, 2),
        "fk_grade_estimate": round(fk_grade, 2),
    }

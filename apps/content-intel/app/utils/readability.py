"""Readability scoring utilities (Flesch Reading Ease, FK grade, etc.)."""

from __future__ import annotations

import math
import re
from typing import Dict

WORD_PATTERN = re.compile(r"[a-zA-ZÀ-ÿ]+(?:'[a-z]+)?")
SENTENCE_PATTERN = re.compile(r"[.!?]+")
SYLLABLE_PATTERN = re.compile(r"[aeiouyàáâäæãåāèéêëēėęîïíīįìôöòóœøōõûüùúūÿy]+", re.IGNORECASE)


def _estimate_syllables(word: str) -> int:
    """Estimate the syllable count for a word using a heuristic approach."""

    if not word:
        return 0

    lowered = word.lower()
    syllables = len(SYLLABLE_PATTERN.findall(lowered))

    if lowered.endswith(("e", "es", "ed")) and syllables > 1:
        syllables -= 1

    return max(syllables, 1)


def score_readability(text: str) -> Dict[str, float]:
    """
    Calculate readability metrics for the provided text.

    Returns:
        {
            "word_count": int,
            "sentence_count": int,
            "avg_sentence_length": float,
            "avg_syllables_per_word": float,
            "flesch_reading_ease": float,
            "fk_grade_level": float,
        }
    """

    words = WORD_PATTERN.findall(text)
    sentences = SENTENCE_PATTERN.split(text)
    sentence_count = max(len([s for s in sentences if s.strip()]), 1)
    word_count = max(len(words), 1)

    total_syllables = sum(_estimate_syllables(word) for word in words)
    avg_sentence_length = word_count / sentence_count
    avg_syllables = total_syllables / word_count

    flesch = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables)
    grade = (0.39 * avg_sentence_length) + (11.8 * avg_syllables) - 15.59

    return {
        "word_count": float(word_count),
        "sentence_count": float(sentence_count),
        "avg_sentence_length": round(avg_sentence_length, 2),
        "avg_syllables_per_word": round(avg_syllables, 2),
        "flesch_reading_ease": round(flesch, 2),
        "fk_grade_level": round(grade, 2),
    }

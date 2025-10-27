"""Readability helpers leveraging textstat for Flesch and FK grade."""

from __future__ import annotations

from typing import Dict

from textstat import textstat


def score_readability(text: str) -> Dict[str, float]:
    """Return key readability metrics for the supplied text."""

    cleaned = text or ""
    word_count = max(textstat.lexicon_count(cleaned, removepunct=True), 1)
    sentence_count = max(textstat.sentence_count(cleaned), 1)
    flesch = textstat.flesch_reading_ease(cleaned)
    fk_grade = textstat.flesch_kincaid_grade(cleaned)
    avg_sentence_length = word_count / sentence_count
    syllable_total = textstat.syllable_count(cleaned)
    avg_syllables = syllable_total / word_count if word_count else 0

    return {
        "word_count": float(word_count),
        "sentence_count": float(sentence_count),
        "avg_sentence_length": round(avg_sentence_length, 2),
        "avg_syllables_per_word": round(avg_syllables, 2),
        "flesch_reading_ease": round(flesch, 2) if flesch is not None else 0.0,
        "fk_grade_level": round(fk_grade, 2) if fk_grade is not None else 0.0,
    }

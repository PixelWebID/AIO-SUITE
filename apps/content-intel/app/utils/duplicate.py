"""Duplicate content detection helpers using hashing and SimHash similarity."""

from __future__ import annotations

import hashlib
import math
from typing import Dict, Iterable, List, Tuple

SIMHASH_BIT_LENGTH = 64


def _tokenize(text: str) -> List[str]:
    """Return a list of lowercase tokens suitable for fingerprinting."""

    clean = "".join(char if char.isalnum() else " " for char in text.lower())
    return [token for token in clean.split() if token]


def _hash_token(token: str) -> int:
    """Return a deterministic 64-bit hash for a token."""

    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _simhash(tokens: Iterable[str]) -> int:
    """Compute a SimHash fingerprint for the supplied tokens."""

    weights = [0] * SIMHASH_BIT_LENGTH
    for token in tokens:
        h = _hash_token(token)
        weight = 1 + int(math.log(len(token) + 1, 2))
        for bit in range(SIMHASH_BIT_LENGTH):
            if h & (1 << bit):
                weights[bit] += weight
            else:
                weights[bit] -= weight

    fingerprint = 0
    for bit in range(SIMHASH_BIT_LENGTH):
        if weights[bit] >= 0:
            fingerprint |= 1 << bit
    return fingerprint


def _hamming_distance(a: int, b: int) -> int:
    """Return the Hamming distance between two integers."""

    return (a ^ b).bit_count()


def compute_signatures(text: str) -> Dict[str, str]:
    """
    Generate signatures used to detect duplicate content.

    Returns SHA-1, SHA-256, and a SimHash fingerprint (hex encoded).
    """

    normalized = " ".join(text.lower().split())
    sha1 = hashlib.sha1(normalized.encode("utf-8"), usedforsecurity=False).hexdigest()
    sha256 = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    simhash = _simhash(_tokenize(normalized))

    return {
        "sha1": sha1,
        "sha256": sha256,
        "simhash": f"{simhash:016x}",
    }


def simhash_similarity(simhash_a: str, simhash_b: str) -> float:
    """Return the similarity score (0-1) between two SimHash fingerprints."""

    a = int(simhash_a, 16)
    b = int(simhash_b, 16)
    distance = _hamming_distance(a, b)
    return 1.0 - distance / SIMHASH_BIT_LENGTH


def detect_similar_overlaps(
    target_simhash: str,
    candidates: Iterable[Tuple[str, str]],
    *,
    threshold: float = 0.85,
) -> List[str]:
    """
    Compare the target fingerprint with candidate fingerprints.

    Params:
        target_simhash: SimHash hex value for generated content.
        candidates: iterable of (identifier, simhash_hex).
        threshold: minimal similarity ratio to record a warning.

    Returns:
        Identifiers whose similarity exceeds the configured threshold.
    """

    overlaps: List[str] = []
    for identifier, simhash in candidates:
        score = simhash_similarity(target_simhash, simhash)
        if score >= threshold:
            overlaps.append(f"{identifier} ({score:.2%} similarity)")
    return overlaps

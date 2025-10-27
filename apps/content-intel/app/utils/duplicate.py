
"""Duplicate detection utilities (checksums + SimHash)."""

from __future__ import annotations

import hashlib
from typing import Iterable, List, Tuple

from simhash import Simhash


def checksum(text: str) -> Tuple[str, str]:
    normalized = " ".join(text.split()).encode('utf-8')
    sha1 = hashlib.sha1(normalized, usedforsecurity=False).hexdigest()
    sha256 = hashlib.sha256(normalized).hexdigest()
    return sha1, sha256


def compute_simhash(text: str) -> str:
    tokens = [token for token in text.lower().split() if token]
    return f"{Simhash(tokens).value:016x}"


def detect_similarities(target_simhash: str, candidates: Iterable[Tuple[str, str]], threshold: float = 0.85) -> List[str]:
    target_int = int(target_simhash, 16)
    results: List[str] = []
    for identifier, candidate in candidates:
        if not candidate:
            continue
        score = _similarity(target_int, int(candidate, 16))
        if score >= threshold:
            results.append(f"{identifier} ({score:.0%})")
    return results


def _similarity(a: int, b: int) -> float:
    max_bits = max(a.bit_length(), b.bit_length(), 1)
    distance = (a ^ b).bit_count()
    return 1.0 - distance / max_bits

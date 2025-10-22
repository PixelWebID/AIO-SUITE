"""Duplicate content detection helpers (hashing & similarity)."""

import hashlib
from typing import Dict


def compute_signatures(text: str) -> Dict[str, str]:
    """
    Generate lightweight signatures for duplicate detection.

    The production pipeline will integrate SimHash and vector comparisons. For
    now we expose basic SHA variants so downstream code can persist state.
    """

    normalized = " ".join(text.lower().split())
    sha1 = hashlib.sha1(normalized.encode("utf-8"), usedforsecurity=False).hexdigest()
    sha256 = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    return {
        "sha1": sha1,
        "sha256": sha256,
    }

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.utils.readability import score_readability  # noqa: E402


def test_readability_metrics_have_expected_keys():
    metrics = score_readability('This is a test sentence. Another sentence follows.')
    assert 'word_count' in metrics
    assert metrics['word_count'] >= 2
    assert metrics['flesch_reading_ease'] >= 0

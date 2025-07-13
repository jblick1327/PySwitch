import importlib
import time
from collections import Counter

import switch_interface.predictive as predictive


def test_letter_suggestion():
    letters = predictive.suggest_letters("th")
    assert isinstance(letters, list)
    assert len(letters) > 0
    assert all(isinstance(c, str) and len(c) == 1 for c in letters)


def test_ngram_thread_starts_on_demand(monkeypatch):
    importlib.reload(predictive)
    assert predictive.default_predictor.thread is None

    letters = predictive.suggest_letters("an")
    assert len(letters) > 0
    assert predictive.default_predictor.thread is not None


def _naive_fallback(prefix: str, k: int, words: list[str]) -> list[str]:
    cleaned = "".join(c for c in prefix.lower() if c.isalpha())
    counts = Counter()
    if not cleaned:
        counts = Counter(w[0] for w in words if w and w[0].isalpha())
    else:
        n = len(cleaned)
        for w in words:
            if w.startswith(cleaned) and len(w) > n:
                c = w[n]
                if c.isalpha():
                    counts[c] += 1
        if not counts:
            counts = Counter(w[0] for w in words if w and w[0].isalpha())
    return [c for c, _ in counts.most_common(k)]


def test_fallback_speed_and_correctness():
    predictor = predictive.Predictor()
    prefix = "pre"
    start = time.perf_counter()
    result = predictor._fallback_letters(prefix, 3)
    elapsed = time.perf_counter() - start
    expected = _naive_fallback(prefix, 3, predictor.words)
    assert result == expected
    assert elapsed < 0.005

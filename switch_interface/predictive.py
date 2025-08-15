"""Simple predictive text helpers without module-level state."""

from __future__ import annotations

import threading
from collections import Counter, defaultdict
from functools import lru_cache
from typing import Counter as CounterType
from typing import DefaultDict

from wordfreq import top_n_list
from typing import TYPE_CHECKING


class Predictor:
    """Generate common word and letter suggestions."""

    def __init__(self, words: list[str] | None = None, max_words: int = 10_000) -> None:
        self.words = words or top_n_list("en", max_words)
        self.fallback_starts = Counter(w[0] for w in self.words if w and w[0].isalpha())
        self.start_letters: CounterType[str] | None = None
        self.bigrams: DefaultDict[str, CounterType[str]] | None = None
        self.trigrams: DefaultDict[str, CounterType[str]] | None = None
        self.ready = False
        self.thread: threading.Thread | None = None
        self.lock = threading.Lock()
        self._prefix_index: DefaultDict[str, CounterType[str]] = defaultdict(Counter)
        self._build_prefix_index()

    # ───────── internal helpers ────────────────────────────────────────────
    def _build_prefix_index(self) -> None:
        """Index word prefixes up to length 6 for fast fallback lookups."""
        for word in self.words:
            w = "".join(c for c in word.lower() if c.isalpha())
            for i in range(min(len(w) - 1, 6)):
                prefix = w[: i + 1]
                next_letter = w[i + 1]
                self._prefix_index[prefix][next_letter] += 1

    def _build_ngrams(self) -> None:
        start_letters: CounterType[str] = Counter()
        bigrams: DefaultDict[str, CounterType[str]] = defaultdict(Counter)
        trigrams: DefaultDict[str, CounterType[str]] = defaultdict(Counter)

        for word in self.words:
            w = "".join(c for c in word.lower() if c.isalpha())
            if not w:
                continue
            start_letters[w[0]] += 1
            for a, b in zip(w, w[1:]):
                bigrams[a][b] += 1
            for a, b, c in zip(w, w[1:], w[2:]):
                trigrams[a + b][c] += 1

        self.start_letters = start_letters
        self.bigrams = bigrams
        self.trigrams = trigrams
        self.ready = True

    def _ensure_thread(self) -> None:
        """Kick off n-gram building in the background if not already running."""

        if self.ready or self.thread is not None:
            return
        with self.lock:
            if self.thread is None and not self.ready:
                self.thread = threading.Thread(target=self._build_ngrams, daemon=True)
                self.thread.start()

    def _fallback_letters(self, prefix: str, k: int) -> list[str]:
        cleaned = "".join(c for c in prefix.lower() if c.isalpha())
        if not cleaned:
            counts = self.fallback_starts
        else:
            prefix_counts = self._prefix_index.get(cleaned)
            if prefix_counts and len(prefix_counts) > 0:
                counts = prefix_counts
            else:
                n = len(cleaned)
                temp: Counter[str] = Counter()
                for w in self.words:
                    if w.startswith(cleaned) and len(w) > n:
                        c = w[n]
                        if c.isalpha():
                            temp[c] += 1
                counts = temp if temp else self.fallback_starts

        return [c for c, _ in counts.most_common(k)]

    # ───────── public API ─────────────────────────────────────────────────
    @lru_cache(maxsize=512)
    def suggest_words(self, prefix: str, k: int = 3) -> list[str]:
        """Return up to ``k`` common words starting with ``prefix``."""
        self._ensure_thread()

        if not prefix:
            return []
        p = prefix.lower()
        return [w for w in self.words if w.startswith(p)][:k]

    def suggest_letters(self, prefix: str, k: int = 3) -> list[str]:
        """Suggest up to ``k`` likely next letters for ``prefix``."""
        self._ensure_thread()

        if not self.ready:
            return self._fallback_letters(prefix, k)

        return self._suggest_letters_cached(prefix, k)

    @lru_cache(maxsize=512)
    def _suggest_letters_cached(self, prefix: str, k: int = 3) -> list[str]:
        """Cached implementation for suggesting letters once data is ready."""
        # ``_ensure_thread`` and readiness checks happen in ``suggest_letters``.
        cleaned = "".join(c for c in prefix.lower() if c.isalpha())
        if not cleaned:
            assert self.start_letters is not None
            source = self.start_letters
        else:
            last2 = cleaned[-2:]
            if len(last2) == 2 and self.trigrams is not None and last2 in self.trigrams:
                source = self.trigrams[last2]
            else:
                last1 = cleaned[-1]
                assert self.bigrams is not None and self.start_letters is not None
                source = self.bigrams.get(last1, self.start_letters)
        return [letter for letter, _ in source.most_common(k)]


class PredictorManager:
    """Thread-safe singleton manager for the default predictor."""
    
    _instance: PredictorManager | None = None
    _lock = threading.Lock()
    
    def __new__(cls) -> PredictorManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._predictor = None
                    cls._instance._predictor_lock = threading.Lock()
        return cls._instance
    
    def get_predictor(self) -> Predictor:
        """Get the default predictor instance in a thread-safe manner."""
        with self._predictor_lock:
            if self._predictor is None:
                self._predictor = Predictor()
            return self._predictor


_predictor_manager = PredictorManager()


def _get_default_predictor() -> Predictor:
    """Get the default predictor instance."""
    return _predictor_manager.get_predictor()


def suggest_words(prefix: str, k: int = 3) -> list[str]:
    """Wrapper around :meth:`Predictor.suggest_words` using ``default_predictor``."""

    return _get_default_predictor().suggest_words(prefix, k)


def suggest_letters(prefix: str, k: int = 3) -> list[str]:
    """Wrapper around :meth:`Predictor.suggest_letters` using ``default_predictor``."""

    return _get_default_predictor().suggest_letters(prefix, k)


def __getattr__(name: str):
    if name == "default_predictor":
        return _get_default_predictor()
    raise AttributeError(name)


if TYPE_CHECKING:  # pragma: no cover - exported via __getattr__
    default_predictor: Predictor


__all__ = [
    "Predictor",
    "default_predictor",
    "suggest_words",
    "suggest_letters",
]

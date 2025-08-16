from __future__ import annotations

import abc
import contextlib
import importlib
import inspect
import logging
import platform
from pathlib import Path
from threading import Lock
from types import ModuleType
from typing import Any, Callable, Iterator, Optional

import sounddevice as sd

log = logging.getLogger(__name__)

__all__ = ["open_input", "rescan_backends"]


class InputBackend(abc.ABC):
    """Abstract base class for audio input back-ends."""

    #: Higher priority back-ends are preferred when multiple match.
    priority: int = 0

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(priority={self.priority})"

    @abc.abstractmethod
    def matches_hostapi(self, hostapi_info: dict[str, Any]) -> bool:
        """Return ``True`` if this backend supports ``hostapi_info``."""

    @contextlib.contextmanager
    @abc.abstractmethod
    def open(
        self,
        *,
        samplerate: int,
        blocksize: int,
        channels: int,
        dtype: str,
        device: int | str | None,
        callback: Callable[..., None],
        **extra_kwargs: Any,
    ) -> Iterator[sd.InputStream]:
        """Yield a started :class:`sounddevice.InputStream`."""


_BACKENDS: list[InputBackend] = []
_BACKENDS_LOADED = False
_BACKENDS_LOCK = Lock()


def _discover_backends() -> None:

    global _BACKENDS_LOADED
    with _BACKENDS_LOCK:
        if _BACKENDS_LOADED:
            return

        _BACKENDS.clear()

        backends_dir = Path(__file__).parent / "backends"
        for file in backends_dir.glob("*.py"):
            if file.stem == "__init__":
                continue
            module_name = f"{__package__}.backends.{file.stem}"
            try:
                mod: ModuleType = importlib.import_module(module_name)
            except Exception as exc:
                log.debug("Backend %s skipped (%s)", module_name, exc)
                continue

            for name, cls in inspect.getmembers(mod, inspect.isclass):
                if issubclass(cls, InputBackend) and cls is not InputBackend:
                    try:
                        _BACKENDS.append(cls())
                    except Exception:
                        log.debug("Backend %s failed to initialize", cls.__name__)

        _BACKENDS_LOADED = True
        _BACKENDS.sort(key=lambda b: b.priority, reverse=True)
        log.debug(
            "Found %d functional audio back-ends: %s",
            len(_BACKENDS),
            _BACKENDS,
        )


def _select_backend(
    platform_name: str | None = None, preferred_name: str | None = None
) -> InputBackend:
    """Return the best backend for the platform or preferred name."""

    _discover_backends()
    if not _BACKENDS:
        raise RuntimeError("No audio back-ends loaded at all")

    # If preferred_name matches one of our backends, use that
    if preferred_name:
        preferred_lower = preferred_name.lower()
        for b in _BACKENDS:
            backend_name = b.__class__.__name__.lower()
            if preferred_lower in backend_name:
                log.debug("Selected preferred backend %s", b)
                return b

    # Platform default selection
    if platform_name is None:
        platform_name = platform.system()

    platform_preferences = {"Windows": "wasapi", "Darwin": "coreaudio", "Linux": "alsa"}

    preferred_api = platform_preferences.get(platform_name, "").lower()
    if preferred_api:
        for b in _BACKENDS:
            if preferred_api in b.__class__.__name__.lower():
                log.debug(
                    "Selected platform default backend %s for %s", b, platform_name
                )
                return b

    # Fall back to highest priority backend (first in sorted list)
    fallback = _BACKENDS[0] if _BACKENDS else None
    if fallback:
        log.warning(
            "No platform match for %s; using highest priority backend %s",
            platform_name,
            fallback,
        )
        return fallback

    raise RuntimeError("No functional audio backends available")


@contextlib.contextmanager
def open_input(
    *,
    samplerate: int,
    blocksize: int,
    callback: Callable[..., None],
    channels: int = 1,
    dtype: str = "float32",
    device: Optional[int | str] = None,
    backend: Optional[str] = None,
    preflight: bool = True,
    **extra_kwargs: Any,
) -> Iterator[sd.InputStream]:
    """Yield a started :class:`sounddevice.InputStream`.

    The best input backend is chosen for ``device`` and platform-specific
    fallbacks (e.g. WASAPI shared mode) are handled automatically. Use this
    instead of instantiating ``sd.InputStream`` directly.
    """

    _discover_backends()

    if backend is not None:
        chosen = _select_backend(preferred_name=backend)
    else:
        chosen = _select_backend()

    # Preflight check if requested
    if preflight:
        try:
            check_kwargs = {
                "device": device,
                "samplerate": samplerate,
                "channels": channels,
                "dtype": dtype,
                "blocksize": blocksize,
            }
            if "extra_settings" in extra_kwargs:
                check_kwargs["extra_settings"] = extra_kwargs["extra_settings"]

            sd.check_input_settings(**check_kwargs)
        except Exception as exc:
            log.debug("Preflight check failed: %s", exc)
            # Continue anyway - backend may handle the fallback

    # Open stream with proper context management
    with chosen.open(
        samplerate=samplerate,
        blocksize=blocksize,
        channels=channels,
        dtype=dtype,
        device=device,
        callback=callback,
        **extra_kwargs,
    ) as s:
        # Get device info for logging
        try:
            info = (
                sd.query_devices(None, "input")
                if device is None
                else sd.query_devices(device, "input")
            )
            dev_name = info.get("name", "unknown")
            dev_idx = info.get("index", device or "default")
        except Exception:
            dev_name = "unknown"
            dev_idx = device or "default"

        # Get mode from backend if available
        mode = getattr(chosen, "_last_mode", "n/a")

        log.info(
            'audio_open_ok api=%s dev="%s" idx=%s mode=%s sr=%d bs=%d dt=%s preflight=%s',
            chosen.__class__.__name__.replace("Backend", ""),
            dev_name,
            dev_idx,
            mode,
            samplerate,
            blocksize,
            dtype,
            preflight,
        )
        yield s


def rescan_backends() -> None:
    global _BACKENDS_LOADED
    with _BACKENDS_LOCK:
        _BACKENDS_LOADED = False
        _BACKENDS.clear()
    _discover_backends()
    log.debug("Re-scanning backends")

"""Audio listener for switch activation.

This module is responsible solely for opening the microphone input and
emitting callbacks when a switch press is detected.  It relies on the
edge-detection algorithm defined in :mod:`switch_interface.detection`.
"""
from __future__ import annotations

import math
import time
from typing import Callable, Optional

import numpy as np

from .audio.backends.wasapi import get_extra_settings


__all__ = ["listen", "check_device"]


def check_device(*, samplerate: int = 44_100, blocksize: int = 256, device: int | str | None = None) -> None:
    """Raise ``RuntimeError`` if the input device can't be opened."""
    import sounddevice as sd

    extra = get_extra_settings()
    kwargs = {
        "samplerate": samplerate,
        "blocksize": blocksize,
        "channels": 1,
        "dtype": "float32",
        "device": device,
    }
    if extra is not None:
        kwargs["extra_settings"] = extra
    try:
        with sd.InputStream(callback=lambda *a: None, **kwargs):
            pass
    except sd.PortAudioError as exc:
        if extra is not None:
            kwargs.pop("extra_settings", None)
            try:
                with sd.InputStream(callback=lambda *a: None, **kwargs):
                    pass
            except sd.PortAudioError as exc2:
                raise RuntimeError("Failed to open audio input device") from exc2
        else:
            raise RuntimeError("Failed to open audio input device") from exc


def listen(
    on_press: Callable[[], None],
    *,
    upper_offset: float = -0.2,
    lower_offset: float = -0.5,
    samplerate: int = 44_100,
    blocksize: int = 256,
    debounce_ms: int = 40,
    device: Optional[int | str] = None,
) -> None:
    """Block while monitoring the input stream for switch presses."""
    from .detection import EdgeState, detect_edges
    import sounddevice as sd

    if upper_offset <= lower_offset:
        raise ValueError("upper_offset must be > lower_offset (both negative values)")

    refractory_samples = int(math.ceil((debounce_ms / 1_000) * samplerate))
    state = EdgeState(armed=True, cooldown=0)

    def _callback(indata: np.ndarray, frames: int, _: int, __: int) -> None:
        nonlocal state
        mono = indata.mean(axis=1) if indata.shape[1] > 1 else indata[:, 0]
        state, pressed = detect_edges(
            mono,
            state,
            upper_offset,
            lower_offset,
            refractory_samples,
        )
        if pressed:
            on_press()

    extra = get_extra_settings()
    stream_kwargs = {
        "samplerate": samplerate,
        "blocksize": blocksize,
        "channels": 1,
        "dtype": "float32",
        "callback": _callback,
        "device": device,
    }
    if extra is not None:
        stream_kwargs["extra_settings"] = extra

    def _run(kwargs):
        with sd.InputStream(**kwargs):
            try:
                while True:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                return

    try:
        _run(stream_kwargs)
    except sd.PortAudioError as exc:
        if extra is not None:
            stream_kwargs.pop("extra_settings", None)
            try:
                _run(stream_kwargs)
            except sd.PortAudioError as exc2:
                raise RuntimeError("Failed to open audio input device") from exc2
        else:
            raise RuntimeError("Failed to open audio input device") from exc

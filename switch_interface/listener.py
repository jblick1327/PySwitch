"""Monitor audio input and call a handler when a switch press is detected."""
from __future__ import annotations

import math
import time
from typing import Callable, Optional

import numpy as np

from .audio.stream import open_input


__all__ = ["listen", "check_device"]


def check_device(*, samplerate: int = 44_100, blocksize: int = 256, device: int | str | None = None) -> None:
    """Raise ``RuntimeError`` if the input device can't be opened."""
    import sounddevice as sd

    try:
        with open_input(
            samplerate=samplerate,
            blocksize=blocksize,
            channels=1,
            dtype="float32",
            device=device,
            callback=lambda *a: None,
        ):
            pass
    except sd.PortAudioError as exc:
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

    def _run() -> None:
        with open_input(
            samplerate=samplerate,
            blocksize=blocksize,
            channels=1,
            dtype="float32",
            callback=_callback,
            device=device,
        ):
            try:
                while True:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                return

    try:
        _run()
    except sd.PortAudioError as exc:
        raise RuntimeError("Failed to open audio input device") from exc

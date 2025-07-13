"""Switch press edge-detection algorithm.

This module contains only the signal-processing logic required to detect
presses in a stream of audio samples.  Opening the microphone and
handling input streams lives in :mod:`switch_interface.listener`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np

__all__ = ["EdgeState", "detect_edges"]

@dataclass
class EdgeState:
    armed: bool
    cooldown: int
    prev_sample: float = 0.0
    bias: float = 0.0


def detect_edges(
    block: np.ndarray,
    state: EdgeState,
    upper_offset: float,
    lower_offset: float,
    refractory_samples: int,
) -> Tuple[EdgeState, bool]:
    """Detect a falling edge in ``block``.

    Returns the updated ``EdgeState`` and whether a press was detected.
    """

    if block.ndim != 1:
        raise ValueError(f"block must be a 1-D array (got shape {block.shape})")

    if state.armed:
        # exponential moving average over the current block
        state.bias = 0.995 * state.bias + 0.005 * float(block.mean())

    dyn_upper = state.bias + upper_offset
    dyn_lower = state.bias + lower_offset

    samples = np.concatenate(([state.prev_sample], block))
    crossings = (samples[:-1] >= dyn_upper) & (samples[1:] <= dyn_lower)

    armed = state.armed
    cooldown = state.cooldown
    press_index: int | None = None

    if not armed:
        if cooldown >= len(block):
            cooldown -= len(block)
        else:
            offset = cooldown  # cooldown just expired
            # re-arm ONLY if the signal has risen back above dyn_upper
            if samples[offset] >= dyn_upper:
                armed = True
                remaining = crossings[offset:]
                idxs = np.flatnonzero(remaining)
                if idxs.size:
                    press_index = idxs[0] + offset
    else:
        idxs = np.flatnonzero(crossings)
        if idxs.size:
            press_index = idxs[0]

    if press_index is not None:
        armed = False
        cooldown = refractory_samples - (len(block) - press_index - 1)
        if cooldown <= 0:
            cooldown = 0
            # re-arm only after release
            if block[-1] >= dyn_upper:
                armed = True

    return (
        EdgeState(
            armed=armed,
            cooldown=cooldown,
            prev_sample=block[-1] if len(block) else state.prev_sample,
            bias=state.bias,
        ),
        press_index is not None,
    )


def __getattr__(name: str):
    if name in {"listen", "check_device"}:
        from . import compat

        return getattr(compat, name)
    raise AttributeError(name)





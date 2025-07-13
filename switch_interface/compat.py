from __future__ import annotations

import warnings
from typing import Any, Callable

__all__ = ["check_device", "listen"]


def check_device(*args, **kwargs):
    """Deprecated wrapper for :func:`listener.check_device`."""
    warnings.warn(
        "check_device moved to switch_interface.listener",
        DeprecationWarning,
        stacklevel=2,
    )
    from .listener import check_device as _real

    return _real(*args, **kwargs)


def listen(
    on_press: Callable[[], None],
    config: Any | None = None,
    /,
    **kwargs: Any,
) -> None:
    """Deprecated wrapper for :func:`listener.listen`.

    Supports the legacy call signature ``listen(on_press, config)`` where
    ``config`` provides detector parameters as attributes or mapping keys.
    """
    warnings.warn(
        "listen moved to switch_interface.listener",
        DeprecationWarning,
        stacklevel=2,
    )
    from .listener import listen as _real

    if config is not None and not kwargs:
        attrs = [
            "upper_offset",
            "lower_offset",
            "samplerate",
            "blocksize",
            "debounce_ms",
            "device",
        ]
        if isinstance(config, dict):
            params = {k: config.get(k) for k in attrs}
        else:
            params = {k: getattr(config, k, None) for k in attrs}
        return _real(on_press, **params)

    return _real(on_press, **kwargs)

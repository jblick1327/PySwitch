from __future__ import annotations

import warnings

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


def listen(*args, **kwargs):
    """Deprecated wrapper for :func:`listener.listen`."""
    warnings.warn(
        "listen moved to switch_interface.listener",
        DeprecationWarning,
        stacklevel=2,
    )
    from .listener import listen as _real

    return _real(*args, **kwargs)


"""PulseAudio backend stub.

This module is a placeholder used on platforms without a functional
PulseAudio implementation. Importing it provides a :class:`PulseAudioBackend`
class whose constructor immediately raises :class:`NotImplementedError`.
"""


class PulseAudioBackend:
    """Stubbed backend for the PulseAudio host API."""

    def __init__(self) -> None:
        raise NotImplementedError("PulseAudio backend not implemented on this platform")

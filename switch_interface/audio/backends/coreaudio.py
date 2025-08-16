from __future__ import annotations

import contextlib
import logging
from typing import Any, Callable, Iterator

import sounddevice as sd

from ..stream import InputBackend

log = logging.getLogger(__name__)


class CoreAudioBackend(InputBackend):
    """Backend for macOS Core Audio."""

    priority = 10

    def matches_hostapi(self, hostapi_info: dict[str, Any]) -> bool:
        return "Core Audio" in hostapi_info.get("name", "")

    @contextlib.contextmanager
    def open(
        self,
        *,
        samplerate: int = 48000,
        blocksize: int = 128,
        channels: int = 1,
        dtype: str = "float32",
        device: int | str | None,
        callback: Callable[..., None],
        **extra_kwargs: Any,
    ) -> Iterator[sd.InputStream]:
        kwargs = dict(
            samplerate=samplerate,
            blocksize=blocksize,
            channels=channels,
            dtype=dtype,
            device=device,
            callback=callback,
        )
        kwargs.update(extra_kwargs)

        # Strict preflight check
        try:
            sd.check_input_settings(**kwargs)
        except Exception as exc:
            # Retry with blocksize 256
            if kwargs["blocksize"] == 128:
                log.debug(
                    "CoreAudio preflight failed with bs=128, trying bs=256: %s", exc
                )
                kwargs["blocksize"] = 256
                try:
                    sd.check_input_settings(**kwargs)
                except Exception as exc2:
                    log.debug(
                        "CoreAudio preflight failed: device=%s sr=%d bs=%d dtype=%s",
                        device,
                        samplerate,
                        256,
                        dtype,
                    )
                    raise exc2
            else:
                log.debug(
                    "CoreAudio preflight failed: device=%s sr=%d bs=%d dtype=%s",
                    device,
                    samplerate,
                    blocksize,
                    dtype,
                )
                raise

        # Store mode for logging
        self._last_mode = "n/a"

        try:
            stream = sd.InputStream(**kwargs)
            stream.start()
        except Exception as exc:
            log.debug(
                "CoreAudio open failed: device=%s sr=%d bs=%d dtype=%s - %s",
                device,
                kwargs["samplerate"],
                kwargs["blocksize"],
                dtype,
                exc,
            )
            raise

        try:
            yield stream
        finally:
            with contextlib.suppress(Exception):
                stream.stop()
                stream.close()

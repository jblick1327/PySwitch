from __future__ import annotations

import contextlib
import logging
from typing import Any, Callable, Iterator

import sounddevice as sd

from ..stream import InputBackend

log = logging.getLogger(__name__)


class AlsaBackend(InputBackend):
    """Backend for Linux ALSA."""

    priority = 10

    def matches_hostapi(self, hostapi_info: dict[str, Any]) -> bool:
        return "ALSA" in hostapi_info.get("name", "")

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

        prefer_raw = kwargs.pop("prefer_raw", False)

        # Build candidate device list
        candidates: list[str] = []
        if isinstance(device, str) and device.startswith(("hw:", "plughw:")):
            candidates.append(device)
        if device is not None:
            candidates.append(str(device))  # as-is
        for name in ("default", "sysdefault"):
            if name not in candidates:
                candidates.append(name)
        # Last resort: if caller gave hw:X, also try plughw:X
        if isinstance(device, str) and device.startswith("hw:"):
            candidates.append(device.replace("hw:", "plughw:", 1))

        # Store mode for logging
        self._last_mode = "n/a"

        attempted = []
        stream = None
        last_error = None

        for candidate in candidates:
            test_kwargs = kwargs.copy()
            test_kwargs["device"] = candidate
            attempted.append(str(candidate) if candidate is not None else "default")

            # Preflight check
            try:
                sd.check_input_settings(**test_kwargs)
            except Exception as exc:
                log.debug(
                    "ALSA preflight failed for %s: %s", candidate or "default", exc
                )
                last_error = exc
                continue

            # Try to open with current blocksize
            try:
                stream = sd.InputStream(**test_kwargs)
                stream.start()
                log.debug(
                    "ALSA opened successfully with device: %s", candidate or "default"
                )
                break
            except Exception as exc:
                log.debug("ALSA open failed for %s: %s", candidate or "default", exc)
                last_error = exc

                # Retry with blocksize 256 if we were using 128
                if test_kwargs["blocksize"] == 128:
                    try:
                        test_kwargs["blocksize"] = 256
                        # Preflight with new blocksize
                        sd.check_input_settings(**test_kwargs)
                        stream = sd.InputStream(**test_kwargs)
                        stream.start()
                        log.debug(
                            "ALSA opened with device %s and blocksize 256",
                            candidate or "default",
                        )
                        break
                    except Exception as exc2:
                        log.debug(
                            "ALSA retry with bs=256 failed for %s: %s",
                            candidate or "default",
                            exc2,
                        )
                        last_error = exc2
                        continue

        if stream is None:
            raise RuntimeError(
                f"ALSA open failed; tried {attempted!r}. Last error: {last_error}"
            )

        try:
            yield stream
        finally:
            with contextlib.suppress(Exception):
                stream.stop()
                stream.close()

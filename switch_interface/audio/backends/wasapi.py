from __future__ import annotations

import contextlib
import logging
from typing import Any, Callable, Iterator

import sounddevice as sd

from ..stream import InputBackend


def get_extra_settings() -> sd.WasapiSettings | None:
    """Return exclusive-mode settings for WASAPI if available."""
    try:
        info = sd.query_hostapis(sd.default.hostapi)
        if info.get("name") == "Windows WASAPI":
            return sd.WasapiSettings(exclusive=True)
    except Exception:
        pass
    return None


log = logging.getLogger(__name__)


class WasapiBackend(InputBackend):
    """Backend for the Windows WASAPI host API."""

    priority = 20

    def matches_hostapi(self, hostapi_info: dict[str, Any]) -> bool:
        return "WASAPI" in hostapi_info.get("name", "")

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
        # Build base kwargs
        kwargs = dict(
            samplerate=samplerate,
            blocksize=blocksize,
            channels=channels,
            dtype=dtype,
            device=device,
            callback=callback,
        )
        kwargs.update(extra_kwargs)

        # Handle exclusive mode preference
        exclusive_req = kwargs.pop("exclusive", None)
        try_excl = (exclusive_req is None) or (exclusive_req is True)

        mode = "shared"  # Default assumption
        stream = None

        # Blacklist obvious virtual loopbacks for auto-selection
        if device is None:
            try:
                dev_info = sd.query_devices(sd.default.device[0], "input")
                dev_name = dev_info.get("name", "").lower()
                if any(
                    term in dev_name
                    for term in ["stereo mix", "what u hear", "loopback"]
                ):
                    log.debug("Skipping virtual loopback device: %s", dev_name)
                    # Let it proceed anyway - user may need it
            except Exception:
                pass

        # Try exclusive mode first if requested
        if try_excl:
            try:
                exclusive_kwargs = kwargs.copy()
                exclusive_kwargs["extra_settings"] = sd.WasapiSettings(exclusive=True)

                # Preflight check for exclusive mode
                try:
                    sd.check_input_settings(**exclusive_kwargs)
                except Exception as exc:
                    log.debug("WASAPI exclusive preflight failed: %s", exc)
                    raise  # Skip to shared mode

                stream = sd.InputStream(**exclusive_kwargs)
                stream.start()
                mode = "exclusive"
                log.debug("WASAPI exclusive mode successful")

            except Exception as exc:
                log.debug("WASAPI exclusive mode failed: %s", exc)
                stream = None

        # Fall back to shared mode if exclusive failed or wasn't tried
        if stream is None:
            shared_kwargs = kwargs.copy()
            shared_kwargs.pop("extra_settings", None)  # Remove any exclusive settings

            # Match device mix rate in shared mode to avoid SRC
            try:
                info = (
                    sd.query_devices(device, "input")
                    if isinstance(device, int)
                    else sd.query_devices(None, "input")
                )
                device_sr = int(
                    info.get("default_samplerate", samplerate) or samplerate
                )
                if device_sr != samplerate:
                    log.debug(
                        "Adjusting samplerate from %d to device mix rate %d",
                        samplerate,
                        device_sr,
                    )
                    shared_kwargs["samplerate"] = device_sr
            except Exception:
                pass

            mode = "shared"

            # Preflight check for shared mode
            try:
                sd.check_input_settings(**shared_kwargs)
            except Exception as exc:
                log.debug("WASAPI shared preflight failed: %s", exc)
                # Continue anyway

            try:
                stream = sd.InputStream(**shared_kwargs)
                stream.start()
            except Exception as exc:
                # Try with larger blocksize
                if shared_kwargs["blocksize"] == 128:
                    log.debug("Retrying WASAPI shared with blocksize 256: %s", exc)
                    shared_kwargs["blocksize"] = 256
                    try:
                        sd.check_input_settings(**shared_kwargs)
                    except Exception:
                        pass  # Continue anyway

                    stream = sd.InputStream(**shared_kwargs)
                    stream.start()
                else:
                    raise

        # Store mode for logging
        self._last_mode = mode

        try:
            yield stream
        finally:
            with contextlib.suppress(Exception):
                stream.stop()
                stream.close()

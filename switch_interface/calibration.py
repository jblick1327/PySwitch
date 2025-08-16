import contextlib
import json
import logging
import math
import os
import threading
import time
import tkinter as tk
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path
from tkinter import messagebox
from typing import Callable, Optional, Union

import numpy as np
import sounddevice as sd
from appdirs import user_config_dir

from .audio.stream import open_input
from .detection import EdgeState, detect_edges


@dataclass
class DetectorConfig:
    upper_offset: float = -0.2
    lower_offset: float = -0.5
    samplerate: int = 44_100
    blocksize: int = 256
    debounce_ms: int = 40
    device: str | None = None


CONFIG_DIR = Path(user_config_dir("switch_interface"))
CONFIG_FILE = CONFIG_DIR / "calibration.json"


def load_config(path: str | Path = CONFIG_FILE) -> "DetectorConfig":
    """Return saved detector settings or defaults if unavailable."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return DetectorConfig(**data)
    except Exception as exc:  # pragma: no cover - depends on filesystem errors
        logging.getLogger(__name__).exception(
            "Failed to load calibration config: %s", path
        )
        messagebox.showerror(
            "Error",
            (
                f"Could not read calibration file at {path}. "
                "Delete this file or run calibration again to create a new one."
            ),
        )
        return DetectorConfig()


def save_config(config: "DetectorConfig", path: str | Path = CONFIG_FILE) -> None:
    """Persist ``config`` to ``path`` in JSON format."""
    os.makedirs(Path(path).parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(config), f)


def calibrate(
    config: DetectorConfig | None = None,
    parent: tk.Tk | tk.Toplevel | None = None,
    on_complete: Optional[Callable] = None,
) -> DetectorConfig:
    """Launch a simple UI to adjust detector settings.

    Args:
        config: Initial detector configuration
        parent: Parent window (None to create a new Tk instance)
        on_complete: Callback function when calibration completes

    Returns:
        DetectorConfig: Updated detector configuration
    """
    config = config or DetectorConfig()

    # Create root window if no parent provided
    root: Union[tk.Tk, tk.Toplevel]
    if parent is None:
        root = tk.Tk()
    else:
        root = tk.Toplevel(parent)

    root.title("Calibrate Detector")

    u_var = tk.DoubleVar(master=root, value=config.upper_offset)
    l_var = tk.DoubleVar(master=root, value=config.lower_offset)
    db_var = tk.IntVar(master=root, value=config.debounce_ms)
    dev_var = tk.StringVar(master=root, value=config.device or "")

    STANDARD_RATES = [8000, 16000, 22050, 32000, 44100, 48000, 88200, 96000]

    def _supported_rates(device: str | None) -> list[int]:
        rates: list[int] = []
        for r in STANDARD_RATES:
            with suppress(Exception):
                sd.check_input_settings(device=device, samplerate=r)
                rates.append(r)
        return rates

    available_rates = _supported_rates(config.device) or STANDARD_RATES

    sr_var = tk.StringVar(master=root, value=str(config.samplerate))
    tk.Label(root, text="Sample rate").pack(padx=10, pady=(10, 0))
    tk.OptionMenu(root, sr_var, *[str(r) for r in available_rates]).pack(
        fill=tk.X, padx=10
    )

    STANDARD_BLOCKS = [64, 128, 256, 512, 1024, 2048]

    def _supported_blocks(device: str | None, samplerate: int) -> list[int]:
        params = dict(device=device, samplerate=samplerate, channels=1, dtype="float32")
        blocks: list[int] = []
        for b in STANDARD_BLOCKS:
            try:
                sd.check_input_settings(blocksize=b, **params)
            except TypeError:
                with suppress(Exception):
                    sd.InputStream(blocksize=b, **params).close()
                    blocks.append(b)
            except Exception:
                continue
            else:
                blocks.append(b)
        return blocks

    available_blocks = (
        _supported_blocks(config.device, int(sr_var.get())) or STANDARD_BLOCKS
    )

    bs_var = tk.StringVar(master=root, value=str(config.blocksize))
    tk.Label(root, text="Block size").pack(padx=10, pady=(10, 0))
    tk.OptionMenu(root, bs_var, *[str(b) for b in available_blocks]).pack(
        fill=tk.X, padx=10
    )

    wave_canvas = tk.Canvas(root, width=500, height=150, bg="white")
    wave_canvas.pack(padx=10, pady=5)

    WIDTH = 500
    HEIGHT = 150

    def _draw_ruler() -> None:
        for amp in (1, 0.5, 0, -0.5, -1):
            y = HEIGHT / 2 - amp * (HEIGHT / 2)
            wave_canvas.create_line(0, y, WIDTH, y, fill="#ccc", tags="ruler")

    _draw_ruler()

    tk.Scale(
        root,
        variable=u_var,
        from_=-1.0,
        to=1.0,
        resolution=0.01,
        label="Upper offset",
        orient=tk.HORIZONTAL,
    ).pack(fill=tk.X, padx=10, pady=5)

    tk.Scale(
        root,
        variable=l_var,
        from_=-1.0,
        to=0.0,
        resolution=0.01,
        label="Lower offset",
        orient=tk.HORIZONTAL,
    ).pack(fill=tk.X, padx=10, pady=5)

    tk.Scale(
        root,
        variable=db_var,
        from_=5,
        to=200,
        resolution=1,
        label="Debounce ms",
        orient=tk.HORIZONTAL,
    ).pack(fill=tk.X, padx=10, pady=5)

    devices = [d for d in sd.query_devices() if d.get("max_input_channels", 0) > 0]
    if devices and not dev_var.get():
        dev_var.set(devices[0]["name"])
    tk.Label(root, text="Microphone").pack(padx=10, pady=(10, 0))
    tk.OptionMenu(root, dev_var, *[d["name"] for d in devices]).pack(fill=tk.X, padx=10)

    result: DetectorConfig | None = None
    buf = np.zeros(int(sr_var.get()) * 2, dtype=np.float32)
    buf_index = 0
    bias = 0.0
    stream: sd.InputStream | None = None
    stream_cm: contextlib.AbstractContextManager | None = None
    edge_state = EdgeState(armed=True, cooldown=0)
    press_pending = False
    normal_bg = root.cget("bg")
    _update_id: str | None = None

    def _stop_stream() -> None:
        nonlocal stream, stream_cm
        if stream_cm is not None:
            with contextlib.suppress(Exception):
                stream_cm.__exit__(None, None, None)
            stream_cm = None
            stream = None

    def _callback(indata: np.ndarray, frames: int, time_info: int, status: int) -> None:
        nonlocal buf_index, edge_state, press_pending
        mono = indata.mean(axis=1) if indata.shape[1] > 1 else indata[:, 0]
        n = len(mono)
        if n > len(buf):
            mono = mono[-len(buf) :]
            n = len(buf)
        end = buf_index + n
        if end <= len(buf):
            buf[buf_index:end] = mono
        else:
            first = len(buf) - buf_index
            buf[buf_index:] = mono[:first]
            buf[: n - first] = mono[first:]
        buf_index = (buf_index + n) % len(buf)
        refract = int(math.ceil((db_var.get() / 1000) * int(sr_var.get())))
        edge_state, pressed = detect_edges(
            mono,
            edge_state,
            u_var.get(),
            l_var.get(),
            refract,
        )
        if pressed:
            press_pending = True

    def _start_stream() -> None:
        nonlocal stream
        nonlocal stream_cm, stream

        # Try with fallback mechanism
        from .audio_device_manager import AudioDeviceManager

        manager = AudioDeviceManager()
        device_id = dev_var.get() or None

        # Try to find a working device with fallback
        working_device, error, mode = manager.find_working_device(
            device_id, samplerate=int(sr_var.get()), blocksize=int(bs_var.get())
        )

        if working_device is not None:
            # Update device selection if different from original
            if working_device != device_id:
                dev_var.set(str(working_device) if working_device is not None else "")
                messagebox.showinfo(
                    "Device Changed",
                    f"Using alternative audio device: {working_device}",
                )

            try:
                # Use the working device
                stream_cm = open_input(
                    samplerate=int(sr_var.get()),
                    blocksize=int(bs_var.get()),
                    channels=1,
                    dtype="float32",
                    callback=_callback,
                    device=working_device,
                )
                stream = stream_cm.__enter__()
                return
            except Exception:
                # Continue to fallback approach
                pass

        # Original approach as fallback
        try:
            stream_cm = open_input(
                samplerate=int(sr_var.get()),
                blocksize=int(bs_var.get()),
                channels=1,
                dtype="float32",
                callback=_callback,
                device=dev_var.get() or None,
            )
            stream = stream_cm.__enter__()
        except sd.PortAudioError as exc:
            stream_cm = None
            stream = None
            raise RuntimeError("Failed to open audio input device") from exc

    def _restart_stream() -> None:
        _stop_stream()
        _start_stream()

    def _update_wave() -> None:
        nonlocal bias, press_pending, _update_id
        if not getattr(root, "winfo_exists", lambda: True)():
            return
        wave_canvas.delete("all")
        _draw_ruler()
        data = np.concatenate([buf[buf_index:], buf[:buf_index]])
        bias = 0.995 * bias + 0.005 * float(data.mean())
        step = max(1, len(data) // WIDTH)
        if step > 1:
            trimmed = data[: step * WIDTH]
        else:
            trimmed = data
        samples = trimmed.reshape(-1, step).mean(axis=1)
        points: list[float] = []
        x_positions = np.linspace(0, WIDTH, len(samples), endpoint=False)
        for x, sample in zip(x_positions, samples):
            y = HEIGHT / 2 - float(sample) * (HEIGHT / 2)
            points.extend([float(x), y])
        wave_canvas.create_line(*points, fill="blue", tags="wave")
        upper = bias + u_var.get()
        lower = bias + l_var.get()
        y_upper = HEIGHT / 2 - upper * (HEIGHT / 2)
        y_lower = HEIGHT / 2 - lower * (HEIGHT / 2)
        wave_canvas.create_line(0, y_upper, WIDTH, y_upper, fill="red", tags="thr")
        wave_canvas.create_line(0, y_lower, WIDTH, y_lower, fill="red", tags="thr")
        if press_pending:
            root.configure(bg="yellow")
            root.after(150, lambda: root.configure(bg=normal_bg))
            press_pending = False
        _update_id = root.after(30, _update_wave)

    def _start() -> None:
        nonlocal result
        try:
            _start_stream()
        except RuntimeError as exc:
            root.withdraw()
            retry = messagebox.askretrycancel(
                "Error",
                f"Could not read switch: {exc}\n\nWould you like to try again with a different device?",
                parent=root,
            )
            if retry:
                # Try to find another working device
                from .audio_device_manager import AudioDeviceManager

                manager = AudioDeviceManager()
                working_device, error, mode = manager.find_working_device(None)

                if working_device is not None:
                    dev_var.set(
                        str(working_device) if working_device is not None else ""
                    )
                    messagebox.showinfo(
                        "Device Changed",
                        f"Trying with alternative audio device: {working_device}",
                        parent=root,
                    )
                    try:
                        _start_stream()
                    except RuntimeError:
                        messagebox.showerror(
                            "Error",
                            "Could not read switch with alternative device",
                            parent=root,
                        )
                        if _update_id is not None and hasattr(root, "after_cancel"):
                            root.after_cancel(_update_id)
                        root.destroy()
                        result = config
                        return
                else:
                    messagebox.showerror(
                        "Error",
                        "No working audio devices found",
                        parent=root,
                    )
                    if _update_id is not None and hasattr(root, "after_cancel"):
                        root.after_cancel(_update_id)
                    root.destroy()
                    result = config
                    return
            else:
                if _update_id is not None and hasattr(root, "after_cancel"):
                    root.after_cancel(_update_id)
                root.destroy()
                result = config
                return

        result = DetectorConfig(
            upper_offset=u_var.get(),
            lower_offset=l_var.get(),
            samplerate=int(sr_var.get()),
            blocksize=int(bs_var.get()),
            debounce_ms=db_var.get(),
            device=dev_var.get() or None,
        )

        # Validate the calibration
        if not validate_calibration(result):
            retry = messagebox.askretrycancel(
                "Warning",
                "Calibration settings may not be optimal. Would you like to try again?",
                parent=root,
            )
            if retry:
                return

        _stop_stream()
        if _update_id is not None and hasattr(root, "after_cancel"):
            root.after_cancel(_update_id)

        # Call completion callback if provided
        if on_complete is not None:
            on_complete(result)

        root.destroy()

    # Create button frame for multiple buttons
    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)

    # Start button
    tk.Button(button_frame, text="Start", command=_start).pack(side=tk.LEFT, padx=5)

    # Auto-calibration button
    def _auto_calibrate():
        _stop_stream()
        try:
            device_id = dev_var.get() or None
            messagebox.showinfo(
                "Auto Calibration",
                "Press your switch 3-5 times when prompted.\nCalibration will begin in 2 seconds.",
                parent=root,
            )
            root.update()
            import time

            time.sleep(2)

            try:
                auto_settings = run_auto_calibration(device_id)

                # Update UI with auto-calibration results
                u_var.set(auto_settings["upper_offset"])
                l_var.set(auto_settings["lower_offset"])
                db_var.set(auto_settings["debounce_ms"])
                sr_var.set(str(auto_settings["samplerate"]))
                bs_var.set(str(auto_settings["blocksize"]))
                if auto_settings["device"] is not None:
                    dev_var.set(str(auto_settings["device"]))

                messagebox.showinfo(
                    "Auto Calibration",
                    "Auto-calibration complete! You can now test these settings.",
                    parent=root,
                )

                # Restart stream with new settings
                _restart_stream()

            except Exception as exc:
                messagebox.showerror(
                    "Auto Calibration Error",
                    f"Auto-calibration failed: {exc}",
                    parent=root,
                )
                # Restart stream with original settings
                _restart_stream()

        except Exception as exc:
            messagebox.showerror(
                "Error", f"Auto-calibration failed: {exc}", parent=root
            )

    tk.Button(button_frame, text="Auto-Calibrate", command=_auto_calibrate).pack(
        side=tk.LEFT, padx=5
    )

    def _on_close() -> None:
        _stop_stream()
        if _update_id is not None and hasattr(root, "after_cancel"):
            root.after_cancel(_update_id)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)

    _update_wave()
    root.mainloop()

    assert result is not None
    return result


def run_auto_calibration(
    device_id: int | str | None = None,
    max_attempts: int = 3,
    timeout_seconds: float = 5.0,
) -> dict:
    """Record a short sample from ``device_id`` and return calibration settings.

    Args:
        device_id: Audio device ID or name
        max_attempts: Maximum number of calibration attempts
        timeout_seconds: Maximum time to wait for recording

    Returns:
        dict: Calibration settings

    Raises:
        RuntimeError: If calibration fails after max_attempts
    """
    from .audio_device_manager import AudioDeviceManager

    duration = 3
    samplerate = 44_100
    blocksize = 256

    # Try to find a working device if the provided one fails
    manager = AudioDeviceManager()
    working_device, error, mode = manager.find_working_device(
        device_id, samplerate, blocksize
    )

    if working_device is not None:
        device_id = working_device

    # Function to run calibration with timeout
    def run_calibration_with_timeout() -> dict:
        # Use a flag to track completion
        calibration_complete = threading.Event()
        calibration_result = [None]
        calibration_error = [None]

        def record_thread():
            try:
                stream = sd.rec(
                    int(duration * samplerate),
                    samplerate=samplerate,
                    channels=1,
                    dtype="float32",
                    device=device_id,
                )
                sd.wait()
                samples = stream.reshape(-1)
                from .auto_calibration import calibrate

                res = calibrate(samples, samplerate)

                # Store result and signal completion
                calibration_result[0] = {
                    "upper_offset": res.upper_offset,
                    "lower_offset": res.lower_offset,
                    "debounce_ms": res.debounce_ms,
                    "samplerate": samplerate,
                    "blocksize": blocksize,
                    "device": device_id,
                    "calib_ok": res.calib_ok,
                }
                calibration_complete.set()
            except Exception as exc:
                calibration_error[0] = exc
                calibration_complete.set()

        # Start recording thread
        thread = threading.Thread(target=record_thread)
        thread.daemon = True
        thread.start()

        # Wait for completion or timeout
        if not calibration_complete.wait(timeout_seconds):
            raise TimeoutError(f"Calibration timed out after {timeout_seconds} seconds")

        # Check for errors
        if calibration_error[0] is not None:
            raise calibration_error[0]

        # Return result
        result = calibration_result[0]
        assert result is not None, "Calibration result should not be None at this point"
        return result

    # Try calibration with retries
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            result = run_calibration_with_timeout()

            # Validate calibration result
            if result.get("calib_ok", False):
                return result
            else:
                # Try again if calibration quality is poor
                last_error = RuntimeError("Calibration quality check failed")
                continue

        except Exception as exc:
            last_error = exc
            logging.getLogger(__name__).warning(
                f"Calibration attempt {attempt+1}/{max_attempts} failed: {exc}"
            )

            # Try with a different device on next attempt
            if attempt < max_attempts - 1:
                # Find another device to try
                available_devices = manager.get_available_input_devices()
                for device_info in available_devices:
                    if device_info["index"] != device_id:
                        device_id = device_info["index"]
                        logging.getLogger(__name__).info(
                            f"Trying alternative device for calibration: {device_id}"
                        )
                        break

    # If we get here, all attempts failed
    raise RuntimeError(
        f"Calibration failed after {max_attempts} attempts: {last_error}"
    )


def validate_calibration(config: DetectorConfig) -> bool:
    """Validate calibration settings to ensure they work.

    Args:
        config: Detector configuration to validate

    Returns:
        bool: True if calibration is valid
    """
    # Check for valid threshold values
    if config.upper_offset >= 0 or config.lower_offset >= 0:
        return False

    # Ensure upper threshold is higher than lower threshold
    if config.upper_offset <= config.lower_offset:
        return False

    # Check for reasonable debounce time
    if config.debounce_ms < 10 or config.debounce_ms > 200:
        return False

    # Check for valid sample rate
    if config.samplerate not in [8000, 16000, 22050, 32000, 44100, 48000, 88200, 96000]:
        return False

    # Check if device is available (if specified)
    if config.device is not None:
        from .audio_device_manager import AudioDeviceManager

        manager = AudioDeviceManager()
        valid, _, _ = manager.validate_device_settings(
            config.device, config.samplerate, config.blocksize
        )
        if not valid:
            return False

    return True

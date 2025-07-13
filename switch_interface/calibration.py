import json
import math
import os
import tkinter as tk
from dataclasses import asdict, dataclass
from contextlib import suppress
from pathlib import Path
from tkinter import messagebox

import numpy as np
import sounddevice as sd
from appdirs import user_config_dir

from .audio.backends.wasapi import get_extra_settings
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
    except Exception:
        return DetectorConfig()


def save_config(config: "DetectorConfig", path: str | Path = CONFIG_FILE) -> None:
    """Persist ``config`` to ``path`` in JSON format."""
    os.makedirs(Path(path).parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(config), f)


def calibrate(config: DetectorConfig | None = None) -> DetectorConfig:
    """Launch a simple UI to adjust detector settings."""
    config = config or DetectorConfig()
    root = tk.Tk()
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
    edge_state = EdgeState(armed=True, cooldown=0)
    press_pending = False
    normal_bg = root.cget("bg")

    def _stop_stream() -> None:
        nonlocal stream
        if stream is not None:
            try:
                stream.stop()
            finally:
                stream.close()
            stream = None

    def _callback(indata: np.ndarray, frames: int, time: int, status: int) -> None:
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
        extra = get_extra_settings()
        kwargs = dict(
            samplerate=int(sr_var.get()),
            blocksize=int(bs_var.get()),
            channels=1,
            dtype="float32",
            callback=_callback,
            device=dev_var.get() or None,
        )
        if extra is not None:
            kwargs["extra_settings"] = extra
        try:
            stream = sd.InputStream(**kwargs)
        except sd.PortAudioError as exc:
            if extra is not None:
                kwargs.pop("extra_settings", None)
                try:
                    stream = sd.InputStream(**kwargs)
                except sd.PortAudioError as exc2:
                    raise RuntimeError("Failed to open audio input device") from exc2
            else:
                raise RuntimeError("Failed to open audio input device") from exc
        stream.start()

    def _restart_stream() -> None:
        _stop_stream()
        _start_stream()

    def _update_wave() -> None:
        wave_canvas.delete("all")
        _draw_ruler()
        data = np.concatenate([buf[buf_index:], buf[:buf_index]])
        nonlocal bias
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
            y = HEIGHT / 2 - sample * (HEIGHT / 2)
            points.extend([x, y])
        wave_canvas.create_line(*points, fill="blue", tags="wave")
        upper = bias + u_var.get()
        lower = bias + l_var.get()
        y_upper = HEIGHT / 2 - upper * (HEIGHT / 2)
        y_lower = HEIGHT / 2 - lower * (HEIGHT / 2)
        wave_canvas.create_line(0, y_upper, WIDTH, y_upper, fill="red", tags="thr")
        wave_canvas.create_line(0, y_lower, WIDTH, y_lower, fill="red", tags="thr")
        nonlocal press_pending
        if press_pending:
            root.configure(bg="yellow")
            root.after(150, lambda: root.configure(bg=normal_bg))
            press_pending = False
        root.after(30, _update_wave)

    def _start() -> None:
        nonlocal result
        result = DetectorConfig(
            upper_offset=u_var.get(),
            lower_offset=l_var.get(),
            samplerate=int(sr_var.get()),
            blocksize=int(bs_var.get()),
            debounce_ms=db_var.get(),
            device=dev_var.get() or None,
        )
        _stop_stream()
        root.destroy()

    tk.Button(root, text="Start", command=_start).pack(pady=10)

    def _on_close() -> None:
        _stop_stream()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)

    try:
        _start_stream()
    except RuntimeError:
        root.withdraw()
        messagebox.showerror(
            "Error",
            "Could not read switch",
            parent=root,
        )
        root.destroy()
        return config

    _update_wave()
    root.mainloop()

    assert result is not None
    return result


def run_auto_calibration(device_id: int | str | None = None) -> dict:
    """Record a short sample from ``device_id`` and return calibration settings."""
    duration = 3
    samplerate = 44_100
    blocksize = 256
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
    return {
        "upper_offset": res.upper_offset,
        "lower_offset": res.lower_offset,
        "debounce_ms": res.debounce_ms,
        "samplerate": samplerate,
        "blocksize": blocksize,
        "device": device_id,
    }

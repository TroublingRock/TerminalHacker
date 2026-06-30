#!/usr/bin/env python3
"""Procedural sound effects for the TerminalHacker GUI (stdlib-only)."""

from __future__ import annotations

import math
import os
import struct
import subprocess
import tempfile
import threading
import wave


# (frequency Hz, duration seconds)
SOUND_PRESETS: dict[str, tuple[float, float]] = {
    "click": (1200, 0.04),
    "open": (880, 0.06),
    "close": (440, 0.05),
    "mail": (660, 0.12),
    "success": (523, 0.14),
    "alert": (220, 0.18),
    "error": (180, 0.2),
}


def _write_tone_wav(path: str, freq: float, duration: float, volume: float = 0.25) -> None:
    sample_rate = 22050
    n_samples = int(sample_rate * duration)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(n_samples):
            t = i / sample_rate
            envelope = min(1.0, t * 20) * max(0.0, 1.0 - (t / duration) * 0.6)
            value = int(volume * envelope * 32767 * math.sin(2 * math.pi * freq * t))
            wf.writeframes(struct.pack("<h", value))


def _play_wav_file(path: str) -> None:
    if os.name == "nt":
        try:
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return
        except OSError:
            pass
    for cmd in (["aplay", "-q", path], ["paplay", path]):
        try:
            subprocess.run(cmd, check=True, timeout=3, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except (FileNotFoundError, subprocess.SubprocessError, OSError):
            continue


def play(name: str) -> None:
    """Play a named sound asynchronously; silently skips if audio unavailable."""
    preset = SOUND_PRESETS.get(name)
    if not preset:
        return

    def _run() -> None:
        freq, duration = preset
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            _write_tone_wav(tmp_path, freq, duration)
            _play_wav_file(tmp_path)
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        except OSError:
            pass

    threading.Thread(target=_run, daemon=True).start()

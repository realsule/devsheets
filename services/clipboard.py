"""Optional clipboard support. Copies TEXT only - never runs anything from the sheets."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys


def _candidates():
    if sys.platform == "darwin":
        yield ["pbcopy"], "utf-8"
    if sys.platform == "win32" or shutil.which("clip.exe"):   # Windows and WSL
        yield ["clip.exe" if sys.platform != "win32" else "clip"], "utf-16"
    if os.environ.get("WAYLAND_DISPLAY"):
        yield ["wl-copy"], "utf-8"
    yield ["xclip", "-selection", "clipboard"], "utf-8"
    yield ["xsel", "--clipboard", "--input"], "utf-8"
    yield ["wl-copy"], "utf-8"


def find_tool():
    for cmd, enc in _candidates():
        if shutil.which(cmd[0]):
            return cmd, enc
    return None


def copy(text: str) -> tuple[bool, str]:
    """Return (ok, message). Never raises."""
    tool = find_tool()
    if not tool:
        return False, ("No clipboard tool found (install xclip, xsel or wl-clipboard on Linux; "
                       "clip.exe/pbcopy are built in on Windows/WSL/macOS). Select the text and copy it manually.")
    cmd, enc = tool
    try:
        subprocess.run(cmd, input=text.encode(enc), stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=5, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"Clipboard tool '{cmd[0]}' failed ({exc}). Select the text and copy it manually."
    return True, f"Copied to clipboard using {cmd[0]}."

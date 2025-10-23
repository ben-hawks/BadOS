# configuration.py
# Minimal, CircuitPython-friendly configuration and UI defaults for BadOS.
# This module provides a `settings` object and a `ui` namespace used by main.py.

class _HW:
    """Hardware abstraction used by main.py; display may be replaced by a board-specific driver.
    Keep attributes minimal: `display` is expected by Menu constructors elsewhere.
    """
    def __init__(self):
        self.display = None

class _UI:
    def __init__(self):
        # CircuitPython display libraries often use 16-bit color values or tuples; these
        # default values are safe fallbacks for console-based testing.
        self.bg_color = 0xFFFFFF
        self.fg_color = 0x000000

class _Settings:
    def __init__(self):
        # Paths are device-relative and intentionally conservative. CircuitPython
        # often mounts the flash root as '/'. Adjust these paths for your board
        # layout if needed.
        self.path = {
            "apps": ["/apps/"],
            "icons": ["/icons/"],
        }
        # hardware-specific config may be injected at runtime (main.py attempts this)
        self.hw = _HW()
        # network/time defaults
        self.ntp_server = "pool.ntp.org"

settings = _Settings()
ui = _UI()

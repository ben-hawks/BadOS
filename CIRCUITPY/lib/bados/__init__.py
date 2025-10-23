"""BadOS minimal CircuitPython library package

This package contains lightweight stubs used by the BadOS `main.py`.
Imports are wrapped so this file is safe for static analysis and partial
installs on devices where not all modules may be frozen or present.

We keep None placeholders for missing submodules so callers can fall back
cleanly. A small helper `available()` returns which high-level components
are present at runtime.
"""

__version__ = "0.1.0"
__repo__ = "https://github.com/yourname/BadOS"

# Try to import public symbols from local modules; if a module isn't present,
# expose a None placeholder so callers can fall back gracefully.
# Use ImportError where possible but fall back to the broad Exception so this
# module is robust during partial installs or when running static checks.

try:
    from .screen import Screen
except Exception:
    Screen = None

try:
    from .buttons import Buttons
except Exception:
    Buttons = None

try:
    from .menu import Menu
except Exception:
    Menu = None

try:
    from .rtc import BadOS_RTC
except Exception:
    BadOS_RTC = None

try:
    from .lowpower import LowPowerManager
except Exception:
    LowPowerManager = None

try:
    from .wifi import WiFiManager
except Exception:
    WiFiManager = None

# Import the configuration module as a module and fetch symbols via getattr to
# avoid some static analysis tools incorrectly flagging symbol imports.
try:
    from . import configuration as configuration
    settings = getattr(configuration, "settings", None)
    ui = getattr(configuration, "ui", None)
except Exception:
    settings = None
    ui = None

# hw helper
try:
    from . import hw as hw
except Exception:
    hw = None


def available():
    """Return a dict mapping public component names to booleans indicating
    whether the component is available (imported) at runtime.

    Example: bados.available()['WiFiManager']  # True if WiFiManager was imported
    """
    return {
        "Screen": Screen is not None,
        "Buttons": Buttons is not None,
        "Menu": Menu is not None,
        "BadOS_RTC": BadOS_RTC is not None,
        "LowPowerManager": LowPowerManager is not None,
        "WiFiManager": WiFiManager is not None,
        "settings": settings is not None,
        "ui": ui is not None,
        "hw": hw is not None,
    }


__all__ = [
    "Screen",
    "Buttons",
    "Menu",
    "BadOS_RTC",
    "LowPowerManager",
    "WiFiManager",
    "settings",
    "ui",
    "hw",
    "available",
]

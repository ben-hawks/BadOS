"""BadOS configuration settings

Provides ui (colors, layout) and settings (hardware calibration) objects.
"""

class UI:
    """UI configuration: colors, fonts, layout"""
    # Colors
    white = 0xFFFFFF
    black = 0x000000
    bg_color = 0xFFFFFF
    fg_color = 0x000000
    status_bg = 0x000000

    # Layout
    status_bar_height = 16
    button_pos = [50, 148, 246]  # X positions for A, B, C buttons (for 296px wide display)


class Settings:
    """Hardware settings: battery calibration, paths, etc."""
    # Battery voltage calibration
    min_battery = 320
    max_battery = 415

    # File paths
    path = {
        'icons': ['/icons/'],
        'apps': ['/apps/'],
    }

import sys

try:
    import storage
    import sdcardio
    import board
    import os
except Exception:
    storage = None
    sdcardio = None
    board = None
    os = None


SD_MOUNT_POINT = "/sd"


def mount_sd(readonly=False):
    """Mount the SD card at /sd using board.SPI() and CS = board.GP1.

    This implementation uses the direct call `board.SPI()` and does not
    include fallback logic. It returns True on success, False otherwise.
    """
    try:
        import board
        import sdcardio
        import storage
        import sys as _sys
    except Exception:
        # Required CircuitPython modules missing
        return False

    # Helper to check mounted volumes using storage.getmounts() when available
    def _is_mounted():
        getmounts = getattr(storage, 'getmounts', None)
        if callable(getmounts):
            try:
                for m in getmounts():
                    try:
                        if getattr(m, 'mount_point', None) == SD_MOUNT_POINT:
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
        return False

    # If already mounted via storage.getmounts(), ensure sys.path and return True
    try:
        if _is_mounted():
            if SD_MOUNT_POINT not in _sys.path:
                _sys.path.append(SD_MOUNT_POINT)
            return True
    except Exception:
        pass

    try:
        cs = getattr(board, 'GP1')
    except Exception:
        return False

    try:
        # Use the board-provided SPI constructor/object directly
        spi = board.SPI()
        sd = sdcardio.SDCard(spi, cs)
        vfs = storage.VfsFat(sd)
        # Ensure the mount point directory exists (CircuitPython expects the
        # mount-point path to exist before mounting).
        try:
            import os as _os
            if not _os.path.isdir(SD_MOUNT_POINT):
                try:
                    _os.mkdir(SD_MOUNT_POINT)
                except Exception:
                    pass
        except Exception:
            pass
        storage.mount(vfs, SD_MOUNT_POINT)
        if SD_MOUNT_POINT not in _sys.path:
            _sys.path.append(SD_MOUNT_POINT)
        return True
    except Exception:
        # On any exception while attempting to mount, do not retry — just return False
        return False


def add_search_path(path):
    """Add a path to the module/content search list used by BadOS."""
    if path and path not in sys.path:
        sys.path.append(path)
        return True
    return False

# A simple UI config placeholder; projects can replace this with their own UI
# descriptions loaded from SD or CIRCUITPY

__all__ = ["mount_sd", "add_search_path", "load_settings", "settings", "ui"]

# Previously we attempted a best-effort mount at import; that behavior was
# removed so mounting only happens when `mount_sd()` is explicitly called by
# the application (for example from `boot.py` or app startup code).

# Export singleton instances
ui = UI()
settings = Settings()


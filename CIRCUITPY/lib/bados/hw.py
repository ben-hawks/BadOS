"""Hardware helpers for BadOS (concise)

Provide small helpers to access the board's user LED and the five main
buttons. Prefer values from the board config module `config.bhawks_brainbadge_rp2040`
when present; otherwise fall back to `board.SW_<name>` and `board.USER_LED`.
"""

# Assume CircuitPython 10.x on-device; be less defensive to save code/ram
import board
import digitalio


def led_pin():
    """Return the board pin object for the user LED (or None)."""
    # Prefer board-specific config if present
    try:
        cfg = __import__("config.bhawks_brainbadge_rp2040", fromlist=["LED_PIN"])
        lp = getattr(cfg, "LED_PIN", None)
        if lp is not None:
            return lp
    except Exception:
        pass
    # Fallback to standard name
    return getattr(board, "USER_LED", None)


def make_led():
    """Return a configured DigitalInOut for the user LED, or None."""
    pin = led_pin()
    if pin is None:
        return None
    led = digitalio.DigitalInOut(pin)
    led.direction = digitalio.Direction.OUTPUT
    return led


def set_led(on=True):
    """Set the user LED on/off using a temporary DigitalInOut if necessary."""
    try:
        led = make_led()
        if not led:
            return False
        led.value = bool(on)
        return True
    except Exception:
        return False


def button_pins():
    """Return a tuple of 5 pins in the order: A, B, C, UP, DOWN.

    Prefers `config.bhawks_brainbadge_rp2040.BUTTON_PINS` when available.
    """
    try:
        cfg = __import__("config.bhawks_brainbadge_rp2040", fromlist=["BUTTON_PINS"])
        bp = getattr(cfg, "BUTTON_PINS", None)
        if bp:
            return tuple(bp)
    except Exception:
        pass
    # Fallback to standard board pin names SW_A, SW_B, SW_C, SW_UP, SW_DOWN
    return (
        getattr(board, "SW_A", None),
        getattr(board, "SW_B", None),
        getattr(board, "SW_C", None),
        getattr(board, "SW_UP", None),
        getattr(board, "SW_DOWN", None),
    )

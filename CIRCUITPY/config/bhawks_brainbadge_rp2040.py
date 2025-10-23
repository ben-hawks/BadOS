"""Board-specific hardware configuration for bhawks_brainbadge_rp2040

Expose the five navigation buttons and the user LED so higher-level code
(e.g. bados.buttons, bados.menu) can import this module from
CIRCUITPY/config/<board_id>.py and not need to reference `board` directly.

The module uses getattr(board, name, None) so it is safe to import on
non-target hardware (useful for desktop tests and static analysis).

Provided symbols:
- BOARD_ID: string board id
- BUTTONS: dict mapping names 'A','B','C','UP','DOWN' -> board pin object or None
- USER_LED: board pin object or None
- get_button(name): helper returning pin or None
"""

BOARD_ID = "bhawks_brainbadge_rp2040"

try:
    import board
except Exception:
    # When running static analysis or tests off-device, `board` may be absent.
    board = None

# Names on the board are expected to be accessible as board.SW_A, board.SW_B, ...
_button_names = {
    "A": "SW_A",
    "B": "SW_B",
    "C": "SW_C",
    "UP": "SW_UP",
    "DOWN": "SW_DOWN",
}

BUTTONS = {}
for logical, attr in _button_names.items():
    BUTTONS[logical] = getattr(board, attr, None) if board is not None else None

# LED exposed as board.USER_LED per project convention
USER_LED = getattr(board, "USER_LED", None) if board is not None else None


def get_button(name):
    """Return the board pin for `name` (one of 'A','B','C','UP','DOWN') or None.

    Use-case: from config import get_button; pin = get_button('A')
    """
    # Accept str-like names case-insensitively and allow passing the logical
    # key ('A','B','C','UP','DOWN'). If an invalid name is provided, return None.
    if not isinstance(name, str):
        return None
    key = name.strip().upper()
    return BUTTONS.get(key)


def get_all_buttons():
    """Return a shallow copy of the BUTTONS mapping.

    Useful to iterate available buttons without modifying the original mapping.
    """
    return dict(BUTTONS)

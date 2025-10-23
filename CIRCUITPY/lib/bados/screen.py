"""Screen helper for BadOS - thin displayio-friendly wrapper

Now assumes CircuitPython 10.x libraries (displayio, adafruit_display_text, terminalio)
are available on-device to reduce code size and complexity.
"""

import displayio
from adafruit_display_text import label
import terminalio


class Screen:
    """Small helper around a displayio display instance.

    Usage:
        screen = Screen(display)
        screen.show_text("Hello")
    """

    def __init__(self, display=None):
        self.display = display
        self.root = None

    @property
    def value(self):
        """Return current root group for compatibility with older code"""
        if self.root is None:
            self.root = displayio.Group()
        return self.root

    @value.setter
    def value(self, group):
        """Set root group"""
        self.root = group

    def claim_display(self, display):
        self.display = display

    def new_root(self):
        self.root = displayio.Group()
        return self.root

    def show_splash(self, group):
        if not self.display:
            return False
        self.display.root_group = group
        return True

    def clear(self):
        if not self.display:
            return False
        self.display.root_group = displayio.Group()
        return True

    def show_text(self, text, color=0xFFFFFF, x=10, y=10, font=None):
        f = font or terminalio.FONT
        g = displayio.Group()
        t = label.Label(f, text=text, color=color, x=x, y=y)
        g.append(t)
        self.show_splash(g)
        return t

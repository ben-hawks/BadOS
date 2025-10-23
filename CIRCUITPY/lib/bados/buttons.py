"""
Buttons implementation for BadOS with correct pull-down/active-high logic.

Features:
- Accepts config objects with get_all_buttons() method OR a list of pin names
- Uses pull-down resistors (active-high: pressed = True)
- Implements: read(), poll(), await_click(), names(), register_callback()
"""

import time

try:
    import board
except Exception:
    board = None

try:
    import digitalio
except Exception:
    digitalio = None

DEFAULT_NAMES = ["SW_A", "SW_B", "SW_C", "SW_UP", "SW_DOWN"]

class Buttons:
    def __init__(self, config_or_names=None, active_level=None, debounce=0.04):
        """Initialize Buttons wrapper.

        config_or_names: either a config object with get_all_buttons() method,
                        or a list of board attr names to use; defaults to DEFAULT_NAMES.
        active_level: boolean indicating the raw value when pressed. If None,
                      default to True (active-high for pull-down).
        debounce: seconds of stable reading required to accept a press.
        """
        self.debounce = debounce
        # Default to active_high (pressed == True) for pull-down buttons
        self.active_level = True if active_level is None else bool(active_level)
        self._btn_objs = {}  # name -> obj (board attr or DigitalInOut)
        self._last_event = None
        self._callbacks = []
        self._last_states = {}

        # Determine button mapping
        button_mapping = {}
        if config_or_names is None:
            # Use default names
            for name in DEFAULT_NAMES:
                if board is not None:
                    pin = getattr(board, name, None)
                    if pin is not None:
                        button_mapping[name.replace('SW_', '')] = pin
        elif hasattr(config_or_names, 'get_all_buttons'):
            # Config object with get_all_buttons() method
            try:
                button_mapping = config_or_names.get_all_buttons()
            except Exception as e:
                print(f"Warning: could not get buttons from config: {e}")
                button_mapping = {}
        elif isinstance(config_or_names, (list, tuple)):
            # List of button names
            for name in config_or_names:
                if board is not None:
                    pin = getattr(board, name, None)
                    if pin is not None:
                        button_mapping[name.replace('SW_', '')] = pin
        elif isinstance(config_or_names, dict):
            # Direct dictionary mapping
            button_mapping = config_or_names

        # Initialize button objects
        for name, pin in button_mapping.items():
            obj = None
            if pin is not None:
                # If the pin already exposes .value, use as-is (runtime configured)
                if hasattr(pin, 'value'):
                    obj = pin
                else:
                    # Pin object - try to create DigitalInOut wrapper with pull-down
                    if digitalio is not None:
                        try:
                            d = digitalio.DigitalInOut(pin)
                            d.direction = digitalio.Direction.INPUT
                            try:
                                d.pull = digitalio.Pull.DOWN  # Pull-down for active-high
                            except Exception:
                                pass
                            obj = d
                        except Exception as e:
                            print(f"Warning: could not initialize button {name}: {e}")
                            obj = None

            if obj is not None:
                self._btn_objs[name] = obj
                self._last_states[name] = False

        # Friendly alias
        self.led = None

    def _raw(self, name):
        """Return the raw boolean value for a button or None if unreadable."""
        obj = self._btn_objs.get(name)
        if obj is None:
            return None
        try:
            if hasattr(obj, 'value'):
                return obj.value
            return bool(obj)
        except Exception:
            return None

    def _is_pressed_raw(self, raw):
        """Convert raw value to pressed state based on active_level."""
        if raw is None:
            return False
        return bool(raw) == bool(self.active_level)

    def read(self, name):
        """Return True if the named button is pressed, False otherwise."""
        raw = self._raw(name)
        return self._is_pressed_raw(raw)

    def names(self):
        """Return list of button names."""
        return list(self._btn_objs.keys())

    def register_callback(self, fn):
        """Register fn(name, pressed) to be called when a button state changes."""
        if callable(fn):
            self._callbacks.append(fn)

    def poll(self):
        """Poll all buttons and dispatch change events."""
        for name in self.names():
            pressed = self.read(name)
            last = self._last_states.get(name, False)
            if pressed != last:
                self._last_states[name] = pressed
                # Call all registered callbacks
                for cb in list(self._callbacks):
                    try:
                        cb(name, pressed)
                    except Exception:
                        pass

    def await_click(self, timeout=None):
        """Block until a button is pressed and released, or timeout; return button name or None."""
        deadline = None if timeout is None else time.time() + timeout
        while True:
            for name in list(self._btn_objs.keys()):
                raw = self._raw(name)
                if raw is None:
                    continue
                if self._is_pressed_raw(raw):
                    # debounce: ensure it stays pressed for debounce interval
                    t_end = time.time() + self.debounce
                    stable = True
                    while time.time() < t_end:
                        cur = self._raw(name)
                        if not self._is_pressed_raw(cur):
                            stable = False
                            break
                        time.sleep(0.005)
                    if stable:
                        # Wait for button release before returning
                        while self._is_pressed_raw(self._raw(name)):
                            time.sleep(0.01)
                        # Small delay after release for debounce
                        time.sleep(self.debounce)
                        self._last_event = (name, raw)
                        return name  # Return button name directly
            if deadline and time.time() > deadline:
                return None
            time.sleep(0.01)

    def set_led(self, value):
        """Set LED on/off if available."""
        if self.led is not None:
            try:
                self.led.value = bool(value)
            except Exception:
                pass

    def get_event(self):
        """Get and clear the last event."""
        e = self._last_event
        self._last_event = None
        return e

    def deinit(self):
        """Clean up any DigitalInOut objects we created."""
        if digitalio is None:
            self._btn_objs.clear()
            return
        for name, obj in list(self._btn_objs.items()):
            try:
                if isinstance(obj, digitalio.DigitalInOut):
                    try:
                        obj.deinit()
                    except Exception:
                        pass
            except Exception:
                pass
        self._btn_objs.clear()

    def label(self, name):
        """Return friendly label for button name."""
        if name is None:
            return None
        if name.endswith('_A') or name == 'SW_A' or name == 'A':
            return 'A'
        if name.endswith('_B') or name == 'SW_B' or name == 'B':
            return 'B'
        if name.endswith('_C') or name == 'SW_C' or name == 'C':
            return 'C'
        if name.endswith('_UP') or name == 'SW_UP' or name == 'UP':
            return 'UP'
        if name.endswith('_DOWN') or name == 'SW_DOWN' or name == 'DOWN':
            return 'DOWN'
        return name

# Backwards compatibility: expose ButtonsShim alias
ButtonsShim = Buttons

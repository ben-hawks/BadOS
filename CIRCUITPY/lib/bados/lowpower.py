"""Low power helpers for BadOS

Provides LowPowerManager that can:
- Disable USB storage (if allowed)
- Enter light sleep (time.sleep) or deep sleep (alarm module)
- Set wake alarms using RTC
- Track wake reasons
- Save/restore system and app state across deep sleep
"""

try:
    import supervisor
    import storage
except Exception:
    supervisor = None
    storage = None

try:
    import alarm
    import alarm.time
    import alarm.pin
except Exception:
    alarm = None

try:
    import wakeup
except Exception:
    wakeup = None

import time
import json

try:
    from bados.logger import get_logger
    logger = get_logger()
except Exception:
    logger = None


class WakeReason:
    """Wake reason constants"""
    UNKNOWN = 0
    ALARM = 1
    BUTTON = 2
    RESET = 3
    USB = 4


class LowPowerManager:
    # State file paths
    STATE_FILE = "/state/system_state.json"
    APP_STATE_FILE = "/state/app_state.json"

    def __init__(self, rtc=None):
        """Initialize low power manager.

        Args:
            rtc: Optional BadOS_RTC instance for alarm-based wakes
        """
        self._rtc = rtc
        self._last_wake_reason = WakeReason.UNKNOWN
        self._system_state = {}
        self._app_state = {}
        self._fs_writable = self._check_filesystem_writable()

        # Ensure state directory exists if filesystem is writable
        if self._fs_writable:
            self._ensure_state_dir()

        # Check wake reason using the frozen wakeup module
        self._check_wake_reason()

        # Load saved state if waking from deep sleep
        if self._last_wake_reason in (WakeReason.ALARM, WakeReason.BUTTON):
            self.load_state()

        if logger:
            logger.info("LowPowerManager initialized")
            logger.info(f"Wake reason: {self._last_wake_reason}")
            logger.info(f"Filesystem writable: {self._fs_writable}")

    def _check_filesystem_writable(self):
        """Check if filesystem is writable"""
        try:
            # Try to write a test file to root
            with open("/.write_test", 'w') as f:
                f.write("test")
            # If successful, delete it
            import os
            os.remove("/.write_test")
            print("LowPowerManager: Filesystem is writable")
            return True
        except (OSError, Exception) as e:
            print(f"LowPowerManager: Filesystem is read-only: {e}")
            return False

    def _ensure_state_dir(self):
        """Create state directory if it doesn't exist"""
        try:
            import os
            try:
                os.stat("/state")
                print("LowPowerManager: /state directory exists")
            except OSError:
                print("LowPowerManager: Creating /state directory...")
                os.mkdir("/state")
                print("LowPowerManager: /state directory created")
        except Exception as e:
            print(f"LowPowerManager: Could not create /state directory: {e}")

    def _check_wake_reason(self):
        """Determine why device woke from sleep using frozen wakeup module"""
        if wakeup:
            try:
                # Use the frozen wakeup module to check wake reason
                if wakeup.rtc_alarm_triggered():
                    self._last_wake_reason = WakeReason.ALARM
                    msg = "Wake reason: RTC alarm (detected by wakeup module)"
                    print(msg)
                    if logger:
                        logger.info(msg)
                elif wakeup.pressed_to_wake():
                    self._last_wake_reason = WakeReason.BUTTON
                    # Determine which button
                    button = None
                    if wakeup.button_a():
                        button = "Button A"
                    elif wakeup.button_b():
                        button = "Button B"
                    elif wakeup.button_c():
                        button = "Button C"
                    elif wakeup.button_up():
                        button = "Button UP"
                    elif wakeup.button_down():
                        button = "Button DOWN"
                    else:
                        button = "Unknown button"
                    msg = f"Wake reason: {button}"
                    print(msg)
                    if logger:
                        logger.info(msg)
                else:
                    self._last_wake_reason = WakeReason.RESET
                    msg = "Wake reason: Power on/reset"
                    print(msg)
                    if logger:
                        logger.info(msg)
                return
            except Exception as e:
                msg = f"Wakeup module error: {e}"
                print(msg)
                if logger:
                    logger.error(msg)

        # Fallback to alarm module if wakeup not available
        if not alarm:
            self._last_wake_reason = WakeReason.RESET
            return

        try:
            wake_alarm = alarm.wake_alarm
            if wake_alarm is None:
                self._last_wake_reason = WakeReason.RESET
            elif isinstance(wake_alarm, alarm.time.TimeAlarm):
                self._last_wake_reason = WakeReason.ALARM
            elif hasattr(alarm.pin, 'PinAlarm') and isinstance(wake_alarm, alarm.pin.PinAlarm):
                self._last_wake_reason = WakeReason.BUTTON
            else:
                self._last_wake_reason = WakeReason.UNKNOWN
        except Exception:
            self._last_wake_reason = WakeReason.UNKNOWN

    @property
    def wake_reason(self):
        """Get the reason for last wake"""
        return self._last_wake_reason

    def get_wake_button(self):
        """Get which button was pressed to wake (if any)

        Returns:
            str: Button name ('A', 'B', 'C', 'UP', 'DOWN') or None
        """
        if not wakeup or not wakeup.pressed_to_wake():
            return None

        if wakeup.button_a():
            return 'A'
        elif wakeup.button_b():
            return 'B'
        elif wakeup.button_c():
            return 'C'
        elif wakeup.button_up():
            return 'UP'
        elif wakeup.button_down():
            return 'DOWN'
        return None

    def disable_usb(self):
        """Disable the USB mass storage drive if storage.disable_usb_drive exists."""
        if storage is None:
            return False
        try:
            if hasattr(storage, "disable_usb_drive"):
                storage.disable_usb_drive()
                return True
        except Exception:
            return False
        return False

    def light_sleep(self, seconds):
        """Simple blocking sleep helper for low-power pauses.

        Args:
            seconds: Time to sleep in seconds

        Returns True on success, False on error.
        """
        try:
            time.sleep(seconds)
            return True
        except Exception:
            return False

    def deep_sleep(self, seconds=None, wake_on_button=None, wake_on_all_buttons=False):
        """Enter deep sleep mode with optional wake conditions.

        Args:
            seconds: Wake after this many seconds (uses alarm.time.TimeAlarm)
            wake_on_button: Button name ('A', 'B', 'C', 'UP', 'DOWN') or Pin object to wake on
            wake_on_all_buttons: If True, wake on any button press

        Returns True if entering deep sleep, False if not supported or error.
        Note: This function will not return if deep sleep is successful.
        """
        if not alarm:
            print("Deep sleep not supported - alarm module not available")
            if seconds:
                print(f"Falling back to light sleep for {seconds}s")
                return self.light_sleep(seconds)
            return False

        alarms = []

        # Add time alarm if requested
        if seconds is not None:
            try:
                time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + seconds)
                alarms.append(time_alarm)
                print(f"Created TimeAlarm for {seconds}s from now")
            except Exception as e:
                print(f"Time alarm error: {e}")
                return False

        # Add button alarm(s) using wakeup helper functions if available
        if wakeup:
            try:
                if wake_on_all_buttons:
                    # Use wakeup helper to create alarms for all buttons
                    button_alarms = wakeup.create_all_button_alarms()
                    alarms.extend(button_alarms)
                    print(f"Created PinAlarms for all buttons")
                elif wake_on_button is not None:
                    # Check if it's a button name string
                    if isinstance(wake_on_button, str):
                        button_alarm = wakeup.create_button_alarm(wake_on_button)
                        alarms.append(button_alarm)
                        print(f"Created PinAlarm for button {wake_on_button}")
                    else:
                        # Legacy: Pin object passed directly
                        if hasattr(alarm.pin, 'PinAlarm'):
                            pin_alarm = alarm.pin.PinAlarm(pin=wake_on_button, value=True, pull=False)
                            alarms.append(pin_alarm)
                            print(f"Created PinAlarm for button wake")
            except Exception as e:
                print(f"Button alarm error: {e}")
        elif wake_on_button is not None:
            # Fallback if wakeup module not available
            try:
                if hasattr(alarm.pin, 'PinAlarm'):
                    # Assume it's a pin object
                    pin_alarm = alarm.pin.PinAlarm(pin=wake_on_button, value=True, pull=False)
                    alarms.append(pin_alarm)
                    print(f"Created PinAlarm for button wake (no wakeup module)")
            except Exception as e:
                print(f"Pin alarm error: {e}")

        if not alarms:
            print("No wake conditions set")
            return False

        print(f"Entering deep sleep with {len(alarms)} alarm(s)...")
        print("NOTE: If the device resets instead of sleeping, deep sleep may not be supported")

        try:
            # Enter deep sleep - this does not return if successful
            if len(alarms) == 1:
                alarm.exit_and_deep_sleep_until_alarms(alarms[0])
            else:
                alarm.exit_and_deep_sleep_until_alarms(*alarms)

            # If we reach here, deep sleep failed
            print("WARNING: Deep sleep call returned (should not happen)")
            print("Device may not support deep sleep - using light sleep instead")
            if seconds:
                return self.light_sleep(seconds)
            return False

        except Exception as e:
            print(f"Deep sleep error: {e}")
            print("Falling back to light sleep")
            if seconds:
                return self.light_sleep(seconds)
            return False

    def sleep_until_alarm(self, seconds):
        """Sleep until RTC alarm fires.

        Configures RTC hardware alarm and uses wakeup module helper for proper deep sleep.
        Relies solely on RTC hardware alarm (no backup timer).

        Args:
            seconds: Seconds to sleep

        IMPORTANT: This function does NOT return if deep sleep is successful!
        The device will reset when it wakes up.
        """
        if logger:
            logger.info(f"sleep_until_alarm called: {seconds}s")

        # Configure RTC hardware alarm if we have RTC and wakeup
        if not self._rtc:
            msg = "RTC not available - cannot use RTC alarm"
            print(msg)
            if logger:
                logger.error(msg)
            return False

        if not wakeup:
            msg = "Wakeup module not available - cannot use RTC alarm"
            print(msg)
            if logger:
                logger.error(msg)
            return False

        if not alarm:
            msg = "Alarm module not available - cannot enter deep sleep"
            print(msg)
            if logger:
                logger.error(msg)
            return False

        try:
            # Set the RTC alarm time
            # The BadOS_RTC.set_alarm() method handles enabling interrupts internally
            if logger:
                logger.debug(f"Setting RTC alarm for {seconds}s from now")

            if not self._rtc.set_alarm(seconds_from_now=seconds):
                msg = "Failed to set RTC alarm time"
                print(msg)
                if logger:
                    logger.error(msg)
                return False

            msg = f"RTC hardware alarm configured for {seconds}s"
            print(msg)
            if logger:
                logger.info(msg)

            # Create RTC alarm PinAlarm using wakeup helper
            # This creates the correct PinAlarm for GPIO8 (RTC interrupt pin)
            if logger:
                logger.debug("Creating RTC PinAlarm")

            rtc_alarm = None
            try:
                rtc_alarm = wakeup.create_rtc_alarm()
            except Exception as e:
                # Provide helpful diagnostics about who owns the pin
                owner_info = None
                try:
                    import board as _board
                    pin_obj = getattr(_board, 'GP8', None) or getattr(_board, 'RTC_ALARM', None) or getattr(_board, 'D8', None)
                    if pin_obj is not None and hasattr(wakeup, 'describe_pin_owner'):
                        owner_info = wakeup.describe_pin_owner(pin_obj)
                    else:
                        owner_info = repr(pin_obj)
                except Exception as ie:
                    owner_info = f"(could not inspect board pin: {ie})"

                msg = f"Could not create RTC PinAlarm: {e}; pin_owner={owner_info}"
                print(msg)
                if logger:
                    logger.error(msg)

            # Also add button wake capability so we can interrupt if needed
            if logger:
                logger.debug("Creating button PinAlarms")

            button_alarms = []
            try:
                button_alarms = wakeup.create_all_button_alarms()
            except Exception as e_all:
                # Fall back to creating button alarms one-by-one, skipping pins already in use
                if logger:
                    logger.warning(f"create_all_button_alarms failed: {e_all}; falling back to per-button creation")
                try:
                    import board as _board
                    for btn_name in ('A', 'B', 'C', 'UP', 'DOWN'):
                        try:
                            # If the board pin wrapper already exposes .value, it means
                            # some code (main/menu/buttons) already configured it
                            # with DigitalInOut and claiming the pin. Skip creating
                            # a PinAlarm in that case and rely on the frozen wakeup
                            # GPIO snapshot for button wake detection.
                            pin_attr = f"SW_{btn_name}"
                            pin_obj = getattr(_board, pin_attr, None)
                            if pin_obj is not None and hasattr(pin_obj, 'value'):
                                if logger:
                                    logger.debug(f"Skipping PinAlarm for {pin_attr}: already configured (value attr present)")
                                continue

                            pa = wakeup.create_button_alarm(btn_name)
                            button_alarms.append(pa)
                        except Exception as e_btn:
                            # Report who owns the pin for diagnostics
                            try:
                                owner_info = wakeup.describe_pin_owner(pin_obj) if (pin_obj is not None and hasattr(wakeup, 'describe_pin_owner')) else repr(pin_obj)
                            except Exception:
                                owner_info = "(could not inspect pin owner)"
                            if logger:
                                logger.debug(f"Skipping button {btn_name}: {e_btn}; owner={owner_info}")
                except Exception as e:
                    if logger:
                        logger.error(f"Per-button alarm fallback failed: {e}")

            # Build final alarms list to pass into exit_and_deep_sleep_until_alarms
            # Require the RTC PinAlarm to be available: we rely solely on the
            # hardware RTC alarm for wake; do not fall back to time-based alarms.
            if rtc_alarm is None:
                msg = "RTC PinAlarm unavailable; deep sleep requires the RTC hardware alarm"
                print(msg)
                if logger:
                    logger.error(msg)
                return False

            # Build final alarms list: rtc alarm first, then any button PinAlarms
            final_alarms = [rtc_alarm] + [a for a in button_alarms if a is not None]

            msg = f"Entering deep sleep with {len(final_alarms)} alarm(s) (rtc_pin_present=True, button_alarms={len(button_alarms)})"
            print(msg)
            if logger:
                logger.info(msg)
                logger.info("=== ENTERING DEEP SLEEP NOW ===")

            # Build argument list for exit call depending on what's available
            try:
                # Only pass non-None alarms
                if len(final_alarms) == 1:
                    alarm.exit_and_deep_sleep_until_alarms(final_alarms[0])
                else:
                    alarm.exit_and_deep_sleep_until_alarms(*final_alarms)

                # We should NEVER reach this point - if we do, deep sleep failed
                msg = "CRITICAL: Deep sleep call returned - this should never happen!"
                print(msg)
                if logger:
                    logger.error(msg)
                return False

            except Exception as e:
                msg = f"Deep sleep exit call failed: {e}"
                print(msg)
                if logger:
                    logger.error(msg)
                # Fall back to light sleep
                if seconds:
                    return self.light_sleep(seconds)
                return False

        except Exception as e:
            msg = f"RTC alarm setup exception: {e}"
            print(msg)
            if logger:
                logger.error(msg)
                import traceback
                import io
                s = io.StringIO()
                # Use correct print_exception signature: (exc_type, exc, tb, file=...)
                try:
                    traceback.print_exception(type(e), e, e.__traceback__, file=s)
                    logger.error(s.getvalue())
                except Exception:
                    # Fallback to print_exc
                    s = io.StringIO()
                    traceback.print_exc(file=s)
                    logger.error(s.getvalue())
            return False


    def sleep_until_button(self, button_name=None, timeout_seconds=None):
        """Sleep until button pressed or timeout.

        Args:
            button_name: Button name ('A', 'B', 'C', 'UP', 'DOWN') or None for any button
            timeout_seconds: Optional timeout in seconds

        Returns True on success.
        """
        if button_name is None:
            # Wake on any button
            return self.deep_sleep(seconds=timeout_seconds, wake_on_all_buttons=True)
        elif timeout_seconds:
            return self.deep_sleep(seconds=timeout_seconds, wake_on_button=button_name)
        else:
            return self.deep_sleep(wake_on_button=button_name)

    def get_battery_voltage(self):
        """Get current battery voltage if available.

        Returns voltage as float or None if not available.
        """
        try:
            import analogio
            import board
            battery = analogio.AnalogIn(board.VOLTAGE_MONITOR)
            raw = battery.value
            # Calibration: voltage = (raw / 10000) + 1
            volt = (raw / 10000) + 1.0
            battery.deinit()
            return volt
        except Exception:
            return None

    def should_sleep(self, idle_seconds=300, min_battery=3.2):
        """Check if device should enter sleep mode.

        Args:
            idle_seconds: Seconds of idle before suggesting sleep
            min_battery: Minimum battery voltage before forcing sleep

        Returns True if sleep recommended, False otherwise.
        """
        # Check battery voltage
        voltage = self.get_battery_voltage()
        if voltage and voltage < min_battery:
            print(f"Low battery: {voltage:.2f}V - sleep recommended")
            return True

        # Could add idle detection logic here
        return False

    def save_state(self, system_state=None, app_state=None):
        """Save system and app state to persistent storage.

        Uses filesystem if writable, otherwise falls back to RTC RAM byte.

        Args:
            system_state: Dict of system-level state to save (e.g., menu position, settings)
            app_state: Dict of app-specific state to save

        Returns True on success, False on failure.
        """
        print(f"LowPowerManager.save_state called - fs_writable={self._fs_writable}")

        try:
            # Update internal state
            if system_state is not None:
                self._system_state = system_state
                print(f"System state to save: {system_state}")
            if app_state is not None:
                self._app_state = app_state
                print(f"App state to save: {app_state}")

            if self._fs_writable:
                print("Using filesystem for state persistence")
                # Use filesystem for full state
                if system_state is not None:
                    print(f"Writing system state to {self.STATE_FILE}...")
                    try:
                        with open(self.STATE_FILE, 'w') as f:
                            json.dump(system_state, f)
                        print("System state saved successfully")
                    except Exception as e:
                        print(f"ERROR writing system state: {e}")
                        raise

                if app_state is not None:
                    print(f"Writing app state to {self.APP_STATE_FILE}...")
                    try:
                        with open(self.APP_STATE_FILE, 'w') as f:
                            json.dump(app_state, f)
                        print("App state saved successfully")
                    except Exception as e:
                        print(f"ERROR writing app state: {e}")
                        raise

                print("State save completed successfully")
                return True
            else:
                print("Filesystem read-only, trying RTC RAM fallback")
                # Fallback: Use RTC RAM byte for simple counter
                # Can only store 0-255, so use it for a simple state flag/counter
                if self._rtc and hasattr(self._rtc._driver, 'ram_byte'):
                    # Store simple counter in RAM byte
                    counter = app_state.get('sleep_count', 0) if app_state else 0
                    self._rtc._driver.ram_byte = min(counter, 255)
                    print(f"State saved to RTC RAM: counter={counter}")
                    return True
                else:
                    print("WARNING: Filesystem read-only and RTC RAM not available")
                    print("To enable state persistence:")
                    print("1. Disconnect USB and reboot the device")
                    print("2. Check boot.py remount logic")
                    return False

        except Exception as e:
            print(f"State save error: {e}")
            import traceback
            traceback.print_exception(e)
            return False

    def load_state(self):
        """Load system and app state from persistent storage.

        Returns tuple of (system_state, app_state) dicts.
        """
        try:
            if self._fs_writable:
                # Load from filesystem
                try:
                    with open(self.STATE_FILE, 'r') as f:
                        self._system_state = json.load(f)
                except (OSError, ValueError):
                    self._system_state = {}

                try:
                    with open(self.APP_STATE_FILE, 'r') as f:
                        self._app_state = json.load(f)
                except (OSError, ValueError):
                    self._app_state = {}
            else:
                # Fallback: Load from RTC RAM byte
                if self._rtc and hasattr(self._rtc._driver, 'ram_byte'):
                    counter = self._rtc._driver.ram_byte
                    self._app_state = {'sleep_count': counter}
                    print(f"State loaded from RTC RAM: counter={counter}")
                else:
                    self._app_state = {}

            return (self._system_state, self._app_state)
        except Exception as e:
            print(f"State load error: {e}")
            return ({}, {})

    def get_system_state(self, key=None, default=None):
        """Get system state value.

        Args:
            key: State key to retrieve (None returns entire dict)
            default: Default value if key doesn't exist

        Returns state value or default.
        """
        if key is None:
            return self._system_state
        return self._system_state.get(key, default)

    def get_app_state(self, key=None, default=None):
        """Get app state value.

        Args:
            key: State key to retrieve (None returns entire dict)
            default: Default value if key doesn't exist

        Returns state value or default.
        """
        if key is None:
            return self._app_state
        return self._app_state.get(key, default)

    def clear_state(self, clear_system=True, clear_app=True):
        """Clear saved state.

        Args:
            clear_system: Clear system state
            clear_app: Clear app state

        Returns True on success.
        """
        try:
            if clear_system:
                self._system_state = {}
                try:
                    import os
                    os.remove(self.STATE_FILE)
                except OSError:
                    pass

            if clear_app:
                self._app_state = {}
                try:
                    import os
                    os.remove(self.APP_STATE_FILE)
                except OSError:
                    pass

            return True
        except Exception as e:
            print(f"State clear error: {e}")
            return False

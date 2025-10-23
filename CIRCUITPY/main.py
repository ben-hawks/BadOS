"""BadOS Main Menu - bhawks_brainbadge_rp2040

Main menu launcher for BadOS apps.
"""

import time
import gc
import board
import displayio
import terminalio
import digitalio
import busio

print("\n" + "="*50)
print("BadOS v3.0")
print("="*50)

# Initialize display
print("Initializing display...")
display = board.DISPLAY

# Verify display is valid
if display is None:
    print("ERROR: Display not available!")
    import supervisor
    supervisor.reload()

print(f"Display: {display.width}x{display.height}")

# Initialize buttons with PULL-DOWN (active-high)
print("Initializing buttons...")
buttons_dict = {}
led = None

for name in ['A', 'B', 'C', 'UP', 'DOWN']:
    pin_name = f'SW_{name}'
    pin = getattr(board, pin_name, None)
    if pin is None:
        continue

    # If already configured by runtime, use as-is
    if hasattr(pin, 'value'):
        buttons_dict[name] = pin
    else:
        # Wrap raw pin with pull-down
        try:
            btn = digitalio.DigitalInOut(pin)
            btn.direction = digitalio.Direction.INPUT
            btn.pull = digitalio.Pull.DOWN
            buttons_dict[name] = btn
        except Exception as e:
            print(f"Warning: Could not init {name}: {e}")

# Initialize LED
led_pin = board.USER_LED
if hasattr(led_pin, 'value'):
    led = led_pin
else:
    led = digitalio.DigitalInOut(led_pin)
    led.direction = digitalio.Direction.OUTPUT
    led.value = False

# Create shared I2C bus for RTC and other peripherals
print("Initializing I2C bus...")
try:
    i2c = busio.I2C(board.SCL, board.SDA)
    print("I2C bus initialized")
except Exception as e:
    print(f"I2C init failed: {e}")
    i2c = None

# Create menu components
print("Creating menu...")
from bados.menu import Menu, Status_Bar
from bados.buttons import Buttons
from bados.screen import Screen

# Use real bados Screen class
screen = Screen(display)

# Use bados Buttons class
buttons = Buttons(buttons_dict)
buttons.led = led

# App list - use actual icon paths from existing apps
test_items = [
    ("BADGE", "/apps/badge/badge.bmp", "/apps/badge/badge.py"),
    ("CLOCK", "/apps/clock/clock.bmp", "/apps/clock/clock.py"),
    ("D20", "/apps/d20/d20.bmp", "/apps/d20/d20.py"),
    ("DUCKY", "/apps/ducky/ducky.bmp", "/apps/ducky/ducky.py"),
    ("IMAGE", "/apps/image/image.bmp", "/apps/image/image.py"),
    ("LOGS", "/assets/icons/file.bmp", "/apps/log_viewer.py"),  # Log viewer
    ("POWER", "/assets/icons/file.bmp", "/apps/power_demo_stateful.py"),  # Power demo
    ("PREFS", "/apps/prefs/prefs.bmp", "/apps/prefs/prefs.py"),
]

# Check if we're waking from deep sleep and should relaunch an app
print("Checking for deep sleep wake...")
try:
    from bados.rtc import BadOS_RTC
    from bados.lowpower import LowPowerManager, WakeReason

    rtc = BadOS_RTC(i2c=i2c)  # Pass the shared I2C bus

    # If the frozen wakeup capture shows the RTC alarm fired, try to clear it
    try:
        import wakeup as _wakeup
        if hasattr(_wakeup, 'rtc_alarm_triggered') and _wakeup.rtc_alarm_triggered():
            print("main.py: Detected RTC alarm via wakeup capture; attempting to clear via BadOS_RTC")
            try:
                # Use high-level clear_alarm method when available
                if hasattr(rtc, 'clear_alarm'):
                    rtc.clear_alarm()
                    print("main.py: RTC alarm cleared via BadOS_RTC.clear_alarm()")
                else:
                    # Last resort: try to clear driver flags directly
                    if hasattr(rtc, '_driver') and rtc._driver is not None:
                        try:
                            rtc._driver.alarm_status = False
                            print("main.py: RTC alarm_status cleared on driver")
                        except Exception:
                            try:
                                rtc._driver.alarm = None
                                print("main.py: RTC alarm cleared via driver.alarm=None")
                            except Exception as e:
                                print(f"main.py: Could not clear RTC alarm on driver: {e}")

                # Additionally, if the frozen wakeup helper exists, clear snapshot flags
                try:
                    import wakeup as _wakeup
                    # Clear the RTC alarm flag in the driver via wakeup helper if available
                    if hasattr(_wakeup, 'clear_rtc_alarm'):
                        try:
                            if hasattr(rtc, '_driver') and rtc._driver is not None:
                                _wakeup.clear_rtc_alarm(rtc._driver)
                                print('main.py: wakeup.clear_rtc_alarm called on driver')
                        except Exception as e:
                            print(f'main.py: wakeup.clear_rtc_alarm failed: {e}')
                    # Additionally, disable RTC alarm interrupt output to avoid spurious INTs
                    if hasattr(_wakeup, 'configure_rtc_alarm_interrupt'):
                        try:
                            if hasattr(rtc, '_driver') and rtc._driver is not None:
                                _wakeup.configure_rtc_alarm_interrupt(rtc._driver, False)
                                print('main.py: RTC alarm interrupt disabled via wakeup.configure_rtc_alarm_interrupt')
                        except Exception as e:
                            print(f'main.py: configure_rtc_alarm_interrupt failed: {e}')
                except Exception:
                    pass

            except Exception as e:
                print(f"main.py: Failed to clear RTC alarm: {e}")
    except Exception:
        # If wakeup module isn't importable here, skip silently
        pass

    power = LowPowerManager(rtc=rtc)

    print(f"Wake reason detected: {power.wake_reason}")
    print(f"WakeReason.ALARM = {WakeReason.ALARM}")
    print(f"WakeReason.BUTTON = {WakeReason.BUTTON}")
    print(f"WakeReason.RESET = {WakeReason.RESET}")

    # If waking from alarm or button, check if there's a saved app to relaunch
    if power.wake_reason in (WakeReason.ALARM, WakeReason.BUTTON):
        print("Detected deep sleep wake - checking for saved app...")

        # Load state explicitly to ensure it's available
        system_state, app_state = power.load_state()
        print(f"Loaded system state: {system_state}")
        print(f"Loaded app state: {app_state}")

        saved_app = power.get_system_state('resume_app_path')
        saved_app_name = power.get_system_state('resume_app_name', 'Unknown')

        print(f"Saved app path: {saved_app}")
        print(f"Saved app name: {saved_app_name}")

        if saved_app:
            print(f"Waking from deep sleep - relaunching: {saved_app_name}")
            print(f"Wake reason: {power.wake_reason}")

            # Flash LED to indicate resume
            if led:
                for _ in range(3):
                    led.value = True
                    time.sleep(0.1)
                    led.value = False
                    time.sleep(0.1)

            try:
                gc.collect()

                # Create globals dict for app with power manager available
                app_globals = {
                    '__name__': '__main__',
                    'gc': gc,
                    'board': board,
                    'displayio': displayio,
                    'time': time,
                    'display': display,
                    'buttons': buttons,
                    'screen': screen,
                    'i2c': i2c,  # Pass shared I2C bus
                    'rtc': rtc,  # Pass shared RTC instance
                    'power': power,  # Pass shared power manager
                }

                # Execute the saved app
                print(f"Executing app from: {saved_app}")
                with open(saved_app, 'r') as f:
                    exec(f.read(), app_globals)

                # If app exits normally, clear the resume state
                print("App exited normally, clearing resume state...")
                power.clear_state(clear_system=True, clear_app=False)
                print("App exited - returning to menu")

            except Exception as e:
                print(f"ERROR relaunching app: {e}")
                import traceback
                traceback.print_exception(e)
                # Clear bad state
                power.clear_state(clear_system=True, clear_app=False)
                time.sleep(2)
        else:
            print("Waking from deep sleep but no app to resume")
    else:
        print(f"Normal boot (wake reason: {power.wake_reason})")

except Exception as e:
    print(f"Deep sleep check failed: {e}")
    import traceback
    traceback.print_exception(e)
    # Continue to normal menu if check fails

# Create menu
menu = Menu(
    display=display,
    screen=screen,
    buttons=buttons,
    item_list=test_items,
    font=terminalio.FONT,
    defaulticon="/assets/icons/file.bmp"
)

# Debug: verify menu has display
print(f"Menu created with display: {menu.display}")
print(f"Display dimensions: {menu.display.width if menu.display else 'None'}x{menu.display.height if menu.display else 'None'}")

print("Ready!\n")

# Main menu loop
current_page = 0

while True:
    try:
        # Calculate max page dynamically
        max_page = (len(test_items) - 1) // 3

        # Show menu and wait for input
        result = menu.show_menu(current_page)

        # Handle navigation (UP/DOWN) with wrap-around
        if result == -2:  # UP
            current_page = (current_page - 1) % (max_page + 1)
        elif result == -3:  # DOWN
            current_page = (current_page + 1) % (max_page + 1)
        elif result is not None and 0 <= result <= 2:
            item_idx = current_page * 3 + result
            if item_idx < len(test_items):
                app_name, icon_path, app_path = test_items[item_idx]
                print(f"\nLaunching: {app_name}")

                # Flash LED to indicate selection
                if led:
                    led.value = True
                    time.sleep(0.1)
                    led.value = False

                # Launch the app
                try:
                    gc.collect()

                    # Create a globals dict with access to necessary objects
                    # Note: CircuitPython doesn't have __builtins__ like CPython
                    app_globals = {
                        '__name__': '__main__',
                        'gc': gc,
                        'board': board,
                        'displayio': displayio,
                        'time': time,
                        # Pass pre-initialized objects so apps don't reinitialize pins
                        'display': display,
                        'buttons': buttons,
                        'screen': screen,
                        'i2c': i2c,  # Pass shared I2C bus
                        'rtc': rtc,  # Pass shared RTC instance
                        'power': power,  # Pass shared power manager
                    }

                    # Execute the app
                    with open(app_path, 'r') as f:
                        exec(f.read(), app_globals)

                    # When app exits, recreate menu
                    print(f"\nReturning to menu...")
                    gc.collect()
                    menu = Menu(
                        display=display,
                        screen=screen,
                        buttons=buttons,
                        item_list=test_items,
                        font=terminalio.FONT,
                        defaulticon="/assets/icons/file.bmp"
                    )

                except Exception as e:
                    print(f"ERROR: {e}")
                    import traceback
                    traceback.print_exception(e)
                    time.sleep(2)

                    # Try to recover by recreating menu
                    try:
                        gc.collect()
                        menu = Menu(
                            display=display,
                            screen=screen,
                            buttons=buttons,
                            item_list=test_items,
                            font=terminalio.FONT,
                            defaulticon="/assets/icons/file.bmp"
                        )
                    except Exception:
                        print("ERROR: Menu recovery failed")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exception(e)
        time.sleep(1)

'''BadOS Power Management Demo

Demonstrates low power features including:
- RTC time display and sync
- Deep sleep with wake alarms
- Battery monitoring
- Wake reason detection
'''

from time import sleep
import board, displayio
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect
import terminalio

# Use objects from main menu
display = globals().get('display', board.DISPLAY)
buttons = globals().get('buttons')

def show_message(text, duration=2):
    """Show a message on screen"""
    grp = displayio.Group()

    # Add white background
    grp.append(Rect(0, 0, display.width, display.height, fill=0xFFFFFF))

    # Split multi-line text
    lines = text.split('\n')
    y = display.height // 2 - (len(lines) * 8)

    for line in lines:
        lbl = label.Label(terminalio.FONT, text=line, color=0x000000, scale=1)
        lbl.x = 10
        lbl.y = y
        grp.append(lbl)
        y += 12

    display.root_group = grp

    # Wait for display ready
    while display.time_to_refresh > 0:
        sleep(0.01)

    try:
        display.refresh()
    except RuntimeError:
        sleep(0.1)
        try:
            display.refresh()
        except Exception:
            pass

    sleep(duration)

def show_menu(options):
    """Show power demo menu"""
    grp = displayio.Group()

    # Add white background
    grp.append(Rect(0, 0, display.width, display.height, fill=0xFFFFFF))

    y = 10
    for opt in options:
        lbl = label.Label(terminalio.FONT, text=opt, color=0x000000, scale=1)
        lbl.x, lbl.y = 10, y
        grp.append(lbl)
        y += 15

    display.root_group = grp

    while display.time_to_refresh > 0:
        sleep(0.01)

    try:
        display.refresh()
    except RuntimeError:
        sleep(0.1)
        try:
            display.refresh()
        except Exception:
            pass

# Check if we have required objects
if not display:
    print("ERROR: No display available")
    raise RuntimeError("Display not available")

if not buttons:
    show_message("ERROR:\nNo buttons\navailable", 3)
    raise RuntimeError("Buttons not available")

show_message("Initializing...", 1)

# Try to import power modules with error handling
rtc = None
power = None

try:
    from bados.rtc import BadOS_RTC
    rtc = BadOS_RTC()
    print("RTC initialized")
except Exception as e:
    print(f"RTC init failed: {e}")
    show_message(f"RTC init failed:\n{e}", 3)

try:
    from bados.lowpower import LowPowerManager, WakeReason
    power = LowPowerManager(rtc=rtc)
    print("Power manager initialized")
except Exception as e:
    print(f"Power init failed: {e}")
    show_message(f"Power init failed:\n{e}", 3)

# Check wake reason if power manager available
if power:
    wake = power.wake_reason
    if wake == WakeReason.ALARM:
        show_message("Woke from alarm!", 2)
    elif wake == WakeReason.BUTTON:
        show_message("Woke from button!", 2)

show_message("Power Demo Ready", 1)

# Main loop
while True:
    options = [
        "Power Management Demo",
        "",
        "A: Show Time",
        "B: Battery Info",
        "C: Sleep 10s",
        "UP: Sync NTP",
        "DOWN: Exit"
    ]

    show_menu(options)

    btn = buttons.await_click()

    if btn == 'A':  # Show time
        if rtc:
            now = rtc.now()
            if now:
                time_str = (f"{now.tm_year}-{now.tm_mon:02d}-{now.tm_mday:02d}\n"
                           f"{now.tm_hour:02d}:{now.tm_min:02d}:{now.tm_sec:02d}")
                show_message(time_str, 3)
            else:
                show_message("RTC time\nnot set", 2)
        else:
            show_message("RTC not\navailable", 2)

    elif btn == 'B':  # Battery info
        if power:
            volt = power.get_battery_voltage()
            if volt:
                pct = max(0, min(100, int((volt - 3.2) / (4.2 - 3.2) * 100)))
                msg = f"Battery:\n{volt:.2f}V\n({pct}%)"
                show_message(msg, 3)
            else:
                show_message("Battery\nN/A", 2)
        else:
            show_message("Power manager\nnot available", 2)

    elif btn == 'C':  # Sleep 10 seconds
        if power:
            show_message("Sleeping 10s...\nPress button\nto wake", 2)
            power.sleep_until_alarm(10)
            show_message("Woke up!", 2)
        else:
            show_message("Power manager\nnot available", 2)

    elif btn == 'UP':  # Sync NTP
        if rtc:
            show_message("Syncing NTP...\n(requires WiFi)", 1)
            try:
                # Use verbose mode for detailed diagnostics
                if rtc.sync_from_ntp(verbose=True):
                    now = rtc.now()
                    time_str = f"Synced!\n{now.tm_hour:02d}:{now.tm_min:02d}:{now.tm_sec:02d}"
                    show_message(time_str, 3)
                else:
                    show_message("NTP sync failed\nCheck serial\nfor details", 3)
            except Exception as e:
                show_message(f"NTP error:\n{str(e)[:20]}", 3)
        else:
            show_message("RTC not\navailable", 2)

    elif btn == 'DOWN':  # Exit
        break

show_message("Exiting...", 1)

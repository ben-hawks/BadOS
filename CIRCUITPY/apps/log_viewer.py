"""Log Viewer App - View debug logs on the e-paper display"""

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
    grp.append(Rect(0, 0, display.width, display.height, fill=0xFFFFFF))

    lines = text.split('\n')
    y = 10

    for line in lines:
        lbl = label.Label(terminalio.FONT, text=line, color=0x000000, scale=1)
        lbl.x = 5
        lbl.y = y
        grp.append(lbl)
        y += 10
        if y > display.height - 10:
            break

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

    sleep(duration)

# Initialize
if not display or not buttons:
    print("ERROR: Display or buttons not available")
    # Don't raise - just show message and exit
    try:
        show_message("ERROR:\nDisplay or\nbuttons not\navailable", 3)
    except:
        pass
    import sys
    sys.exit()

try:
    show_message("Log Viewer\nLoading...", 1)
except Exception as e:
    print(f"Display error: {e}")
    import sys
    sys.exit()

LOG_FILE = "/logs/debug.log"

# Read log file
try:
    with open(LOG_FILE, 'r') as f:
        log_lines = f.readlines()

    if not log_lines:
        show_message("Log file is empty", 3)
        import sys
        sys.exit()

    # Show last 20 lines
    log_lines = log_lines[-20:]

except OSError:
    show_message("No log file found\nat:\n/logs/debug.log\n\nRun an app to\ncreate logs", 3)
    import sys
    sys.exit()
except Exception as e:
    show_message(f"Error reading\nlogs:\n{str(e)[:30]}", 3)
    print(f"Log viewer error: {e}")
    import traceback
    traceback.print_exception(e)
    import sys
    sys.exit()

# Pagination
lines_per_page = 15
total_pages = (len(log_lines) + lines_per_page - 1) // lines_per_page
current_page = total_pages - 1  # Start at last page

try:
    show_message(f"Log Viewer\n{len(log_lines)} lines\n{total_pages} pages\n\nUP/DOWN: scroll\nC: Clear logs\nB: Exit", 2)
except Exception as e:
    print(f"Display error: {e}")

while True:
    try:
        # Show current page
        start_idx = current_page * lines_per_page
        end_idx = min(start_idx + lines_per_page, len(log_lines))

        page_lines = log_lines[start_idx:end_idx]

        grp = displayio.Group()
        grp.append(Rect(0, 0, display.width, display.height, fill=0xFFFFFF))

        # Title
        title = f"Logs {current_page + 1}/{total_pages}"
        lbl = label.Label(terminalio.FONT, text=title, color=0x000000, scale=1)
        lbl.x, lbl.y = 5, 5
        grp.append(lbl)

        # Log lines
        y = 18
        for line in page_lines:
            # Truncate long lines
            line = line.rstrip('\n')
            if len(line) > 50:
                line = line[:47] + "..."

            lbl = label.Label(terminalio.FONT, text=line, color=0x000000, scale=1)
            lbl.x, lbl.y = 2, y
            grp.append(lbl)
            y += 9

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

        # Wait for button
        btn = buttons.await_click()

        if btn == 'UP':
            if current_page > 0:
                current_page -= 1
        elif btn == 'DOWN':
            if current_page < total_pages - 1:
                current_page += 1
        elif btn == 'C':
            # Clear logs
            show_message("Clear logs?\n\nA: Yes\nB: No", 2)
            confirm = buttons.await_click()
            if confirm == 'A':
                try:
                    import os
                    os.remove(LOG_FILE)
                    try:
                        os.remove(LOG_FILE + ".old")
                    except:
                        pass
                    show_message("Logs cleared!", 1)
                except Exception as e:
                    show_message(f"Clear failed:\n{e}", 3)
                break
        elif btn == 'B':
            break

    except Exception as e:
        print(f"Log viewer loop error: {e}")
        import traceback
        traceback.print_exception(e)
        show_message(f"ERROR:\n{str(e)[:40]}\n\nExiting...", 3)
        break

try:
    show_message("Exiting...", 1)
except:
    pass

"""Dump pin owner diagnostics to /logs/pin_owners.txt

Run this on the badge (copy to CIRCUITPY/scripts or execute from REPL). It writes
owner info for GP8/RTC_ALARM, SCL/SDA and all SW_* pins so you can inspect which
object/driver has claimed each pin (useful when PinAlarm creation fails).

Usage:
    import dump_pin_owners
    dump_pin_owners.run()

The output file will be /logs/pin_owners.txt on the device filesystem.
"""

import os
import time

try:
    import board
    import wakeup
except Exception:
    board = None
    wakeup = None

OUT_DIR = "/logs"
OUT_FILE = OUT_DIR + "/pin_owners.txt"

def _safe_describe(name, pin_obj):
    try:
        if wakeup and hasattr(wakeup, 'describe_pin_owner'):
            return wakeup.describe_pin_owner(pin_obj)
        # Fallback: basic repr
        return repr(pin_obj)
    except Exception as e:
        return f"<describe error: {e}>"


def run():
    try:
        if not os.path.exists(OUT_DIR):
            try:
                os.mkdir(OUT_DIR)
            except Exception:
                # On some CircuitPython builds /logs may not be writable; fall back to root
                global OUT_FILE
                OUT_FILE = "/pin_owners.txt"

        lines = []
        lines.append(f"Pin owner dump: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        targets = [
            ("GP8", getattr(board, 'GP8', None)),
            ("RTC_ALARM", getattr(board, 'RTC_ALARM', None)),
            ("SCL", getattr(board, 'SCL', None)),
            ("SDA", getattr(board, 'SDA', None)),
            ("SW_A", getattr(board, 'SW_A', None)),
            ("SW_B", getattr(board, 'SW_B', None)),
            ("SW_C", getattr(board, 'SW_C', None)),
            ("SW_UP", getattr(board, 'SW_UP', None)),
            ("SW_DOWN", getattr(board, 'SW_DOWN', None)),
        ]

        for name, pin in targets:
            desc = _safe_describe(name, pin)
            lines.append(f"{name}: {desc}")

        # Also check if any module likely initialized I2C
        i2c_owner = []
        try:
            import sys
            for m in sys.modules:
                if 'i2c' in m.lower() or 'busio' in m.lower() or 'pcf' in m.lower():
                    i2c_owner.append(m)
        except Exception:
            pass

        lines.append("")
        lines.append("Likely modules in sys.modules that mention I2C/PCF:")
        lines.extend([f" - {m}" for m in i2c_owner])

        # Write out
        with open(OUT_FILE, 'w') as f:
            f.write('\n'.join(lines))

        # Also print to stdout for immediate REPL reading
        print('\n'.join(lines))
        print(f"Wrote pin owner dump to: {OUT_FILE}")

    except Exception as e:
        print(f"Failed to write pin owner dump: {e}")


if __name__ == '__main__':
    run()

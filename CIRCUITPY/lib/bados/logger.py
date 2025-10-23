"""Simple file logger for BadOS debugging

Logs to /logs/debug.log with automatic rotation when file gets too large.
"""

import time

class Logger:
    """Simple file logger for debugging without serial console"""

    LOG_FILE = "/logs/debug.log"
    MAX_LOG_SIZE = 50000  # 50KB max before rotation

    def __init__(self, enabled=True):
        self.enabled = enabled
        self._ensure_log_dir()

    def _ensure_log_dir(self):
        """Create logs directory if it doesn't exist"""
        if not self.enabled:
            return
        try:
            import os
            try:
                os.stat("/logs")
            except OSError:
                os.mkdir("/logs")
        except Exception:
            pass

    def _rotate_if_needed(self):
        """Rotate log file if it's too large"""
        try:
            import os
            try:
                stat = os.stat(self.LOG_FILE)
                if stat[6] > self.MAX_LOG_SIZE:  # st_size
                    # Rename to .old
                    try:
                        os.remove(self.LOG_FILE + ".old")
                    except OSError:
                        pass
                    os.rename(self.LOG_FILE, self.LOG_FILE + ".old")
            except OSError:
                pass
        except Exception:
            pass

    def log(self, message, level="INFO"):
        """Write a log message to file

        Args:
            message: Message to log
            level: Log level (INFO, ERROR, DEBUG, WARNING)
        """
        if not self.enabled:
            print(f"[{level}] {message}")
            return

        try:
            self._rotate_if_needed()

            # Get timestamp
            try:
                import rtc
                now = rtc.RTC().datetime
                timestamp = f"{now.tm_year}-{now.tm_mon:02d}-{now.tm_mday:02d} {now.tm_hour:02d}:{now.tm_min:02d}:{now.tm_sec:02d}"
            except:
                timestamp = f"{time.monotonic():.3f}"

            # Write to file
            with open(self.LOG_FILE, 'a') as f:
                f.write(f"[{timestamp}] [{level}] {message}\n")

            # Also print to serial if available
            print(f"[{level}] {message}")

        except Exception as e:
            # Fallback to print if file logging fails
            print(f"[{level}] {message}")
            #print(f"[ERROR] Logging failed: {e}")
            # Best-effort: show error on attached display (e.g. epaper) so users
            # without serial can see critical failure messages.
            try:
                import board
                disp = getattr(board, 'DISPLAY', None)
                if disp is not None:
                    try:
                        import displayio
                        import terminalio
                        from adafruit_display_text import label

                        # Create a simple group with a label
                        g = displayio.Group(max_size=1)
                        text = f"LOG FAIL: {message}"
                        lbl = label.Label(terminalio.FONT, text=text, color=0x000000)
                        lbl.x = 0
                        lbl.y = 10
                        g.append(lbl)
                        disp.show(g)
                    except Exception:
                        # display rendering is best-effort; ignore failures
                        pass
            except Exception:
                pass

    def info(self, message):
        """Log info message"""
        self.log(message, "INFO")

    def error(self, message):
        """Log error message"""
        self.log(message, "ERROR")

    def debug(self, message):
        """Log debug message"""
        self.log(message, "DEBUG")

    def warning(self, message):
        """Log warning message"""
        self.log(message, "WARNING")

    def clear(self):
        """Clear the log file"""
        try:
            import os
            try:
                os.remove(self.LOG_FILE)
            except OSError:
                pass
            try:
                os.remove(self.LOG_FILE + ".old")
            except OSError:
                pass
        except Exception:
            pass


# Global logger instance
_logger = None

def get_logger():
    """Get or create global logger instance"""
    global _logger
    if _logger is None:
        _logger = Logger(enabled=True)
    return _logger

"""NTP time synchronization for BadOS

Provides simple NTP client to get current time from internet time servers.
Uses adafruit_ntp library for Raspberry Pi Pico W compatibility.
"""

try:
    import time
except Exception:
    time = None


def get_ntp_time(ntp_host=None, timeout=10, verbose=True):
    """Get current Unix epoch time from NTP server.

    Args:
        ntp_host: NTP server hostname (uses pool.ntp.org if None)
        timeout: Socket timeout in seconds
        verbose: Print debug messages

    Returns Unix epoch timestamp (int) or None on failure.
    """
    if time is None:
        if verbose:
            print("NTP: Time module not available")
        return None

    # Try to get WiFi and socket pool
    try:
        from bados.wifi import WiFiManager
        wifi_mgr = WiFiManager()

        # Check if already connected
        if not wifi_mgr.is_connected():
            if verbose:
                print("NTP: Connecting to WiFi...")
            if not wifi_mgr.connect():
                if verbose:
                    print("NTP: WiFi connection failed")
                return None
        else:
            if verbose:
                print(f"NTP: Already connected, IP: {wifi_mgr.get_ip()}")

        pool = wifi_mgr.socket_pool()
        if pool is None:
            if verbose:
                print("NTP: No socket pool available")
            return None

    except Exception as e:
        if verbose:
            print(f"NTP: WiFi setup failed: {e}")
        return None

    # Try to use adafruit_ntp library
    try:
        import adafruit_ntp

        if verbose:
            print(f"NTP: Using adafruit_ntp library")
            if ntp_host:
                print(f"NTP: Server: {ntp_host}")

        # Create NTP client - don't pass server parameter if it's None
        if ntp_host:
            ntp = adafruit_ntp.NTP(pool, server=ntp_host, tz_offset=0, socket_timeout=timeout)
        else:
            # Use default server (pool.ntp.org)
            ntp = adafruit_ntp.NTP(pool, tz_offset=0, socket_timeout=timeout)

        # Get the datetime
        if verbose:
            print("NTP: Querying time server...")

        ntp_datetime = ntp.datetime

        if verbose:
            print(f"NTP: Got time: {ntp_datetime.tm_year}-{ntp_datetime.tm_mon:02d}-{ntp_datetime.tm_mday:02d} "
                  f"{ntp_datetime.tm_hour:02d}:{ntp_datetime.tm_min:02d}:{ntp_datetime.tm_sec:02d}")

        # Convert to Unix timestamp
        unix_time = time.mktime(ntp_datetime)

        return int(unix_time)

    except ImportError:
        if verbose:
            print("NTP: adafruit_ntp library not found!")
            print("NTP: Please install it from: https://github.com/adafruit/Adafruit_CircuitPython_NTP")
        return None
    except OSError as e:
        if verbose:
            print(f"NTP: Socket error: {e}")
            import sys
            sys.print_exception(e)
        return None
    except Exception as e:
        if verbose:
            print(f"NTP: Query failed: {e}")
            import sys
            sys.print_exception(e)
        return None


def set_system_time(ntp_host=None, verbose=True):
    """Get NTP time and set system RTC.

    Args:
        ntp_host: NTP server hostname (optional)
        verbose: Print debug messages

    Returns True on success, False on failure.
    """
    timestamp = get_ntp_time(ntp_host, verbose=verbose)
    if timestamp is None:
        return False

    try:
        import rtc
        tm = time.localtime(timestamp)
        rtc.RTC().datetime = tm
        if verbose:
            print(f"System time set to: {tm.tm_year}-{tm.tm_mon:02d}-{tm.tm_mday:02d} "
                  f"{tm.tm_hour:02d}:{tm.tm_min:02d}:{tm.tm_sec:02d}")
        return True
    except Exception as e:
        if verbose:
            print(f"Failed to set system time: {e}")
        return False

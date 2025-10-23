"""RTC wrapper for BadOS that prefers the onboard PCF85063A if present.

The board's PCF85063A RTC (if present/frozen) will be used; otherwise the
built-in `rtc.RTC` will be used as a fallback. The wrapper provides simple
get/set operations and returns time.struct_time values.

Supports RTC alarms for low-power wake operations.
"""

try:
    import time
    import rtc as _rtc
except Exception:
    time = None
    _rtc = None

# Try vendor RTC driver names
try:
    import pcf85063a as _pcf_driver
except Exception:
    try:
        import adafruit_pcf85063a as _pcf_driver
    except Exception:
        _pcf_driver = None

try:
    import busio
    import board
except Exception:
    busio = None
    board = None


class BadOS_RTC:
    def __init__(self, i2c=None):
        self._rtc = None
        self._driver = None
        self._i2c = i2c

        # Import logger if available
        try:
            from bados.logger import get_logger
            logger = get_logger()
        except:
            logger = None

        if logger:
            logger.debug("BadOS_RTC.__init__() called")

        # Preference: use hardware PCF85063A if available
        if _pcf_driver and (i2c or (busio and board)):
            if logger:
                logger.debug("Attempting PCF85063A initialization")
            try:
                if i2c is None:
                    # Create I2C bus - use board defaults
                    try:
                        if logger:
                            logger.debug("Creating I2C bus")
                        i2c = busio.I2C(board.SCL, board.SDA)
                        # Wait for I2C to be ready
                        while not i2c.try_lock():
                            pass
                        i2c.unlock()
                        if logger:
                            logger.debug("I2C bus created and ready")
                    except Exception as e:
                        msg = f"RTC: Failed to create I2C bus: {e}"
                        print(msg)
                        if logger:
                            logger.error(msg)
                        i2c = None

                if i2c:
                    try:
                        if logger:
                            logger.debug("Creating PCF85063A driver instance")
                        self._driver = _pcf_driver.PCF85063A(i2c)
                        self._i2c = i2c
                        msg = "RTC: PCF85063A driver initialized"
                        print(msg)
                        if logger:
                            logger.info(msg)
                    except Exception as e:
                        msg = f"RTC: Failed to initialize PCF85063A: {e}"
                        print(msg)
                        if logger:
                            logger.error(msg)
                            import traceback
                            import io
                            s = io.StringIO()
                            traceback.print_exception(e, s)
                            logger.error(s.getvalue())
                        self._driver = None
            except Exception as e:
                msg = f"RTC: Hardware init error: {e}"
                print(msg)
                if logger:
                    logger.error(msg)
                self._driver = None
        else:
            if logger:
                logger.warning("PCF85063A driver not available")
                logger.debug(f"_pcf_driver={_pcf_driver}, i2c={i2c}, busio={busio}, board={board}")

        # Fallback to system RTC
        if self._driver is None and _rtc:
            if logger:
                logger.debug("Falling back to system RTC")
            try:
                self._rtc = _rtc.RTC()
                msg = "RTC: Using system RTC"
                print(msg)
                if logger:
                    logger.info(msg)
            except Exception as e:
                msg = f"RTC: System RTC init failed: {e}"
                print(msg)
                if logger:
                    logger.error(msg)
                self._rtc = None

        # Final check
        if self._driver is None and self._rtc is None:
            msg = "RTC: WARNING - No RTC available!"
            print(msg)
            if logger:
                logger.error(msg)
        elif logger:
            if self._driver:
                logger.info("RTC initialization complete - using PCF85063A")
            elif self._rtc:
                logger.info("RTC initialization complete - using system RTC")

    def now(self):
        """Return current time as time.struct_time or None if unavailable."""
        if self._driver:
            try:
                t = self._driver.datetime
                return time.struct_time(t)
            except Exception:
                pass
        if self._rtc:
            try:
                return self._rtc.datetime
            except Exception:
                pass
        return None

    def set_datetime(self, tm):
        """Set RTC. tm is a time.struct_time or tuple.

        Returns True on success, False on failure.
        """
        if self._driver:
            try:
                # PCF85063A expects time.struct_time directly, not tuple
                if not isinstance(tm, time.struct_time):
                    tm = time.struct_time(tm)
                self._driver.datetime = tm
                return True
            except Exception as e:
                print(f"Hardware RTC set error: {e}")
                import sys
                if hasattr(sys, 'print_exception'):
                    sys.print_exception(e)
                return False
        if self._rtc:
            try:
                self._rtc.datetime = tm
                return True
            except Exception as e:
                print(f"System RTC set error: {e}")
                return False
        return False

    def set_alarm(self, seconds_from_now=None, alarm_time=None):
        """Set an alarm to trigger after seconds_from_now or at specific alarm_time.

        Args:
            seconds_from_now: Seconds from current time to set alarm
            alarm_time: time.struct_time for specific alarm time

        Returns True on success, False if not supported or failed.

        Note: PCF85063A alarm format: (time.struct_time, frequency_string)
        Frequency strings: "daily", "hourly", "minute", "second"
        """
        # Import logger if available
        try:
            from bados.logger import get_logger
            logger = get_logger()
        except:
            logger = None

        if logger:
            logger.debug(f"set_alarm called: seconds_from_now={seconds_from_now}, alarm_time={alarm_time}")

        if not self._driver:
            if logger:
                logger.error("No RTC driver available")
            print("RTC set_alarm: No driver")
            return False

        if not hasattr(self._driver, 'alarm'):
            if logger:
                logger.error("RTC driver does not have 'alarm' attribute")
            print("RTC set_alarm: Driver has no alarm attribute")
            return False

        try:
            # Prefer the RTC's timerA countdown for relative (seconds_from_now)
            # since it offers a true one-shot relative wake using timerA_* props.
            if seconds_from_now is not None:
                if logger:
                    logger.debug("Attempting timerA configuration")

                # If the driver exposes timerA controls, try to use them.
                if (hasattr(self._driver, 'timerA_enabled') and
                    hasattr(self._driver, 'timerA_value') and
                    hasattr(self._driver, 'timerA_frequency')):

                    if logger:
                        logger.debug("Driver has timerA attributes")

                    # Use 1Hz ticks where possible (value range 0-255)
                    try:
                        sec = int(seconds_from_now)
                    except Exception as e:
                        if logger:
                            logger.error(f"Failed to convert seconds_from_now to int: {e}")
                        sec = None

                    if sec is not None and sec > 0:
                        # If within 1-255 seconds, use 1Hz ticks.
                        if sec <= 255:
                            try:
                                if logger:
                                    logger.debug(f"Setting timerA for {sec}s at 1Hz")

                                self._driver.timerA_frequency = _pcf_driver.PCF85063A.TIMER_FREQ_1HZ
                                if logger:
                                    logger.debug("Set timerA_frequency")

                                self._driver.timerA_value = sec
                                if logger:
                                    logger.debug(f"Set timerA_value to {sec}")

                                # Configure interrupt behavior: non-pulsed by default
                                if hasattr(self._driver, 'timerA_pulsed'):
                                    try:
                                        self._driver.timerA_pulsed = False
                                        if logger:
                                            logger.debug("Set timerA_pulsed to False")
                                    except Exception as e:
                                        if logger:
                                            logger.warning(f"Failed to set timerA_pulsed: {e}")

                                if hasattr(self._driver, 'timerA_interrupt'):
                                    try:
                                        self._driver.timerA_interrupt = True
                                        if logger:
                                            logger.debug("Set timerA_interrupt to True")
                                    except Exception as e:
                                        if logger:
                                            logger.warning(f"Failed to set timerA_interrupt: {e}")

                                self._driver.timerA_enabled = True
                                if logger:
                                    logger.info(f"Successfully set timerA alarm for {sec}s")

                                return True
                            except Exception as e:
                                if logger:
                                    logger.error(f"timerA configuration failed: {e}")
                                print(f"RTC timerA error: {e}")
                                # Fall through to absolute alarm fallback
                                pass

                        # If the requested time is an exact multiple of 60 and fits 0-255 ticks
                        # when using 1/60Hz mode, use that (1 tick = 60 seconds)
                        if sec % 60 == 0 and (sec // 60) <= 255:
                            try:
                                if logger:
                                    logger.debug(f"Setting timerA for {sec}s at 1/60Hz")

                                self._driver.timerA_frequency = _pcf_driver.PCF85063A.TIMER_FREQ_1_60HZ
                                self._driver.timerA_value = int(sec // 60)
                                if hasattr(self._driver, 'timerA_pulsed'):
                                    try:
                                        self._driver.timerA_pulsed = False
                                    except Exception:
                                        pass
                                if hasattr(self._driver, 'timerA_interrupt'):
                                    try:
                                        self._driver.timerA_interrupt = True
                                    except Exception:
                                        pass
                                self._driver.timerA_enabled = True
                                if logger:
                                    logger.info(f"Successfully set timerA alarm at 1/60Hz")
                                return True
                            except Exception as e:
                                if logger:
                                    logger.error(f"timerA 1/60Hz configuration failed: {e}")
                                pass

                    # If timerA could not be used for the requested interval, fall back
                    # to absolute alarm method below.
                    if logger:
                        logger.debug("Falling back to absolute alarm method")

                # Fallback: set an absolute alarm using epoch math (existing behavior)
                now = self.now()
                if not now:
                    if logger:
                        logger.error("Could not get current time from RTC")
                    print("RTC set_alarm: Could not get current time")
                    return False

                try:
                    now_epoch = time.mktime(now)
                except Exception:
                    now_epoch = time.mktime(time.struct_time((
                        now.tm_year, now.tm_mon, now.tm_mday,
                        now.tm_hour, now.tm_min, now.tm_sec,
                        now.tm_wday if hasattr(now, 'tm_wday') else 0,
                        -1, -1)))

                target_epoch = int(now_epoch) + int(seconds_from_now)
                alarm_tm = time.localtime(target_epoch)

                if not isinstance(alarm_tm, time.struct_time):
                    alarm_tm = time.struct_time(alarm_tm)

                if logger:
                    logger.debug(f"Setting absolute alarm for {alarm_tm}")

                # Use "daily" match (driver matches day/hour/min/sec) as a one-shot
                # absolute target; caller should clear alarm if repeating behavior is
                # undesired after wake.
                self._driver.alarm = (alarm_tm, "daily")

                if hasattr(self._driver, 'alarm_interrupt'):
                    try:
                        self._driver.alarm_interrupt = True
                    except Exception:
                        pass

                if logger:
                    logger.info("Successfully set absolute alarm")
                return True

            elif alarm_time is not None:
                # Accept tuples or struct_time
                if not isinstance(alarm_time, time.struct_time):
                    alarm_time = time.struct_time(alarm_time)

                self._driver.alarm = (alarm_time, "daily")

                if hasattr(self._driver, 'alarm_interrupt'):
                    try:
                        self._driver.alarm_interrupt = True
                    except Exception:
                        pass

                if logger:
                    logger.info("Successfully set specific time alarm")
                return True

        except Exception as e:
            msg = f"RTC alarm error: {e}"
            print(msg)
            if logger:
                logger.error(msg)
                import traceback
                import io
                s = io.StringIO()
                traceback.print_exception(e, s)
                logger.error(s.getvalue())
            return False

        if logger:
            logger.error("set_alarm: fell through without setting alarm")
        return False

    def clear_alarm(self):
        """Clear any set alarm.

        Returns True on success, False if not supported.
        """
        if self._driver and hasattr(self._driver, 'alarm'):
            try:
                self._driver.alarm = None
                return True
            except Exception:
                return False
        return False

    def alarm_status(self):
        """Check if alarm has triggered.

        Returns True if alarm triggered, False otherwise or if not supported.
        """
        if self._driver and hasattr(self._driver, 'alarm_status'):
            try:
                return self._driver.alarm_status
            except Exception:
                return False
        return False

    def sync_from_ntp(self, ntp_time_func=None, verbose=True):
        """Sync RTC from NTP time.

        Args:
            ntp_time_func: Function that returns unix epoch time (optional)
            verbose: Print debug messages

        Returns True on success, False on failure.
        """
        if ntp_time_func is None:
            # Try to import and use bados.ntp
            try:
                from bados.ntp import get_ntp_time
                ntp_time_func = lambda: get_ntp_time(verbose=verbose)
            except Exception as e:
                if verbose:
                    print(f"RTC: Failed to import NTP module: {e}")
                return False

        try:
            if verbose:
                print("RTC: Getting NTP time...")
            epoch = ntp_time_func()
            if epoch:
                if verbose:
                    print(f"RTC: Got epoch time: {epoch}")
                tm = time.localtime(epoch)
                if verbose:
                    print(f"RTC: Setting RTC to: {tm.tm_year}-{tm.tm_mon:02d}-{tm.tm_mday:02d} "
                          f"{tm.tm_hour:02d}:{tm.tm_min:02d}:{tm.tm_sec:02d}")
                success = self.set_datetime(tm)
                if verbose:
                    print(f"RTC: Set datetime result: {success}")
                return success
            else:
                if verbose:
                    print("RTC: NTP returned no time")
                return False
        except Exception as e:
            if verbose:
                print(f"RTC: NTP sync error: {e}")
            return False
        return False

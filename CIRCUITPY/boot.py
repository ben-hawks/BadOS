"""Boot helper for BadOS: attempt to mount SD early using known pins.

This runs very early on CircuitPython boot and attempts a safe, non-blocking
mount of the SD card using `sd_mount_with_pins_cs.mount_sd`. It uses the
explicit pins you provided: SD_CS = board.GP1 and SD_CD = board.GP0.

The file is intentionally small and tolerant of missing modules so it won't
crash the boot sequence if files aren't present.
"""

# Check wake reason early using frozen wakeup module
try:
    import wakeup
    wake_reason = wakeup.wakeup_reason()
    print(f"boot.py: Wake reason: {wake_reason}")

    # If the frozen wakeup capture indicates the RTC alarm triggered,
    # try to clear the hardware alarm flag immediately so it doesn't
    # persist across subsequent boots. This is best-effort and must not
    # raise or block boot.
    try:
        if hasattr(wakeup, 'rtc_alarm_triggered') and wakeup.rtc_alarm_triggered():
            print("boot.py: RTC alarm detected at boot; attempting to clear RTC alarm flag")
            try:
                # Attempt to create an I2C bus and contact the PCF85063A driver
                import busio
                import board as _board
                try:
                    i2c = busio.I2C(_board.SCL, _board.SDA)
                    # Try to import known PCF drivers (frozen or adafruit lib)
                    _pcf = None
                    try:
                        import pcf85063a as _pcf
                    except Exception:
                        try:
                            import adafruit_pcf85063a as _pcf
                        except Exception:
                            _pcf = None

                    if _pcf is not None:
                        try:
                            drv = _pcf.PCF85063A(i2c)
                            # Try to clear the alarm status flag; try several fallbacks
                            try:
                                drv.alarm_status = False
                            except Exception:
                                try:
                                    drv.alarm = None
                                except Exception:
                                    pass
                            print("boot.py: RTC alarm flag cleared (pcf85063a)")
                        except Exception as e:
                            print(f"boot.py: Error initializing PCF85063A to clear alarm: {e}")
                    else:
                        print("boot.py: PCF85063A driver not available to clear alarm")
                except Exception as e_i2c:
                    print(f"boot.py: Could not create I2C to talk to RTC: {e_i2c}")
            except Exception as e_rtc_clear:
                print(f"boot.py: RTC clear helper failed: {e_rtc_clear}")
    except Exception as e:
        print(f"boot.py: wakeup.rtc check failed: {e}")

except Exception as e:
    print(f"boot.py: Could not check wakeup module: {e}")

try:
    import storage
    import time
    import board
    import bados.configuration as _conf
    try:
        mounted = False
        try:
            mounted = _conf.mount_sd()
        except Exception as e:
            print("boot.py: bados.configuration.mount_sd raised:", e)
        print("boot.py: sd mount result:", mounted)
    except Exception as e:
        print("boot.py: bados.configuration usage error:", e)
except Exception as e:
    # Very defensive: never let boot.py raise
    try:
        print('boot.py: unexpected error during startup SD mount attempt:', e)
    except Exception:
        pass

# Make filesystem writable for state persistence
# CircuitPython defaults to read-only when USB is connected
# We need to explicitly make it writable for battery operation
try:
    import storage
    import supervisor

    # Decide whether we should make the filesystem writable.
    # If SW_UP is pressed at boot (developer intent), keep filesystem READ-ONLY.
    make_writable = True
    try:
        import wakeup as _wakeup
        if hasattr(_wakeup, 'button_up') and _wakeup.button_up():
            make_writable = False
            print("boot.py: SW_UP pressed at boot - keeping filesystem READ-ONLY for development")
        else:
            print("boot.py: SW_UP not pressed - will attempt to make filesystem writable")
    except Exception:
        # If wakeup isn't available, default to writable (as before)
        print("boot.py: wakeup.button_up not available - defaulting to writable")
        make_writable = True

    if make_writable:
        try:
            print("boot.py: Attempting to remount filesystem writable (best-effort)")
            storage.remount('/', readonly=False)
            # Verify it worked
            try:
                with open('/.boot_test', 'w') as f:
                    f.write('writable')
                import os
                os.remove('/.boot_test')
                print('boot.py: ✓ Filesystem is now WRITABLE')
            except Exception as e:
                print(f'boot.py: ✗ Write test failed after remount: {e}')
        except Exception as e_rem:
            # If remount fails (e.g., host is holding the drive), keep readonly
            try:
                print(f'boot.py: Remount attempt failed (drive likely mounted by host): {e_rem}')
            except Exception:
                pass
    else:
        print('boot.py: Developer override - keeping filesystem READ-ONLY')

except Exception as e:
    print(f"boot.py: Filesystem setup error: {e}")
    # Try best-effort fallback to force writable; ignore errors
    try:
        import storage
        storage.remount('/', readonly=False)
        print("boot.py: Forced filesystem writable as fallback")
    except Exception:
        print("boot.py: Could not make filesystem writable")

'''
    BadOS RTC Manager (For Badger2040W/PCF85063A RTC)
    By Ben Hawks, July 2023
    Inspired by the Pimoroni's Badger2040W Badge, AdaFruit, and BeBox
'''

import gc, os, sys, math, time, alarm, rtc
import board, microcontroller, storage, supervisor
import analogio, digitalio, busio, displayio , terminalio , vectorio, usb_hid
from digitalio import DigitalInOut, Direction, Pull

try:  # try importing RTC - will fail if on Badger2040
    import pcf85063a
except ImportError:
    pass

if 'pcf85063a' in sys.modules:
    class BadOS_RTC():
        days = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
        def __init__(self, i2c, enable_timer_interupt=False, RTC_alarm=0):
            self.i2c = i2c
            self.badger_pcf = pcf85063a.PCF85063A(i2c)
            self.rtc = rtc.RTC()
            self.enable_timer_interupt = enable_timer_interupt
            self.rtc_alarm = RTC_alarm

            #set RTC when starting up from no power
            if self.badger_pcf.lost_power:
                default_t = time.struct_time((2023, 8, 10, 5, 00, 0, 0, -1, -1)) #DC31 :)
                self.set_rtc_time(default_t)

            # do fancy wifi ntp sync here

            # create an array containing all of our alarm objects. Buttons (A,B,C,Up,Down) and RTC_Alarm (GPIO8)
            self.alarms = None

        def get_alarms(self, buttons):
            if self.alarms is []:
                # Add the RTC_Alarm pin alarm (is this needed actually? maybe? probably?)
                self.alarms.append(alarm.pin.PinAlarm(board.RTC_ALARM, value=True, pull=False)) #Setup RTC Alarm pin
                for button in buttons:
                    self.alarms.append(alarm.pin.PinAlarm(button, value=True, pull=False))

        def set_rtc_time(self, time):
            #accepts a time.struct_time object:
            # yearday is not supported, isdst can be set but we don't do anything with it at this time
            #                      year, mon, date, hour, min, sec, wday, yday, isdst
            # t = time.struct_time((2017, 10, 29, 10, 31, 0, 0, -1, -1))
            self.rtc.datetime = time

        def get_rtc_time(self):
            return self.rtc.datetime

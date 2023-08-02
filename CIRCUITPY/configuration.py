# ----------------------------------------------------------------------------
# configuration.py: runtime configuration settings template
# for Pimoroni's Badger2040W.
#
# Adapt to your needs (credentials, active-time, hardware, ui) and rename to
# configuration.py
#
# Author: Bernhard Bablok, Ben Hawks
# License: GPL3
#
# Original Source: https://github.com/bablokb/circuitpython-clock
# Current Repo: https://github.com/ben-hawks/BadOS
# ----------------------------------------------------------------------------

import board
import time
import pcf85063a

# Enable or disable the SD Card, will not try to mount on startup if disabled
# --- IMPORTANT NOTE! Failing to init the SD Card while inserted could result in issues, possibly SD card data loss. ---
# --- Only disable if you KNOW you are not and will not be using an SD card! ---
use_SD_card = False

# Enable or disable SAOs in Circuitpython (the ports will always be powered, disabling simply doesn't create the objects
use_SAO = True


# --- Basic settings container
class Settings:
  pass

# --- specific containers ---

settings = Settings()
secrets  = Settings()
pins     = Settings()
ui       = Settings()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ CONFIGURE THE VALUES BELOW! ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# --- WLAN credentials ---

secrets.ssid      = 'your_ssid'
secrets.password  = 'your_password'
secrets.retry     = 1
secrets.debugflag = False
secrets.channel   = 6        # optional
secrets.timeout   = 10       # optional

# --- update via time-api ---

settings.TIMEAPI_URL      = "http://worldtimeapi.org/api/ip"

# --- hardware-setup ---

i2c = board.I2C()
settings.display = board.DISPLAY        # use builtin display
settings.deep_sleep = True                      # use deep-sleep

settings.rtc_ext = lambda: pcf85063a.PCF85063A(i2c)
settings.rtc_ext_wakeup = 1                     # active low|high rtc-wakup

settings.wifi_module = "wifi_impl_builtin"      # implementing module

# power_off command for Badger2040W
def power_off():
  time.sleep(3)
  board.ENABLE_DIO.value = 0

settings.power_off = power_off

#max battery voltages in.. centiamps (300 = 3.0V, 270 = 2.7V, etc.)
#set for AAA's
settings.max_battery = 300
settings.min_battery = 270


# setup a path object to hold locations of apps, assets, etc.
settings.path = {}

#unified
if use_SD_card:
    settings.path.update({"apps":   ['/apps/','/sd/apps/']})
    settings.path.update({"ducky":  ['/ducky/', '/sd/ducky/']})
    settings.path.update({"icons":  ['/assets/icons/', '/sd/assets/icons/']})
    settings.path.update({"images": ['/assets/images/', '/sd/assets/images/']})
    settings.path.update({"fonts":  ['/assets/fonts/', '/sd/assets/fonts/']})
else:
    settings.path.update({"apps":   ['/apps/']})
    settings.path.update({"ducky":  ['/ducky/']})
    settings.path.update({"icons":  ['/assets/icons/']})
    settings.path.update({"images": ['/assets/images/']})
    settings.path.update({"fonts":  ['/assets/fonts/']})
# --- pins ---

pins.PIN_ALARM = board.SW_A                     # wakeup pin
pins.RTC_ALARM = board.RTC_ALARM                # rtc wakup pin

pins.button_pins = [("a", board.SW_A), ("b", board.SW_B), ("c", board.SW_C),
                                ("up", board.SW_UP), ("down", board.SW_DOWN)]


if use_SD_card:
  pins.SD_CS = board.GP1
  pins.SD_CD = board.GP0

# --- UI ---
ui.white = 0xFFFFFF
ui.black = 0x000000
ui.bg_color  = ui.white                         # white
ui.fg_color  = ui.black                         # black
ui.date_fmt  = "{0:02d}.{1:02d}.{2:02d}"        # dd.mm.yy
ui.button_pos = (42, 145, 251)
import os

import board
import alarm
from analogio import AnalogIn
from configuration import settings, ui, pins
import sdcardio
import displayio
import storage
from sao_lib import SAO_port

class HWConfig:
  def __init__(self):
    """ constructor """
    #Try to setup and mount SD Card
    self.sd_mount_loc = '/sd'
    self.sd_insert()
    self.format_populate_sd()

    self.display = settings.display
    self.init_display()

    self.i2c = board.I2C()

    # --- SAOs ---
    if settings.use_SAO:
      # SD card steals the GPIO pins on SAO_1 for SPI CS & SD Card Detect, must solder jumpers to actually use GPIO1/2 here!
      if settings.use_SD_card:
        self.SAO_1 = SAO_port(self.i2c)
      else:
        self.SAO_1 = SAO_port(self.i2c, board.GP0, board.GP1)

      self.SAO_2 = SAO_port(self.i2c, board.GP2, board.GP3)
      self.SAO_3 = SAO_port(self.i2c, board.GP6, board.GP7)
      self.SAO_4 = SAO_port(self.i2c, board.GP27, board.GP28)
    else:
      sao = None

  def bat_level(self):
    """ return battery level """
    adc = AnalogIn(board.VOLTAGE_MONITOR)
    level = adc.value *  3 * 3.3 / 65535
    adc.deinit()
    return level

  def pin_alarm(self):
    """ return pre-configured pin-alarm """
    return alarm.pin.PinAlarm(pins.PIN_ALARM,value=True,edge=True,pull=True)

  def init_sd(self, mnt_loc="/sd"):
    try:
      SD_CS = pins.SD_CS
      # Connect to the card and mount the filesystem.
      spi = board.SPI()
      sdcard = sdcardio.SDCard(spi, SD_CS)
      vfs = storage.VfsFat(sdcard)
      storage.mount(vfs, mnt_loc)
      return True
    except Exception as e:
      print("No SD Card Found or Failed to mount!")
      print(e)
      return False

  def format_populate_sd(self):
    if self.sd_mounted:
      try:
        base_assets = self.sd_mount_loc + "/" + settings.asset_base_path
        os.mkdir(base_assets)
      except:
        print("assets dir exists, no need to create")
      for path_val in settings.path.items():
        sd_path_loc = path_val[1][1] #create paths for only SD card, default paths should always exist...
        try:
          #print(sd_path_loc)
          os.mkdir(sd_path_loc)
        except OSError as e:
          #print("File Exists! no need to create")
          pass



  def update_path_for_sd(self, use_SD):
    if use_SD:
      settings.path.update({"apps": ['/apps/', '/sd/apps/']})
      settings.path.update({"badges": ['/apps/badge/', '/sd/badges/']})
      settings.path.update({"ducky": ['/ducky/', '/sd/ducky/']})
      settings.path.update({"icons": ['/assets/icons/', '/sd/assets/icons/']})
      settings.path.update({"images": ['/assets/images/', '/sd/assets/images/']})
      settings.path.update({"fonts": ['/assets/fonts/', '/sd/assets/fonts/']})
      print("Setting path to include SD card")
    else:
      settings.path.update({"apps": ['/apps/']})
      settings.path.update({"badges": ['/apps/badge/']})
      settings.path.update({"ducky": ['/ducky/']})
      settings.path.update({"icons": ['/assets/icons/']})
      settings.path.update({"images": ['/assets/images/']})
      settings.path.update({"fonts": ['/assets/fonts/']})
      print("Setting path to only include RPi Flash")

  def sd_insert(self):
    mnt_success = False
    if settings.use_SD_card:
      mnt_success = self.init_sd(self.sd_mount_loc)
      self.update_path_for_sd(mnt_success)  # If SD Mount unsuccessful, set path to default, otherwise include sd
    self.sd_mounted = mnt_success

  def init_display(self):
    #self.display.rotation = 270
    self.palette = displayio.Palette(1)
    self.palette[0] = ui.white
    self.palette_inverted = displayio.Palette(1)
    self.palette_inverted[0] = ui.black
    self.width = self.display.width
    self.height = self.display.height

config = HWConfig()
import board
import alarm
from analogio import AnalogIn
import configuration as c
import sdcardio
import displayio
import storage
from sao_lib import SAO_port

class HWConfig:
  def __init__(self):
    """ constructor """
    #Try to setup and mount SD Card
    self.sd_mounted = False
    self.sd_insert()

    self.display = c.settings.display
    self.init_display()

    self.i2c = board.I2C()

    # --- SAOs ---
    if c.use_SAO:
      # SD card steals the GPIO pins on SAO_1 for SPI CS & SD Card Detect, must solder jumpers to actually use GPIO1/2 here!
      if c.use_SD_card:
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
    return alarm.pin.PinAlarm(c.pins.PIN_ALARM,value=True,edge=True,pull=True)

  def init_sd(self, mnt_loc="/sd"):
    try:
      SD_CS = c.pins.SD_CS
      # Connect to the card and mount the filesystem.
      spi = board.SPI()
      sdcard = sdcardio.SDCard(spi, SD_CS)
      vfs = storage.VfsFat(sdcard)
      try: #Try unmounting and remounting sd card for when we come out of sleep. If we can't unmount, try mounting alone
        storage.umount(vfs)
        storage.mount(vfs, mnt_loc)
        print("Remounted SD Card on init! Probably coming out of sleep?")
      except Exception as e:
        storage.mount(vfs, mnt_loc)
        print("Freshly Mounted SD Card on init!")
      return True
    except Exception as e:
      print("No SD Card Found or Failed to mount!")
      print(e)
      return False

  def update_path_for_sd(self, use_SD):
    if use_SD:
      c.settings.path.update({"apps": ['/apps/', '/sd/apps/']})
      c.settings.path.update({"ducky": ['/ducky/', '/sd/ducky/']})
      c.settings.path.update({"icons": ['/assets/icons/', '/sd/assets/icons/']})
      c.settings.path.update({"images": ['/assets/images/', '/sd/assets/images/']})
      c.settings.path.update({"fonts": ['/assets/fonts/', '/sd/assets/fonts/']})
    else:
      c.settings.path.update({"apps": ['/apps/']})
      c.settings.path.update({"ducky": ['/ducky/']})
      c.settings.path.update({"icons": ['/assets/icons/']})
      c.settings.path.update({"images": ['/assets/images/']})
      c.settings.path.update({"fonts": ['/assets/fonts/']})

  def sd_insert(self):
    mnt_success = False
    if c.use_SD_card:
      mnt_success = self.init_sd()
      self.update_path_for_sd(mnt_success)  # If SD Mount unsuccessful, set path to default, otherwise include sd
    self.sd_mounted = mnt_success

  def init_display(self):
    #self.display.rotation = 270
    self.palette = displayio.Palette(1)
    self.palette[0] = c.ui.white
    self.palette_inverted = displayio.Palette(1)
    self.palette_inverted[0] = c.ui.black

config = HWConfig()
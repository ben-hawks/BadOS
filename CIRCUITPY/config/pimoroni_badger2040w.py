import board
import alarm
from analogio import AnalogIn
import configuration as c
import sdcardio
import storage
from sao_lib import SAO_port

class HWConfig:
  def __init__(self):
    """ constructor """
    if c.use_SD_card:
      self.init_sd()
    pass

    # --- SAOs ---
    if c.use_SAO:
      # SD card steals the GPIO pins on SAO_1 for SPI CS & SD Card Detect, must solder jumpers to actually use GPIO1/2 here!
      if c.use_SD_card:
        self.SAO_1 = SAO_port(board.i2c)
      else:
        self.SAO_1 = SAO_port(board.i2c, board.GP0, board.GP1)

      self.SAO_2 = SAO_port(board.i2c, board.GP2, board.GP3)
      self.SAO_3 = SAO_port(board.i2c, board.GP6, board.GP7)
      self.SAO_4 = SAO_port(board.i2c, board.GP27, board.GP28)
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
      storage.mount(vfs, mnt_loc)
      return True
    except Exception as e:
      print("No SD Card Found or Failed to mount!")
      print(e)
      return False

config = HWConfig()
# ----------------------------------------------------------------------------
# sao_lib.py: simple circuitpython wrapper for SAO ports on a badge
#
#
# Author: Ben Hawks
# License: GPL3
#
# Repo: https://github.com/ben-hawks/BadOS
# ----------------------------------------------------------------------------

from adafruit_bus_device.i2c_device import I2CDevice

class SAO_port():
  def __init__(self, i2c, gpio1=None, gpio2=None):
    self.i2c_bus = i2c
    self.gpio1 = gpio1
    self.gpio2 = gpio2
    self.i2c = None
    self.gpio = None

  def set_i2c_device(self, address):
    self.i2c = I2CDevice(self.i2c_bus, address)

  def set_gpio_device(self, gpio_device):
    # allows for easy saving/setting up of various uses for SAO GPIOs
    # assume if GPIO's aren't set, they aren't supported (either old SAO version, or other HW reasons)
    if self.gpio1 is not None and self.gpio2 is not None:
      self.gpio = gpio_device
    else:
      raise ConnectionError("No GPIO pins connected to this SAO port!") # I mean, the GPIOs aren't connected...
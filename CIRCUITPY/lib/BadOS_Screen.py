'''
    BadOS Screen
    Common Screen Functions for BadOS
    David Guidos, May 2022
'''

__version__ = "1.0.0"
__repo__ = "https://github.com/guidoslabs/BadOS.git"

import gc, os, sys, math, time, builtins
import board, microcontroller, storage, supervisor
import analogio, digitalio, busio, displayio , terminalio , vectorio, usb_hid
from digitalio import DigitalInOut, Direction, Pull
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from adafruit_display_shapes.circle import Circle
from adafruit_display_shapes.line import Line
from adafruit_display_shapes.polygon import Polygon
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_display_shapes.triangle import Triangle
from adafruit_hid.keyboard import Keyboard
import adafruit_miniqr
import adafruit_imageload


config_file = "/config/" + board.board_id.replace(".", "_")
hw_impl = builtins.__import__(config_file, None, None, ["config"], 0)

from configuration import settings, ui, pins

class Screen:

    def __init__(self, background_color = ui.white, with_status_bar = True):

        self.fonts = []
        self.get_fonts()
        
        self.width = settings.hw.display.width
        self.height = settings.hw.display.height
        self.background_color = background_color
        self.background_palette = settings.hw.palette_inverted if background_color == ui.black else settings.hw.palette
        self.status_bar = Status_Bar(settings.hw.display)
        self.value = self.create_screen()
        self._status_bar_visible = with_status_bar
        if not with_status_bar:
            self.value.pop()

    @property
    def status_bar_visible(self):
        return self._status_bar_visible

    @status_bar_visible.setter
    def status_bar_visible(self, value):
        if value != self._status_bar_visible:
            # visibility changing
            if value:
                # becoming visible 
                # insert into screen at index position 1
                self.value.insert(1, self.status_bar.value)
            else:
                # becoming invisible
                # remove from screen
                self.value.pop(1)
        self._status_bar_visible = value

    # create and layout display screen
    def create_screen(self):
        screen = displayio.Group()
        background = vectorio.Rectangle(pixel_shader=self.background_palette, width=self.width + 1, height=self.height, x=0, y=0)
        screen.append(background)
        screen.append(self.status_bar.value)
        return screen

    # render the screen
    def render(self):
        # refresh the status bar; always at index 1 (background is at 0)
        if self.status_bar_visible:
            self.value[1] = self.status_bar.value
        # update the display
        self.display.show(self.value)
        while self.display.busy==True:
            time.sleep(0.01)     
        self.display.refresh()

    # clear screen
    # remove all screen objects, except the background and status bar (if visible)
    def clear(self):
        while len(self.value) > (2 if self.status_bar_visible else 1):
            self.value.pop()

    @staticmethod
    # create thumbnail of bitmap image
    def thumbnail(bitmap_image, bitmap_palette, thumbnail_width = -1, thumbnail_height = 64):
        # determine size of thumbnail bitmap
        if thumbnail_height == -1:
            thumbnail_height = int(bitmap_image.height * thumbnail_width / bitmap_image.width)
        elif thumbnail_width == -1:
            thumbnail_width = int(bitmap_image.width * thumbnail_height / bitmap_image.height)
        # create the result bitmap
        thumbnail_image = displayio.Bitmap(thumbnail_width, thumbnail_height, 2)
        thumbnail_palette = displayio.Palette
        hf = thumbnail_height / bitmap_image.height # height conversion factor
        wf = thumbnail_width / bitmap_image.width   # height conversion factor
        for x in range(thumbnail_width):
            xi = int(x / wf)
            for y in range(thumbnail_height):
                yi = int(y / hf)
                thumbnail_image[x, y] = bitmap_image[xi, yi]
        return thumbnail_image, bitmap_palette

    def get_fonts(self):
        # get fonts
        self.fonts.append(bitmap_font.load_font(settings.path["fonts"][0] + 'Arial-12.bdf'))
        self.fonts.append(bitmap_font.load_font(settings.path["fonts"][0] + 'Earth 2073-18.bdf'))
        self.fonts.append(terminalio.FONT)

        if settings.hw.sd_mounted:
            sd_fonts = [font for font in sorted(os.listdir(settings.path["fonts"][1])) if font[0:1] != "."]

class Status_Bar:
    
    def __init__(self, display):
        self.display = display
        self.settings = HID_Settings()
#        vref_en = analogio.AnalogIn(board.VOLTAGE_MONITOR)
        self.battery_sense = analogio.AnalogIn(board.VOLTAGE_MONITOR)
    
    # determine the number of bars representing the logic supply voltage
    @staticmethod
    def battery_level(battery_voltage):
        vbat=int((battery_voltage / 100) + 140)
        range_map = lambda input, in_min, in_max, out_min, out_max: (((input - in_min) * (out_max - out_min)) / (in_max - in_min)) + out_min
        return int(range_map(vbat, settings.min_battery, settings.max_battery, 0, 4))

    # create the battery level icon and text
    def create_battery_level(self, x, y):
        # get voltage
        battery_voltage = self.battery_sense.value
        # show voltage value
        bat_level_group = displayio.Group()
        batvolt = label.Label(font=terminalio.FONT, text=str('{:.2f}v'.format((battery_voltage/10000)+1)), color=ui.white, scale=1)
        batvolt.x, batvolt.y = 235, 7
        bat_level_group.append(batvolt)
        # show battery icon
        bat_level_group.append(Rect(x, y, 19, 10, fill=ui.white, outline=ui.white))
        bat_level_group.append(Rect(x + 19, y + 3, 2, 4, fill=ui.white, outline=ui.white))
        bat_level_group.append(Rect(x + 1, y + 1, 17, 8, fill=ui.black, outline=ui.black))
        if self.battery_level(battery_voltage) < 1:
            bat_level_group.append(Line(x + 3, y, x + 3 + 10, y + 10, ui.black))
            bat_level_group.append(Line(x + 3 + 1, y, x + 3 + 11, y + 10, ui.black))
            bat_level_group.append(Line(x + 2 + 2, y - 1, x + 4 + 12, y + 11, ui.white))
            bat_level_group.append(Line(x + 2 + 3, y - 1, x + 4 + 13, y + 11, ui.white))
        else:
            # show battery bars
            for i in range(4):
                if self.battery_level(battery_voltage) / 4 > (1.0 * i) / 4:
                    bat_level_group.append(Rect(i * 4 + x + 2, y + 2, 3, 6, fill=ui.white, outline=ui.white))
        return bat_level_group

    def usb_available(self):
        return supervisor.runtime.usb_connected

    def serial_available(self):
        return supervisor.runtime.serial_connected

    def usb_connected_icon(self):
        if self.usb_available():
            if self.serial_available():
                image, palette = adafruit_imageload.load(settings.path['icons'][0] + 'usb_serial.bmp', bitmap=displayio.Bitmap,
                                                         palette=displayio.Palette)
            else:
                image, palette = adafruit_imageload.load(settings.path['icons'][0] + 'usb_ns.bmp', bitmap=displayio.Bitmap,
                                                         palette=displayio.Palette)
        else:
            image, palette = adafruit_imageload.load(settings.path['icons'][0] + 'blank.bmp', bitmap=displayio.Bitmap,
                                                     palette=displayio.Palette)
        tile_grid = displayio.TileGrid(image, pixel_shader=palette)
        return tile_grid

    @staticmethod        
    def create_storage_usage(x):
        storage_usage = displayio.Group()
        # f_bfree and f_bavail should be the same?
        # f_files, f_ffree, f_favail and f_flag are unsupported.
        f_bsize, f_frsize, f_blocks, f_bfree, _, _, _, _, _, f_namemax = os.statvfs("/")
        f_total_size = f_frsize * f_blocks
        f_total_free = f_bsize * f_bfree
        f_total_used = f_total_size - f_total_free
        f_used = 100 / f_total_size * f_total_used
        # f_free = 100 / f_total_size * f_total_free
        batbg = Rect(x + 10, 3, 80, 10, fill=ui.black, outline=ui.white)
        batlvl1 = Rect(x + 11, 4, 78, 8, fill=ui.black, outline=ui.black)
        batlvl2 = Rect(x + 12, 5, int(76 / 100.0 * f_used), 6, fill=ui.white, outline=ui.white)
        battxt = label.Label(font=terminalio.FONT, text='{:.0f}%'.format(f_used), color=ui.white, scale=1)
        battxt.x, battxt.y = x + 92, 7
        storage_usage.append(batbg)
        storage_usage.append(batlvl1)
        storage_usage.append(batlvl2)
        storage_usage.append(battxt)
        return storage_usage

    @ property
    def value(self):
        # init and set black background
        bar = displayio.Group()
        background = Rect(0, 0, self.display.width, 16, fill=ui.black, outline=ui.black)
        # title
        title = label.Label(font=terminalio.FONT, text='AIV @ DC31', color=ui.white, scale=1)
        title.x, title.y = 3, 7
        # storage usage
        stg = self.create_storage_usage(85)
        # battery
        battery = self.create_battery_level(self.display.width - 22 - 3, 3)
        # country/language
        llang = label.Label(font=terminalio.FONT, text=self.settings.language.upper(), color=ui.white, scale=1)
        llang.x, llang.y = 202, 7
        # usb icon
        usb_icon = self.usb_connected_icon()
        usb_icon.x, usb_icon.y = 216, 0
        # append components
        bar.append(background)
        bar.append(title)
        bar.append(stg)
        bar.append(battery)
        bar.append(llang)
        bar.append(usb_icon)
        return bar


class HID_Settings:
    def __init__(self):
        self.language = self.keyboard_language()
        self.layout = self.keyboard_layout(self.language)

    @staticmethod
    def keyboard_language():
        try :
            language = microcontroller.nvm[0:2].decode() # 2 chars form nvm memory index 0
        except:
            language = 'us' # default
        return language
    
    @staticmethod
    def keyboard_layout(language):
        try:
            keyboard = Keyboard(usb_hid.devices)
            if language == 'fr':
                # France
                from adafruit_hid.keyboard_layout_fr import KeyboardLayoutFR
                layout = KeyboardLayoutFR(keyboard)
            else:
                # USA
                from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
                layout = KeyboardLayoutUS(keyboard)
            return layout
        except:
            return None


class Progress_Indicator:

    def __init__(self, x, y, width, height, text_scale, bar_font=terminalio.FONT):
        self.x, self.y, self.width, self.height, self.text_scale = x, y, width, height, text_scale
        self.bar_font = bar_font

    def bar(self, percent_complete):
        bar = displayio.Group()
        print(self.x, self.y, self.width, self.height)
        bar_background = Rect(self.x, self.y, self.width, self.height, fill=ui.black, outline=ui.white)
        print(self.x + 1, self.y + 1, self.width - 2, self.height - 2)
        bar_frame = Rect(self.x + 1, self.y + 1, self.width - 2, self.height - 2, fill=ui.black, outline=ui.black)
        print(self.x + 3, self.y + 3, int((self.width - 6) / 100.0 * percent_complete), self.height - 6)
        bar_progress = Rect(self.x + 3, self.y + 3, int((self.width - 6) / 100.0 * percent_complete + 1), self.height - 6, fill=ui.white, outline=ui.white)
        bar_text = label.Label(font=self.bar_font, text='{:.0f}%'.format(percent_complete), color=ui.black, scale=self.text_scale)
        bar_text.x, bar_text.y = self.x + self.width + 2, self.y + 8
        bar.append(bar_background)
        bar.append(bar_frame)
        bar.append(bar_progress)
        bar.append(bar_text)
        return bar

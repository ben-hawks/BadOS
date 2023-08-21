'''
    BadOS Launcher main.py
    By David Guidos, May 2022
    Inspired by the Pimoroni Badger2040 badge, AdaFruit and BeBox
'''

import gc, os, sys, math, time, builtins
import board, microcontroller, storage, supervisor
import analogio, digitalio, busio, displayio , terminalio , vectorio, usb_hid, simpleio
from digitalio import DigitalInOut, Direction, Pull

from BadOS_Screen import Screen
from BadOS_Buttons import Buttons
from BadOS_Menu import Menu


# Import some board specific configuration
import configuration

config_file = "/config/" + board.board_id.replace(".", "_")
hw_impl = builtins.__import__(config_file, None, None, ["config"], 0)

from configuration import settings, ui

settings.hw = hw_impl.config
gc.collect()

# constants
WHITE = ui.bg_color
BLACK = ui.fg_color

def read_le(s):
    # as of this writting, int.from_bytes does not have LE support, DIY!
    result = 0
    shift = 0
    for byte in bytearray(s):
        result += byte << shift
        shift += 8
    return result

# get app list
def get_app_list():
    app_list = []
    # get app information from app directories; names and icon bitmaps

    for i in settings.path["apps"]:
        app_list += [[app, i + app + '/' + app + '.bmp', i + app + '/' + app + '.py'] for app in os.listdir(i) if app[0:1] != "."]
    app_list.sort()
    #print(app_list)
    return app_list 

# menu selection handler
def menu_select(n):
    # invoke the selected app
    ix = menu_page * 3 + n
    if ix < len(app_list):
        #appname = app_list[ix][0]
        app_path = app_list[ix][2]
        supervisor.set_next_code_file(app_path)
        supervisor.reload()

# page selecton handler
def page_select(p):
    global menu_page
    menu_page += p
    if menu_page < 0: menu_page = 0    # TODO: rotate back to last page ?
    if menu_page * 3 >= len(app_list): menu_page = 0


#   m a i n   s e c t i o n

# disable autoreload - only useful during development, restarts board when files on CIRCUITPY mount are changed
supervisor.runtime.autoreload = True

# check for HID request on restart (any A,B,C pressed)
#if buttons.a.value or buttons.b.value or buttons.c.value:
    # TODO: invoke HID app for the specified button
#    pass

# create OS screen
screen = Screen()

# buttons and LED
buttons = Buttons()
buttons.set_led(True) # led on during start-up

# get list of apps for menu and create menu object
menu_page = 0
app_list = get_app_list()
#print(app_list)
icon_path = settings.path["icons"][0]
menu = Menu(settings.hw.display, screen, buttons, app_list, screen.fonts[0], settings.path["icons"][0] + 'file' + '.bmp')
gc.collect()

# main loop root 
while True:
    ix = menu.show_menu(menu_page)
    if ix < 3:
        # a,b,c
        menu_select(ix)
    elif ix < 5:
        # up, down
        page_select(-1 if ix == 3 else 1)

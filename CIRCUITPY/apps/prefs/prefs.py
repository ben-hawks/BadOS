'''
    prefs.py
    BadOS Language Preferences Selection Program
    David Guidos, May 2022
'''

import os, time
import board, supervisor, microcontroller
import displayio, terminalio, vectorio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label

from BadOS_Screen import Screen
from BadOS_Buttons import Buttons
from BadOS_Menu import Menu

WHITE = 0xFFFFFF
BLACK = 0x000000

# language preferences list
language_list = [('France','/apps/prefs/france.bmp'),('USA','/apps/prefs/usa.bmp')]

def read_le(s):
    # as of this writting, int.from_bytes does not have LE support, DIY!
    result = 0
    shift = 0
    for byte in bytearray(s):
        result += byte << shift
        shift += 8
    return result

# save language preference to non-volatile memory
# languages saved as 'fr' or 'us'
def save_language(lang):
    tomem=bytearray(lang.encode())
    microcontroller.nvm[0:2]=tomem[0:2]   

# preference menu selection handler
def menu_select(n):
    # save the selected language
    ix = menu_page * 3 + n
    if ix < len(language_list):
        lang = language_list[ix][0][:2].lower()
        save_language(lang)
        # return to the main menu
        supervisor.reload()

# arrow button selecton handler
def page_select(p):
    # arrow key pressed
    # return to the main menu
    supervisor.reload()


#   m a i n   

# initialize display
display = board.DISPLAY
display.rotation = 270
palette = displayio.Palette(1)
palette[0] = WHITE
palette_inverted = displayio.Palette(1)
palette_inverted[0] = BLACK
WIDTH = display.width
HEIGHT = display.height

# create screen
scr = Screen(background_color = WHITE, with_status_bar = True)

# set up buttons
buttons = Buttons()

# create the book selection menu
menu = Menu(display, scr, buttons, language_list, scr.fonts[0], '/apps/prefs/prefs.bmp')

# main loop root
menu_page = 0 
while True:
    ix = menu.show_menu(menu_page)
    if ix < 3:
        # a,b,c
        menu_select(ix)
    elif ix < 5:
        # up, down
        page_select(-1 if ix == 3 else 1)


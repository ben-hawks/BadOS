'''
keyboard app
By David Guidos, May 2022
Inspired by the Pimoroni Badger2040 badge, AdaFruit and BeBox???
'''
import gc, os , math, microcontroller, digitalio, board, storage, supervisor
import analogio, time, usb_hid
from adafruit_hid.keyboard import Keyboard
import adafruit_ducky, busio, displayio , terminalio , vectorio
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
import adafruit_imageload
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.circle import Circle
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_display_shapes.triangle import Triangle
from adafruit_display_shapes.line import Line
from adafruit_display_shapes.polygon import Polygon
import adafruit_miniqr

from BadOS_Buttons import Buttons
from BadOS_Screen import Screen, Status_Bar
from BadOS_Menu import Menu

WHITE = 0xFFFFFF
BLACK = 0x000000
MAX_BATTERY_VOLTAGE = 400
MIN_BATTERY_VOLTAGE = 320
ICONS_DIR = '/assets/icons/'
IMAGES_DIR = '/assets/images/'
FONTS_DIR = '/assets/fonts/'

SCRIPTS_DIR ='/ducky/'

def get_scripts_list():
    # scan files for HID scripts
    ListHIDFiles = os.listdir(SCRIPTS_DIR)
    hidfiles = []
    count = 0
    for n in ListHIDFiles:
        print("checking ", n)
        if n[-4:] == ".txt" and n[0:2] != "._":
            print("valid script:  ", n)
            script = n.replace(".txt", "")
            print("script name:  ", script)
            if script+".bmp" in ListHIDFiles:
                hidfiles.append((script, script+".bmp"))
            else:
                hidfiles.append((script,))

    hidfiles.sort()
    # add selection for exit
    hidfiles.append(('EXIT', '/assets/icons/exit.bmp'))
    print(hidfiles)
    return hidfiles



def fixlayout(lang):
    global usb, keyboard, keyboard_layout
    print("fixlayout usb =", end='')
    print(usb)
    try:
        keyboard = Keyboard(usb_hid.devices)
        usb=True
    except:
        usb=False
    layout=lang
    if usb==True:
        keyboard = Keyboard(usb_hid.devices)
        if lang=="fr": 
            from adafruit_hid.keyboard_layout_fr import KeyboardLayoutFR
            keyboard_layout = KeyboardLayoutFR(keyboard)  # We're in France :)
            
        else:
            from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
            keyboard_layout = KeyboardLayoutUS(keyboard)  # We're in the US :)
    else:
        print("not connected on usb")
        #usb=False
    return usb
    #print(tomem[0:2] + " / " + lang + "/" + layout)
        
def callduck(filename):
    if usb==True:
        duck = adafruit_ducky.Ducky(filename, keyboard, keyboard_layout)    
        result = True
        while result is not False:
            result = duck.loop()
    else:
        result = "No usb"
    return result

# menu selection handler
def menu_select(n, item_list):
    # display the selected badge
    ix = menu_page * 3 + n
    if ix < len(item_list):
        item = item_list[ix][0]
        if item == 'EXIT':
            # exit requested
            # turn on activity LED
            buttons.set_led(True)
            # return to the main menu
            supervisor.reload()
        else:
            pass


# page selecton handler
def page_select(p, list):
    global menu_page
    menu_page += p
    if menu_page < 0: menu_page = 0    # TODO: rotate back to last page ?
    if menu_page * 3 >= len(list): menu_page = 0

#   m a i n

#HID init
try:
    keyboard = Keyboard(usb_hid.devices)
    usb=True
except:
    usb=False
flag=False



try :
    layout = microcontroller.nvm[0:2].decode() # 2 chars form nvm memory index 0
except:
    layout = "us" # fr or us fixed value if no data in memory
try:    
    if usb==True:
        keyboard = Keyboard(usb_hid.devices)
        if layout=="fr": 
            from adafruit_hid.keyboard_layout_fr import KeyboardLayoutFR
            keyboard_layout = KeyboardLayoutFR(keyboard)  # We're in France :)
            
        else:
            from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
            keyboard_layout = KeyboardLayoutUS(keyboard)  # We're in the US :)
except:
    print("error")

#   m a i n   s e c t i o n

# variables
menu_page = 0
# buttons and LED
buttons = Buttons()
buttons.led.value = 1   # led on during start-up

# initialize display
display = board.DISPLAY
display.rotation = 270
palette = displayio.Palette(1)
palette[0] = WHITE
palette_inverted = displayio.Palette(1)
palette_inverted[0] = BLACK
WIDTH = display.width
HEIGHT = display.height
IMAGE_WIDTH = 104

# create screen
ducky_screen = Screen()

# get list of badges for menu
scripts_list = get_scripts_list()

# create the badge selection menu
menu = Menu(display, ducky_screen, buttons, scripts_list, ducky_screen.fonts[0], ICONS_DIR+'file.bmp')


## Ducky Flow?:
'''
1. User opens Ducky app
2. List scripts in /ducky
3. user selects a specific script
4. write selected file to NVmem? File? Something??
5. reboot pico 
6. boot.py checks for ducky mode flag, unsets flag, if true configures USB as a keyboard, else boots into normal mode
7. duck_main.py sets USB Device Descriptor, manu, product, etc. to a keyboard
8. loop trying to open a USB_HID connection, waiting for user to plug in USB 
9. once USB is plugged in, have present a "Run" "Stop" and "Exit" option 
10. run script when RUN pressed (calls apps/ducky/... functions) 
11. stop when STOP pressed twice rapidly, change option to "Run" "Restart" "Exit" 
12. when "restart" pressed, start from the top of the script, "run" continues from where left off
13. when EXIT pressed three times rapidly (while running or stopped) or once (once done or before running), reboot board

'''


# main loop root
while True:
    ix = menu.show_menu(menu_page)
    if ix < 3:
        # a,b,c
        menu_select(ix, scripts_list)
    elif ix < 5:
        # up, down
        page_select(-1 if ix == 3 else 1, scripts_list)



'''BadOS Badge App - Display digital badges with QR codes'''

import gc, os
from os import listdir
from time import sleep
from gc import collect
import board, displayio
from adafruit_display_text import label
from adafruit_display_shapes.line import Line
from adafruit_display_shapes.rect import Rect
import adafruit_miniqr, adafruit_imageload
from bados.menu import Menu
from bados.configuration import ui

collect()
BADGES_DIR = '/apps/badge/'
DISPLAY_WIDTH, DISPLAY_HEIGHT, IMAGE_WIDTH = display.width, display.height, 104

# Load fonts
try:
    from adafruit_bitmap_font import bitmap_font
    FONT_SMALL = bitmap_font.load_font("/assets/fonts/Arial-12.bdf")
except Exception:
    import terminalio
    FONT_SMALL = terminalio.FONT
FONT_LARGE = FONT_SMALL

# QR palette
qr_palette = displayio.Palette(1)
qr_palette[0] = ui.white


def bitmap_QR(matrix, border=2):
    """Convert QR matrix to bitmap"""
    bmp = displayio.Bitmap(matrix.width + border * 2, matrix.height + border * 2, 2)
    for y in range(matrix.height):
        for x in range(matrix.width):
            bmp[x + border, y + border] = 1 if matrix[x, y] else 0
    return bmp


def badgeQR(badge_data, badge):
    """Generate QR code with memory-safe field exclusion"""
    collect()
    exclude_opts = [[], ['note'], ['note', 'title'], ['note', 'title', 'site'],
                    ['note', 'title', 'site', 'telfix'], ['note', 'title', 'site', 'telfix', 'telmob']]

    for exclude in exclude_opts:
        try:
            collect()
            vcard_text = vcard(badge_data, exclude)
            qr = adafruit_miniqr.QRCode(qr_type=9, error_correct=adafruit_miniqr.L)
            qr.add_data(vcard_text.encode('ascii'))
            qr.make()
            qr_bmp = bitmap_QR(qr.matrix)
            collect()

            pos_x = DISPLAY_WIDTH - IMAGE_WIDTH + (IMAGE_WIDTH - qr_bmp.width) // 2
            pos_y = (DISPLAY_HEIGHT - qr_bmp.height) // 2
            qr_img = displayio.TileGrid(qr_bmp, pixel_shader=qr_palette, x=pos_x, y=pos_y)
            badge.append(qr_img)

            if exclude:
                print(f"QR: excluded {', '.join(exclude)}")
            return
        except (MemoryError, Exception) as e:
            if isinstance(e, MemoryError):
                print("QR: Memory error, retrying...")
            collect()

    # Failed - show error
    print("QR: Unable to generate")
    try:
        err = label.Label(FONT_SMALL, text="QR: Out of memory", color=ui.white, scale=1)
        err.x, err.y = DISPLAY_WIDTH - IMAGE_WIDTH + 10, DISPLAY_HEIGHT // 2
        badge.append(err)
    except Exception:
        pass


def get_badge_data(path):
    """Load badge data from file"""
    data = {}
    try:
        with open(path) as f:
            for key in ['company', 'name', 'detail1_title', 'detail1_text',
                       'detail2_title', 'detail2_text', 'telfix', 'telmob', 'email', 'site']:
                data[key] = f.readline().strip()
    except Exception as e:
        print(f'Error reading {path}: {e}')
    return data


def vcard(data, exclude=None):
    """Generate vCard text with optional field exclusion"""
    exclude = exclude or []
    v = 'BEGIN:VCARD\nVERSION:3.0\n'

    if 'name' in data:
        v += f"N:{data.get('name', '')};\n"
    if 'telfix' not in exclude and data.get('telfix'):
        v += f"TEL;TYPE=work:{data['telfix']}\n"
    if 'telmob' not in exclude and data.get('telmob'):
        v += f"TEL;TYPE=cell:{data['telmob']}\n"
    if 'email' not in exclude and data.get('email'):
        v += f"EMAIL;TYPE=work:{data['email']}\n"
    if 'company' not in exclude and data.get('company'):
        v += f"ORG:{data['company']}\n"
    if 'title' not in exclude and (data.get('detail1_title') or data.get('detail1_text')):
        v += f"TITLE:{data.get('detail1_title', '')} {data.get('detail1_text', '')}\n"
    if 'note' not in exclude and (data.get('detail2_title') or data.get('detail2_text')):
        v += f"NOTE:{data.get('detail2_title', '')} {data.get('detail2_text', '')}\n"
    if 'site' not in exclude and data.get('site'):
        v += f"URL:{data['site']}\n"

    return v + 'END:VCARD\n'


def add_label(grp, font, text, color, x, y):
    """Helper to add text label"""
    lbl = label.Label(font=font, text=text, color=color, scale=1)
    lbl.x, lbl.y = x, y
    grp.append(lbl)


def show_badge(badgename, data, img_path):
    """Display badge with photo or QR code"""
    global showqr
    CH, DH = 40, 20  # Company height, details height
    NH = DISPLAY_HEIGHT - CH - DH * 2 - 2  # Name height
    TW, LP = DISPLAY_WIDTH - IMAGE_WIDTH - 2, 5  # Text width, left padding

    badge = displayio.Group()
    photo = None

    # Load photo if not showing QR
    if not showqr:
        try:
            img = displayio.OnDiskBitmap(img_path)
            photo = displayio.TileGrid(img, pixel_shader=img.pixel_shader)
            photo.x, photo.y = DISPLAY_WIDTH - IMAGE_WIDTH, 0
        except Exception:
            try:
                img, pal = adafruit_imageload.load('/assets/images/user.bmp',
                                                   bitmap=displayio.Bitmap, palette=displayio.Palette)
                photo = displayio.TileGrid(img, pixel_shader=pal)
                photo.x, photo.y = DISPLAY_WIDTH - IMAGE_WIDTH, 0
            except Exception:
                pass

    # Build badge display
    badge.append(Rect(0, 0, DISPLAY_WIDTH + 1, DISPLAY_HEIGHT, fill=ui.black, outline=ui.black))

    # Border around image area
    for coords in [(DISPLAY_WIDTH - IMAGE_WIDTH, 0, DISPLAY_WIDTH - 1, 0),
                   (DISPLAY_WIDTH - IMAGE_WIDTH, 0, DISPLAY_WIDTH - IMAGE_WIDTH, DISPLAY_HEIGHT - 1),
                   (DISPLAY_WIDTH - IMAGE_WIDTH, DISPLAY_HEIGHT - 1, DISPLAY_WIDTH - 1, DISPLAY_HEIGHT - 1),
                   (DISPLAY_WIDTH - 1, 0, DISPLAY_WIDTH - 1, DISPLAY_HEIGHT - 1)]:
        badge.append(Line(*coords, ui.white))

    # Company name
    add_label(badge, FONT_LARGE, data['company'], ui.white, LP, CH // 2)

    # Name section (white background)
    badge.append(Rect(1, CH + 1, TW, NH, fill=ui.white, outline=ui.white))
    add_label(badge, FONT_LARGE, data['name'], ui.black, LP, NH // 2 + CH)

    # Details sections (white backgrounds)
    badge.append(Rect(1, DISPLAY_HEIGHT - DH * 2, TW, DH - 1, fill=ui.white, outline=ui.white))
    badge.append(Rect(1, DISPLAY_HEIGHT - DH, TW, DH - 1, fill=ui.white, outline=ui.white))

    # Detail 1
    add_label(badge, FONT_SMALL, data['detail1_title'], ui.black, LP, DISPLAY_HEIGHT - DH * 3 // 2)
    add_label(badge, FONT_SMALL, data['detail1_text'], ui.black, 97, DISPLAY_HEIGHT - DH * 3 // 2)

    # Detail 2
    add_label(badge, FONT_SMALL, data['detail2_title'], ui.black, LP, DISPLAY_HEIGHT - DH // 2)
    add_label(badge, FONT_SMALL, data['detail2_text'], ui.black, 97, DISPLAY_HEIGHT - DH // 2)
    collect()

    # Main display loop
    while True:
        if showqr:
            badgeQR(data, badge)
        elif photo:
            badge.append(photo)

        display.root_group = badge
        while display.time_to_refresh > 0:
            sleep(0.01)

        try:
            display.refresh()
        except RuntimeError:
            sleep(0.5)
            try:
                display.refresh()
            except Exception:
                pass

        if showqr or photo:
            badge.pop()

        btn = buttons.await_click()
        buttons.set_led(True)
        while buttons.read(btn):
            sleep(0.05)
        buttons.set_led(False)

        if btn == 'DOWN' or btn not in ['UP']:
            return
        showqr = not showqr


def get_badge_list():
    """Get list of available badges"""
    lst = []
    try:
        for b in listdir(BADGES_DIR):
            if "." not in b:
                lst.append([b.upper(), f'{BADGES_DIR}{b}/{b}.bmp', f'{BADGES_DIR}{b}/{b}.txt'])
    except Exception as e:
        print(f"Error loading badges: {e}")

    lst.sort()
    lst.append(['EXIT', '/assets/icons/exit.bmp', ''])
    return lst


# === MAIN ===
menu_page = 0
showqr = False

badge_list = get_badge_list()
collect()

menu = Menu(display, screen, buttons, badge_list, FONT_SMALL, BADGES_DIR + 'badge.bmp')
collect()

# Main loop
while True:
    result = menu.show_menu(menu_page)
    if result is None:
        continue

    max_page = (len(badge_list) - 1) // 3

    if result == -2:  # UP
        menu_page = (menu_page - 1) % (max_page + 1)
    elif result == -3:  # DOWN
        menu_page = (menu_page + 1) % (max_page + 1)
    elif 0 <= result <= 2:
        ix = menu_page * 3 + result
        if ix < len(badge_list):
            if badge_list[ix][0] == 'EXIT':
                break
            collect()
            show_badge(badge_list[ix][0], get_badge_data(badge_list[ix][2]), badge_list[ix][1])

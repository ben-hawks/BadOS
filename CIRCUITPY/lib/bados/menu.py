"""Minimal menu renderer for BadOS - optimized for low memory"""

import os
import gc
import displayio
import adafruit_imageload
import terminalio
from adafruit_display_text.label import Label
from adafruit_display_shapes.rect import Rect
import time

try:
    import board
except ImportError:
    board = None

try:
    import supervisor
except ImportError:
    supervisor = None

try:
    from bados.configuration import ui
except ImportError:
    class _UI:
        white = 0xFFFFFF
        black = 0x000000
        bg_color = 0xFFFFFF
        fg_color = 0x000000
        status_bar_height = 16
        button_pos = [50, 148, 246]
    ui = _UI()


class Status_Bar:
    """Minimal status bar with battery, storage, and USB indicators"""
    def __init__(self, display):
        self.display = display
        self.icon_cache = {}

    @property
    def value(self):
        """Return status bar group"""
        bar = displayio.Group()
        w = self.display.width

        # Black background
        bar.append(Rect(0, 0, w, ui.status_bar_height, fill=ui.black, outline=ui.black))

        # Title
        try:
            title = Label(terminalio.FONT, text='BadOS', color=ui.white, scale=1)
            title.x, title.y = 3, 7
            bar.append(title)
        except Exception:
            pass

        # Storage usage indicator
        try:
            f_bsize, f_frsize, f_blocks, f_bfree, *_ = os.statvfs("/")
            used_pct = 100.0 * (f_blocks - f_bfree) / f_blocks

            # Storage bar background
            bar.append(Rect(45, 3, 50, 10, fill=ui.black, outline=ui.white))
            # Storage level bar
            bar.append(Rect(47, 5, int(46 * used_pct / 100), 6, fill=ui.white, outline=ui.white))
            # Percentage text
            pct_text = Label(terminalio.FONT, text=f'{int(used_pct)}%', color=ui.white, scale=1)
            pct_text.x, pct_text.y = 97, 7
            bar.append(pct_text)
        except Exception:
            pass

        # Battery indicator (before USB icon so USB renders on top)
        try:
            import analogio
            battery = analogio.AnalogIn(board.VOLTAGE_MONITOR)
            raw = battery.value
            volt = (raw / 10000) + 1

            # Battery box
            bx = w - 24
            bar.append(Rect(bx, 3, 19, 10, fill=ui.white, outline=ui.white))
            bar.append(Rect(bx + 19, 6, 2, 4, fill=ui.white, outline=ui.white))
            bar.append(Rect(bx + 1, 4, 17, 8, fill=ui.black, outline=ui.black))

            # Bars based on voltage
            bars = max(0, min(4, int((volt - 3.2) / 0.2)))
            for i in range(bars):
                bar.append(Rect(i * 4 + bx + 2, 5, 3, 6, fill=ui.white, outline=ui.white))
        except Exception:
            pass

        # USB connection icon (render last so it's on top)
        try:
            if supervisor is not None and supervisor.runtime.usb_connected:
                icon_name = 'usb_serial.bmp' if supervisor.runtime.serial_connected else 'usb_ns.bmp'
            else:
                icon_name = 'blank.bmp'

            icon_path = f'/assets/icons/{icon_name}'

            # Try to load from cache or file
            if icon_path in self.icon_cache:
                img, pal = self.icon_cache[icon_path]
            else:
                try:
                    img, pal = adafruit_imageload.load(icon_path, bitmap=displayio.Bitmap, palette=displayio.Palette)
                    self.icon_cache[icon_path] = (img, pal)
                except Exception:
                    img, pal = None, None

            if img and pal:
                usb_icon = displayio.TileGrid(img, pixel_shader=pal)
                # Position to the left of battery (adjust x position)
                usb_icon.x = w - 44  # Move further left to avoid battery overlap
                usb_icon.y = 0
                bar.append(usb_icon)
        except Exception:
            pass

        return bar


class ImageCache:
    """Simple image cache"""
    def __init__(self):
        self._cache = {}

    def get(self, path):
        if path in self._cache:
            return self._cache[path]
        try:
            img, pal = adafruit_imageload.load(path, bitmap=displayio.Bitmap, palette=displayio.Palette)
            self._cache[path] = (img, pal)
            return img, pal
        except Exception:
            return None, None


class Menu:
    """Minimal menu - renders icons and labels with status bar"""

    def __init__(self, display, screen, buttons, item_list, font=None, defaulticon=None, rtc_obj=None):
        self.display = display
        self.buttons = buttons
        self.items = item_list or []
        self.font = font or terminalio.FONT
        self.defaulticon = defaulticon
        self.cache = ImageCache()
        self.last_page = None
        self.status_bar = Status_Bar(display)

    def render_page(self, pagenum):
        """Render menu page with icons and labels"""
        gc.collect()

        # Validate display is still available
        if self.display is None:
            raise RuntimeError("Display is None - was it released?")

        w = self.display.width
        h = self.display.height
        top = ui.status_bar_height

        # Create menu group
        mg = displayio.Group()
        mg.append(Rect(0, top, w, h - top, fill=ui.bg_color, outline=ui.bg_color))

        # Layout calculations
        content_h = h - top
        icon_area = content_h - 30
        icon_y = top + (icon_area // 2)
        label_y = top + icon_area + 8

        items_per_page = len(ui.button_pos)

        # Render each menu item
        for i in range(items_per_page):
            idx = pagenum * items_per_page + i
            if idx >= len(self.items):
                continue

            try:
                name, icon_path, _ = self.items[idx]
            except Exception:
                continue

            x = ui.button_pos[i]

            # Try to load icon
            img, pal = None, None
            if icon_path:
                img, pal = self.cache.get(icon_path)
            elif self.defaulticon:
                img, pal = self.cache.get(self.defaulticon)

            # Render icon or placeholder
            if img and pal:
                try:
                    tile = displayio.TileGrid(img, pixel_shader=pal)
                    tile.x = x - img.width // 2
                    tile.y = icon_y - img.height // 2
                    mg.append(tile)
                except Exception:
                    img = None

            if not img:
                # Simple placeholder
                size = 48
                px = x - size // 2
                py = icon_y - size // 2
                mg.append(Rect(px - 2, py - 2, size + 4, size + 4, fill=None, outline=ui.fg_color))
                mg.append(Rect(px, py, size, size, fill=0xCCCCCC if ui.bg_color == 0xFFFFFF else 0x333333, outline=ui.fg_color))
                try:
                    ch = name[0].upper() if name else "?"
                    lbl = Label(terminalio.FONT, text=ch, color=ui.fg_color, scale=3)
                    lbl.x = x - 9
                    lbl.y = icon_y
                    mg.append(lbl)
                except Exception:
                    pass

            # Label
            try:
                text = (name or "")[:8].upper()
                lbl = Label(self.font, text=text, color=ui.fg_color, scale=1)
                lbl.x = x - len(text) * 3
                lbl.y = label_y
                mg.append(lbl)
            except Exception:
                pass

        # Page indicators
        total_pages = (len(self.items) - 1) // items_per_page + 1 if self.items else 1
        if total_pages > 1:
            ind_x = w - 10
            ind_y_start = (h - ui.status_bar_height) // 2 - (total_pages * 8 // 2)
            for p in range(total_pages):
                fill = ui.black if p == pagenum else ui.white
                mg.append(Rect(ind_x, top + ind_y_start + p * 8, 6, 6, fill=fill, outline=ui.black))

        return mg

    def show_menu(self, pagenum):
        """Display menu and wait for button press"""
        # Always render if page changed OR if last_page is None (first run)
        if pagenum != self.last_page or self.last_page is None:
            gc.collect()

            # Create root group with status bar and menu
            root = displayio.Group()
            root.append(self.render_page(pagenum))
            root.append(self.status_bar.value)

            self.display.root_group = root

            # Wait for display to be ready before refreshing
            while self.display.time_to_refresh > 0:
                time.sleep(0.01)

            try:
                self.display.refresh()
            except RuntimeError:
                # Display not ready yet, wait a bit
                time.sleep(0.1)
                try:
                    self.display.refresh()
                except Exception:
                    pass  # Give up if still failing
            except Exception:
                pass

            # Only update last_page AFTER successful render
            self.last_page = pagenum
            gc.collect()

        # Wait for button
        result = self.buttons.await_click()

        # Handle both tuple (name, raw) and string returns
        if isinstance(result, tuple):
            button = result[0]  # Extract button name from tuple
        else:
            button = result

        # Map button name directly
        if button == 'UP':
            return -2
        elif button == 'DOWN':
            return -3
        elif button == 'A':
            return 0
        elif button == 'B':
            return 1
        elif button == 'C':
            return 2

        return None

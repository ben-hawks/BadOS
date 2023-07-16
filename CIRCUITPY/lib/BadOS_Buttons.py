'''
    BadOS_Buttons
    Common Button Handling Functions for BadOS
    David Guidos, May 2022
'''

__version__ = "1.0.0"
__repo__ = "https://github.com/guidoslabs/BadOS.git"

import time
import board, microcontroller, storage, supervisor
from digitalio import DigitalInOut, Direction, Pull

class Buttons:

    def __init__(self, button_pins=None):
        # Define the buttons we're using here, which will be assigned an index based on the order they're in the array
        if button_pins is None:
            self.button_pins = [("a", board.SW_A), ("b", board.SW_B), ("c", board.SW_C),
                                ("up", board.SW_UP), ("down", board.SW_DOWN)]
        else:
            self.button_pins = button_pins

        # USER_SW only present on Badger2040, not Badger2040 W

        if board.board_id == "pimoroni_badger2040":
            self.button_pins.append(("user", board.USER_SW))

        # dynamically set all of our buttons attributes
        self.button_list = []
        for idx, (button_id, pin) in enumerate(self.button_pins):
            btn = DigitalInOut(pin)
            btn.direction = Direction.INPUT
            btn.pull = Pull.DOWN
            setattr(self, button_id, btn)
            self.button_list.append({"btn": btn, "id": button_id, "idx": idx, "pin":pin})

        #setup our USER LED
        self.led = DigitalInOut(board.USER_LED)
        self.led.direction = Direction.OUTPUT

        print(self.led.value)

    def set_led(self,state=False):
        self.led.value = state

    # wait for button click and return index of button (0,1,2 for a,b,c; 4,5 for up,down)
    def await_click(self):
        clicked = False
        self.set_led()  # awaiting click; activity LED off
        while not clicked:
            bs = self.states()
            clicked = any(bs)
            # prevent spinning    TODO: sleep mode to save energy?
            time.sleep(0.01)
        return self.button_list[bs.index(True)]

    # state of all buttons [a,b,c,up,down]
    def states(self):
        return [b["btn"].value for b in self.button_list]

    def pins(self):
        return [b["pin"] for b in self.button_list]

    # index of clicked button
    def states_index(self):
        bs = self.states()
        return self.button_list[bs.index(True)] if True in bs else -1



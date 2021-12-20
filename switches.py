# The MIT License (MIT)
# Copyright (c) 2021 Klaas Brant
# https://opensource.org/licenses/MIT

# Rotary class based on: http://www.mathertel.de/Arduino/RotaryEncoderLibrary.aspx
# https://github.com/mathertel/RotaryEncoder
# and https://github.com/MikeTeachman/micropython-rotary
# Button class based on M5Stack extensions

import sys
import micropython
micropython.alloc_emergency_exception_buf(100)
from machine import Pin
from time import ticks_ms

class Button:

    def __init__(self, pin, dbtime=50,pull_up=True,lobo=False):
        if pull_up:
            if lobo:
                self._pin = Pin(pin,Pin.IN,trigger=Pin.IRQ_ANYEDGE,handler=self._irq_cb,pull=Pin.PULL_UP)
            else:
                self._pin = Pin(pin,Pin.IN,pull=Pin.PULL_UP)
                self._pin.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self._irq_cb)
        else:
            if lobo:
                self._pin = Pin(pin,Pin.IN,trigger=Pin.IRQ_ANYEDGE,handler=self._irq_cb)
            else:
                self._pin = Pin(pin,Pin.IN)
                self._pin.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self._irq_cb)
        self.pin_value = 1
        self._dbtime = dbtime
        self._timeshoot = 0
        self._lastState = False
        self.startTicks = 0
        self.duration = 0
        self._event = 0
        self.trigger = self._trigger #cannot call directly, would result in allocation
        self._listener = []

    #Interrupt routine, remember keep it short and no allocations!
    def _irq_cb(self, pin):
        if ticks_ms() - self._timeshoot > self._dbtime: # wait for debounce
            #self.pin_value = pin.irqvalue()
            self.pin_value = self._pin.value()
            self._timeshoot = ticks_ms() # New wait time start now
            # FALLING = button pressed
            if self.pin_value == 0:  
                self._lastState = True
                self.startTicks = ticks_ms()
                self._event = 0x02  # EVENT_WAS_PRESSED
                self.duration = 0

        # RISING = button released
            elif self.pin_value == 1:
                if self._lastState == True: #if it was pressed...
                    self._lastState = False
                    self._event |= 0x04  # EVENT_WAS_RELEASED
                    self.duration = ticks_ms() - self.startTicks
            try:
                if len(self._listener) != 0:
                    micropython.schedule(self.trigger,self)
            except:
                pass

    def clear(self):
        self._event = 0

    def isPressed(self):
        return not self.pin_value()

    def wasPressed(self):
      if (self._event & 0x02) > 0: # Pressed?
        self._event -= 0x02 # Don't report again
        return True
      else:
        return False

    def wasReleased(self):
        if (self._event & 0x04 ) > 0: # EVENT_WAS_RELEASED
            self._event -= 0x04
            return self.duration
        else:
            return 0

    def add_listener(self, l):
        self._listener.append(l)

    def _trigger(self,_):
        for listener in self._listener:
            listener(not self.pin_value,self.duration)

class Rotary:

    RANGE_UNBOUNDED = const(1)
    RANGE_WRAP = const(2)
    RANGE_BOUNDED = const(3)
    
    def __init__(self, pin_x, pin_y, min_value=0, max_value=10, range_mode=RANGE_UNBOUNDED,lobo=False):
        self.min_value = min_value
        self.max_value = max_value
        self.range_mode = range_mode
        if lobo:
            self.pin_x = Pin(pin_x,Pin.IN,trigger=Pin.IRQ_ANYEDGE,handler=self._irq_cb)
            self.pin_y = Pin(pin_y,Pin.IN,trigger=Pin.IRQ_ANYEDGE,handler=self._irq_cb)
        else:
            self.pin_x = Pin(pin_x,Pin.IN)
            self.pin_x.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self._irq_cb)
            self.pin_y = Pin(pin_y,Pin.IN)
            self.pin_y.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self._irq_cb)
        self._listener = []
        self.trigger = self._trigger
        self._pos = 0
        self.old_pos = 0
        self.old_state = -1 # force a initial move
        self.position = 0
        self.direction = True # True is clockwise
        self.KNOBDIR = [0, -1, 1, 0,
                        1, 0, 0, -1,
                       -1, 0, 0, 1,
                        0, 1, -1, 0]

    #Interrupt routine, remember keep it short and no allocations!
    def _irq_cb(self,pin):
        x = self.pin_x.value()
        y = self.pin_y.value()
        new_state = x | (y << 1)
        if self.old_state != new_state:
            self.position += self.KNOBDIR[new_state | (self.old_state << 2)] # only valid seq/state cause changes
            self.old_state = new_state
            if new_state == 3: # latched again?
                self._pos = self.position >> 2 #shift back for external
                if self._pos != self.old_pos: # Did we change? If so remember and optional call back
                    self.direction = (self.old_pos < self._pos)
                   
                    if self.range_mode == self.RANGE_WRAP:
                        range = self.max_value - self.min_value + 1
                        if self._pos < self.min_value:
                            self._pos += range * ((self.min_value - self._pos) // range + 1)
                        self._pos = self.min_value + (self._pos - self.min_value) % range
                    elif self.range_mode == self.RANGE_BOUNDED:
                        self._pos = min(self.max_value, max(self.min_value, self._pos))
                    
                    self.setPosition(self._pos)
                    try:
                        if len(self._listener) != 0:
                            micropython.schedule(self.trigger,self)
                    except:
                        pass

    def _trigger(self,_):
        for listener in self._listener:
            listener(self._pos, self.direction)

    def add_listener(self, l):
        self._listener.append(l)

    def setPosition(self,value):
        if self.range_mode != self.RANGE_UNBOUNDED:
            if ((value < self.min_value) | (value > self.max_value)):
                raise IndexError()
        self.position = ((value << 2) | (self._pos & 3 ))
        self.old_pos = self._pos = value

    def value(self):
        return self._pos


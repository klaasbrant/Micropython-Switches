from switches import Rotary, Button
import time   

def prt_val(pos,direction):
    print(pos, direction)

def prt_btn(value,duration): # value True = pressed (duration = 0), False = Released (duration of pressed)
    print(value,duration)

r=Rotary(26,25,range_mode=Rotary.RANGE_BOUNDED,min_value=-10,max_value=10)  # connect to clk/dt or s1/s2
r.setPosition(5)
val_old = r.value()
r.add_listener(prt_val)
b=Button(27)  # connect to sw or key for rotary push button or just any button
b.add_listener(prt_btn)

print("Let's go Fellows")
while True:
    val_new = b.wasReleased()
    if val_new:
        print("Button released:",val_new,"Rotatry at: ",r.value())
    time.sleep_ms(10) # same thread!! will block IRQ's

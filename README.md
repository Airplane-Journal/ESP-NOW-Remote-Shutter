# ESP-NOW-Remote-Shutter
Remote shutter button for Adafruit Memento with ESP-NOW

Basically a mash up of these two learn guides: [ESP-NOW in CircuitPython](https://learn.adafruit.com/esp-now-in-circuitpython) and [Remote Shutter Button for Memento](https://learn.adafruit.com/memento-shutter).

![](https://github.com/Airplane-Journal/ESP-NOW-Remote-Shutter/blob/main/IMG_4606.jpg "Reading signal strength from the Memento ESP-NOW replies")

![](https://github.com/Airplane-Journal/ESP-NOW-Remote-Shutter/blob/main/IMG_4608.jpg "ESP-NOW message read receipts from the send_success and send_failure counters")

The code works great but I have been running into a frustrating safe mode issue with the Memento when its plugged into the rpi, like the rpi tries to mount the sd card and the Circuitpy drive, but then the Memento works okay when not plugged into USB.  Happens on even the simplest "Hello World" code.py.  Tried reinstalling CircuitPython without success.  I need to go look at the safe mode learn guide.

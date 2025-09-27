# Remote_Shutter7
# Wireless Shutter Button on Reverse TFT S3 for Memento with ESP-NOW
# 2025 Jean-Paul Lorrain
# MIT License

# Built upon:
# ESP-NOW transciever demo for ESP32-S2/S3 TFT Feather boards with display
# https://learn.adafruit.com/esp-now-in-circuitpython
# SPDX-FileCopyrightText: John Park for Adafruit 2025
# SPDX-License-Identifier: MIT

import os
import time
import wifi
import espnow
import board
import keypad
import neopixel
import digitalio
import displayio
import terminalio
from adafruit_display_text import label
from adafruit_button import Button
from adafruit_display_shapes.rect import Rect
from adafruit_progressbar.horizontalprogressbar import (
    HorizontalProgressBar,
    HorizontalFillDirection,
    )
from adafruit_simplemath import map_range
import supervisor

supervisor.runtime.autoreload = False

# Display setup
display = board.DISPLAY

def d_print(string):
    if DEBUG_MODE:
        print(string)

P2P_MODE = True
DEBUG_MODE = False
d_print(f"P2P_MODE is {P2P_MODE}, DEBUG_MODE is {DEBUG_MODE}.")

# Store Memento MAC address as Hex string in settings.toml
# like this: HEX_MEMENTO_MAC = "aa:bb:cc:dd:ee:ff"
HEX_MEMENTO_MAC = os.getenv("HEX_MEMENTO_MAC")
d_print(HEX_MEMENTO_MAC)

# Copilot helped write the bytes conversion
MEMENTO_MAC = bytes(int(x,16) for x in HEX_MEMENTO_MAC.split(":"))
d_print(MEMENTO_MAC)

# TFT colors
BLACK = 0x000000
WHITE = 0xFFFFFF
RED = 0xFF0000
TOMATO = 0xFF6347  # source guide
SKY_BLUE = 0x8ECAE6  # palette from https://coolors.co/
BLUE_GREEN = 0x219EBC
PRUSSIAN_BLUE = 0x023047
SELECTIVE_YELLOW = 0xFFB703
UT_ORANGE = 0xFB8500

# TFT Button constants
BUTTON_X = 0
BUTTON_WIDTH = int(display.width * 3/7)
BUTTON_HEIGHT = int(display.height / 3)

LABEL_PADDING = 1

# LED setup
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

# Neopixel setup, maybe for connection status?
status_pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.3)
status_pixel.fill(BLACK)

# Button setup using keypad to debounce
# All buttons have to be wired same for Keys object, so 2 objects need to be created
# This generates D1 and D2 key release events on first run, but otherwise works great,
# especially since the loop looks for key presses
D0_key = keypad.Keys((board.D0,), value_when_pressed=False, pull=True)
D1D2_keys = keypad.Keys((board.D1, board.D2), value_when_pressed=True, pull=False)

# Channel switching hack
wifi.radio.start_ap(" ", "", channel=6, max_connections=0)
wifi.radio.stop_ap()

# Initialize ESP-NOW
e = espnow.ESPNow()

if P2P_MODE:
    memento = espnow.Peer(mac=MEMENTO_MAC, channel=6)
    e.peers.append(memento)
    d_print("Peer to Peer Mode\nmemento MAC added to peer list")
else:
    peer = espnow.Peer(mac=b'\xff\xff\xff\xff\xff\xff', channel=6)
    e.peers.append(peer)
    d_print("Broadcast Mode")

# Create display main group (will be root group)
main_group = displayio.Group()

# Create background rectangle
background_rect = Rect(0, 0, display.width, display.height, fill=PRUSSIAN_BLUE)
main_group.append(background_rect)

# Create display groups, UI buttons, labels, and graphics
button_label_group = displayio.Group()
main_group.append(button_label_group)

snap_button = Button(
    x=0,  # Start at furthest left
    y=0,  # Start at top
    width=BUTTON_WIDTH,
    height=BUTTON_HEIGHT,
    label="SNAP",
    label_font=terminalio.FONT,
    label_color=BLACK,
    fill_color=UT_ORANGE,
    outline_color=SELECTIVE_YELLOW,
    selected_fill=SELECTIVE_YELLOW,
    selected_outline=SELECTIVE_YELLOW,
    selected_label=BLACK,
    label_scale = 3,
)

focus_button = Button(
    x=0,
    y=BUTTON_HEIGHT,
    width=BUTTON_WIDTH,
    height=BUTTON_HEIGHT,
    label="FOCUS",
    label_font=terminalio.FONT,
    label_color=BLACK,
    fill_color=BLUE_GREEN,
    outline_color=SELECTIVE_YELLOW,
    selected_fill=SELECTIVE_YELLOW,
    selected_outline=SELECTIVE_YELLOW,
    selected_label=BLACK,
    label_scale = 3,
)

ping_button = Button(
    x=0,
    y=BUTTON_HEIGHT * 2,
    width=BUTTON_WIDTH,
    height=BUTTON_HEIGHT,
    label="PING",
    label_font=terminalio.FONT,
    label_color=BLACK,
    fill_color=SKY_BLUE,
    outline_color=SELECTIVE_YELLOW,
    selected_fill=SELECTIVE_YELLOW,
    selected_outline=SELECTIVE_YELLOW,
    selected_label=BLACK,
    label_scale = 3,
)

button_label_group.append(snap_button)
button_label_group.append(ping_button)
button_label_group.append(focus_button)  # middle button on top looks better

signal_group = displayio.Group()
main_group.append(signal_group)

signal_label = label.Label(terminalio.FONT, text=" Signal\nStrength", color=SELECTIVE_YELLOW,
                    background_color=None, padding_left=None,
                    scale=2, anchor_point=(0, 0), anchored_position=(120, 10))
signal_group.append(signal_label)

signal_bar = HorizontalProgressBar(
    (120, 70),
    (100, 40),
    fill_color=PRUSSIAN_BLUE,
    outline_color=SELECTIVE_YELLOW,
    bar_color=UT_ORANGE,
    direction=HorizontalFillDirection.LEFT_TO_RIGHT
)
signal_bar.value = 0
signal_group.append(signal_bar)

receipt_group = displayio.Group()
main_group.append(receipt_group)
receipt_group.hidden = True

receipt_button = Button(
    style=Button.ROUNDRECT,
    x=120,
    y=20,
    width=100,
    height=95,
    label="",
    label_font=terminalio.FONT,
    label_color=BLACK,
    fill_color=SELECTIVE_YELLOW,
    outline_color=SELECTIVE_YELLOW,
    selected_fill=RED,
    selected_outline=TOMATO,
    selected_label=WHITE,
    label_scale = 3,
)

receipt_group.append(receipt_button)

# Show the display
display.root_group = main_group

# Status tracking
status_reset_time = 0
button_reset_time = 0
status_needs_reset = False
button_needs_reset = False
message = None
receipt = None
packet = None
success_count = e.send_success
fail_count = e.send_failure
d_print(f"initial run success counter {success_count}")
d_print(f"initial run fail counter {fail_count}")

while True:
    current_time = time.monotonic()

    D0_event = D0_key.events.get()
    D1D2_event = D1D2_keys.events.get()

    if D0_event:
        if D0_event.pressed:
            message = "snap"
            print(message)
            snap_button.selected = True
            button_reset_time = current_time + 0.75  # Reset after 0.75 seconds
            button_needs_reset = True
    if D1D2_event:
        if D1D2_event.pressed and D1D2_event.key_number == 0:
            message = "focus"
            print(message)
            focus_button.selected = True
            button_reset_time = current_time + 0.75
            button_needs_reset = True
        if D1D2_event.pressed and D1D2_event.key_number == 1:
            message = "ping"
            print(message)
            ping_button.selected = True
            button_reset_time = current_time + 0.75
            button_needs_reset = True

    if message:
        try:
            d_print(f"pre msg send success {e.send_success}")
            d_print(f"pre msg send failure {e.send_failure}")

            e.send(message, memento)
            print(f"Sent: {message}")

            time.sleep(0.05)  # wait a bit for message success receipt, need to test range, works at 0.01 on desk

            d_print(f"post msg send success {e.send_success}")
            d_print(f"post msg send failure {e.send_failure}")

            if e.send_success > success_count:
                # success!
                receipt_button.label = message.upper()
                signal_group.hidden = True
                receipt_group.hidden = False
                status_reset_time = current_time + 0.75  # Reset after 0.75 seconds
                status_needs_reset = True
                success_count = e.send_success

            if e.send_failure > fail_count:
                # fail!
                fail_count = e.send_failure
                raise Exception("fail count advanced")

        except Exception as ex: # pylint: disable=broad-except
            print(f"Send failed: {ex}")
            receipt_button.label = "FAIL"
            signal_bar.value = 0
            receipt_button.selected = True
            signal_group.hidden = True
            receipt_group.hidden = False
            status_reset_time = current_time + 2.0  # Show error for 2 seconds
            status_needs_reset = True

    # Reset status only when needed and after appropriate delay
    if status_needs_reset and current_time >= status_reset_time:
        receipt_group.hidden = True
        signal_group.hidden = False
        receipt_button.text = ""
        receipt_button.selected = False
        status_needs_reset = False
    if button_needs_reset and current_time >= button_reset_time:
        snap_button.selected = False
        focus_button.selected = False
        ping_button.selected = False

    message = None

    # check for received packets
    packet = e.read()
    if packet:
        receipt = packet.msg.decode('utf-8')
        d_print(f"received: {receipt}")
        sig_strength = packet.rssi
        d_print(f"signal strength is {sig_strength}")
        signal_bar.value = map_range(sig_strength, -127, 0, 0, 100)
        d_print(f"signal bar value is {signal_bar.value}")


    packet = None
    receipt = None

    time.sleep(0.05)  # Light polling
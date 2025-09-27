# memento_remote_RX2
# ESP-NOW Memento Camera remote shutter and focus
# 2025 Jean-Paul Lorrain
# MIT License

# SPDX-FileCopyrightText: 2023 Jeff Epler for Adafruit Industries
# SPDX-FileCopyrightText: 2023 Limor Fried for Adafruit Industries

# support for wired remote trigger on pin A0 currently commented out
# JP Lorrain modified source code to use jpl_mycamera as adafruit_pycamera
# jpl_mycamera supports 16 LED RGB neopixel ring and TSL2591 i2c light meter

# SPDX-License-Identifier: Unlicense

""" ESP-NOW bits of code are highlighted by triple quotes """

import os
import time

import supervisor

import bitmaptools
import displayio
import gifio
import ulab.numpy as np

import board
from adafruit_debouncer import Button
from digitalio import DigitalInOut, Direction, Pull

import jpl_mycamera as adafruit_pycamera

""" ESP-NOW imports """
import wifi
import espnow

supervisor.runtime.autoreload = False

""" p2p or broadcast mode """
P2P_MODE = True
print(f"P2P_MODE is {P2P_MODE}")

""" Store Feather S3 or other ESP device MAC address as Hex string
    in settings.toml like this: HEX_S3_MAC = "aa:bb:cc:dd:ee:ff" """
HEX_S3_MAC = os.getenv("HEX_S3_MAC")
print(f"hex mac {HEX_S3_MAC}")

""" Copilot helped write the bytes conversion """
S3_MAC = bytes(int(x,16) for x in HEX_S3_MAC.split(":"))
print(f"byte mac {S3_MAC}")

pycam = adafruit_pycamera.PyCamera()
# pycam.live_preview_mode()

settings = (
    None,
    "resolution",
    "led_level",
    "led_color",
    "mode",
    "timelapse_rate",
    "effect",
)
curr_setting = 0

# wired remote shutter button
# pin = DigitalInOut(board.A0)
# pin.direction = Direction.INPUT
# pin.pull = Pull.UP
# ext_button = Button(pin, long_duration_ms=1000)

""" wifi hack """
wifi.radio.start_ap(" ", "", channel=6, max_connections=0)
wifi.radio.stop_ap()

""" Initialize ESP-NOW """
e = espnow.ESPNow()

""" peer list creation """
if P2P_MODE:
    reverse_s3 = espnow.Peer(mac=S3_MAC, channel=6)
    e.peers.append(reverse_s3)
    print("ESP-NOW Peer to Peer Mode\n Feather S3 Reverse TFT  MAC added to peer list")
else:
    peer = espnow.Peer(mac=b'\xff\xff\xff\xff\xff\xff', channel=6)
    e.peers.append(peer)
    print("ESP-NOW Broadcast Mode")

print("Starting!")
# pycam.tone(200, 0.1)
last_frame = displayio.Bitmap(pycam.camera.width, pycam.camera.height, 65535)
onionskin = displayio.Bitmap(pycam.camera.width, pycam.camera.height, 65535)
timelapse_remaining = None
timelapse_timestamp = None
packet = None
message = None

while True:
    if pycam.mode_text == "STOP" and pycam.stop_motion_frame != 0:
        # alpha blend
        new_frame = pycam.continuous_capture()
        bitmaptools.alphablend(
            onionskin, last_frame, new_frame, displayio.Colorspace.RGB565_SWAPPED
        )
        pycam.blit(onionskin)
    elif pycam.mode_text == "GBOY":
        bitmaptools.dither(
            last_frame, pycam.continuous_capture(), displayio.Colorspace.RGB565_SWAPPED
        )
        pycam.blit(last_frame)
    elif pycam.mode_text == "LAPS":
        if settings[curr_setting] == "timelapse_rate":
            pycam._botbar.y = 245
            pycam._timelapsebar.y = 210
        else:
            pycam._timelapsebar.y = 245
            pycam._botbar.y = 210
        if timelapse_remaining is None:
            pycam.timelapsestatus_label.text = "STOP"
        else:
            timelapse_remaining = timelapse_timestamp - time.time()
            pycam.timelapsestatus_label.text = f"{timelapse_remaining}s /    "
        # Manually updating the label text a second time ensures that the label
        # is re-painted over the blitted preview.
        pycam.timelapse_rate_label.text = pycam.timelapse_rate_label.text
        pycam.timelapse_submode_label.text = pycam.timelapse_submode_label.text

        # only in high power mode do we continuously preview
        if (timelapse_remaining is None) or (
            pycam.timelapse_submode_label.text == "HiPwr"
        ):
            pycam.blit(pycam.continuous_capture())
        if pycam.timelapse_submode_label.text == "LowPwr" and (
            timelapse_remaining is not None
        ):
            pycam.display.brightness = 0.05
        else:
            pycam.display.brightness = 1
        pycam.display.refresh()

        if timelapse_remaining is not None and timelapse_remaining <= 0:
            # no matter what, show what was just on the camera
            pycam.blit(pycam.continuous_capture())
            pycam.tone(200, 0.1) # uncomment to add a beep when a photo is taken
            try:
                pycam.display_message("Snap!", color=0x0000FF)
                pycam.capture_jpeg()
            except TypeError as e:
                pycam.display_message("Failed", color=0xFF0000)
                time.sleep(0.5)
            except RuntimeError as e:
                pycam.display_message("Error\nNo SD Card", color=0xFF0000)
                time.sleep(0.5)
            pycam.live_preview_mode()
            pycam.display.refresh()
            pycam.blit(pycam.continuous_capture())
            timelapse_timestamp = (
                time.time() + pycam.timelapse_rates[pycam.timelapse_rate] + 1
            )
    else:
        pycam.blit(pycam.continuous_capture())
    # print("\t\t", capture_time, blit_time)

    pycam.update_lux()
    pycam.keys_debounce()
    # ext_button.update()

    """ check for incoming packet """
    if e:
        packet = e.read()
        if packet:
            message = packet.msg.decode('utf-8')
            print(f"received: {message}")

    # shutter button long press or
    """ focus message """
    # if pycam.shutter.long_press or ext_button.long_press:
    if pycam.shutter.long_press or message == "focus":
        print("FOCUS")
        print(pycam.autofocus_status)
        pycam.autofocus()
        print(pycam.autofocus_status)

    # shutter button short press or
    """ snap message """
    # if pycam.shutter.short_count or ext_button.short_count:
    if pycam.shutter.short_count or message == "snap":
        print("Shutter released")
        if pycam.mode_text == "STOP":
            pycam.capture_into_bitmap(last_frame)
            pycam.stop_motion_frame += 1
            try:
                pycam.display_message("Snap!", color=0x0000FF)
                pycam.capture_jpeg()
            except TypeError as e:
                pycam.display_message("Failed", color=0xFF0000)
                time.sleep(0.5)
            except RuntimeError as e:
                pycam.display_message("Error\nNo SD Card", color=0xFF0000)
                time.sleep(0.5)
            pycam.live_preview_mode()

        if pycam.mode_text == "GBOY":
            try:
                f = pycam.open_next_image("gif")
            except RuntimeError as e:
                pycam.display_message("Error\nNo SD Card", color=0xFF0000)
                time.sleep(0.5)
                continue

            with gifio.GifWriter(
                f,
                pycam.camera.width,
                pycam.camera.height,
                displayio.Colorspace.RGB565_SWAPPED,
                dither=True,
            ) as g:
                g.add_frame(last_frame, 1)

        if pycam.mode_text == "GIF":
            try:
                f = pycam.open_next_image("gif")
            except RuntimeError as e:
                pycam.display_message("Error\nNo SD Card", color=0xFF0000)
                time.sleep(0.5)
                continue
            i = 0
            ft = []
            pycam._mode_label.text = "REC"  # pylint: disable=protected-access

            pycam.display.refresh()
            with gifio.GifWriter(
                f,
                pycam.camera.width,
                pycam.camera.height,
                displayio.Colorspace.RGB565_SWAPPED,
                dither=True,
            ) as g:
                t00 = t0 = time.monotonic()
                while (i < 15) or not pycam.shutter_button.value:
                    i += 1
                    _gifframe = pycam.continuous_capture()
                    g.add_frame(_gifframe, 0.12)
                    pycam.blit(_gifframe)
                    t1 = time.monotonic()
                    ft.append(1 / (t1 - t0))
                    print(end=".")
                    t0 = t1
            pycam._mode_label.text = "GIF"  # pylint: disable=protected-access
            print(f"\nfinal size {f.tell()} for {i} frames")
            print(f"average framerate {i/(t1-t00)}fps")
            print(f"best {max(ft)} worst {min(ft)} std. deviation {np.std(ft)}")
            f.close()
            pycam.display.refresh()

        if pycam.mode_text == "JPEG":
            pycam.tone(200, 0.1)
            try:
                pycam.display_message("Snap!", color=0x0000FF)
                pycam.capture_jpeg()
                pycam.live_preview_mode()
            except TypeError as e:
                pycam.display_message("Failed", color=0xFF0000)
                time.sleep(0.5)
                pycam.live_preview_mode()
            except RuntimeError as e:
                pycam.display_message("Error\nNo SD Card", color=0xFF0000)
                time.sleep(0.5)

    """ respond to any message (including ping) so remote can read signal strength """
    if message:
        try:
            e.send(message, reverse_s3)
        except Exception as e:
            print(f"ESP-NOW message {message} failed to send to target\n {e}")
        finally:
            packet = None
            message = None

    if pycam.card_detect.fell:
        print("SD card removed")
        pycam.unmount_sd_card()
        pycam.display.refresh()
    if pycam.card_detect.rose:
        print("SD card inserted")
        pycam.display_message("Mounting\nSD Card", color=0xFFFFFF)
        for _ in range(3):
            try:
                print("Mounting card")
                pycam.mount_sd_card()
                print("Success!")
                break
            except OSError as e:
                print("Retrying!", e)
                time.sleep(0.5)
        else:
            pycam.display_message("SD Card\nFailed!", color=0xFF0000)
            time.sleep(0.5)
        pycam.display.refresh()

    if pycam.up.fell:
        print("UP")
        key = settings[curr_setting]
        if key:
            setattr(pycam, key, getattr(pycam, key) + 1)
            print("getting", key, getattr(pycam, key))
    if pycam.down.fell:
        print("DN")
        key = settings[curr_setting]
        if key:
            setattr(pycam, key, getattr(pycam, key) - 1)
            print("getting", key, getattr(pycam, key))
    if pycam.right.fell:
        print("RT")
        curr_setting = (curr_setting + 1) % len(settings)
        if pycam.mode_text != "LAPS" and settings[curr_setting] == "timelapse_rate":
            curr_setting = (curr_setting + 1) % len(settings)
        print(settings[curr_setting])
        # new_res = min(len(pycam.resolutions)-1, pycam.get_resolution()+1)
        # pycam.set_resolution(pycam.resolutions[new_res])
        pycam.select_setting(settings[curr_setting])
    if pycam.left.fell:
        print("LF")
        curr_setting = (curr_setting - 1 + len(settings)) % len(settings)
        if pycam.mode_text != "LAPS" and settings[curr_setting] == "timelapse_rate":
            curr_setting = (curr_setting - 1 + len(settings)) % len(settings)
        print(settings[curr_setting])
        pycam.select_setting(settings[curr_setting])
        # new_res = max(1, pycam.get_resolution()-1)
        # pycam.set_resolution(pycam.resolutions[new_res])
    if pycam.select.fell:
        print("SEL")
        if pycam.mode_text == "LAPS" and settings[curr_setting] == "timelapse_rate":
            pycam.timelapse_submode += 1
            pycam.display.refresh()
    if pycam.ok.fell and settings[curr_setting] == "timelapse_rate":
        print("OK")
        if pycam.mode_text == "LAPS":
            if timelapse_remaining is None:  # stopped
                print("Starting timelapse")
                timelapse_remaining = pycam.timelapse_rates[pycam.timelapse_rate]
                timelapse_timestamp = time.time() + timelapse_remaining + 1
                # dont let the camera take over auto-settings
                saved_settings = pycam.get_camera_autosettings()
                # print(f"Current exposure {saved_settings=}")
                pycam.set_camera_exposure(saved_settings["exposure"])
                pycam.set_camera_gain(saved_settings["gain"])
                pycam.set_camera_wb(saved_settings["wb"])
            else:  # is running, turn off
                print("Stopping timelapse")

                timelapse_remaining = None
                pycam.camera.exposure_ctrl = True
                pycam.set_camera_gain(None)  # go back to autogain
                pycam.set_camera_wb(None)  # go back to autobalance
                pycam.set_camera_exposure(None)  # go back to auto shutter
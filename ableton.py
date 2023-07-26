#!/usr/bin/env python3

# Stemgen for Ableton Live

# Installation:
# `pip install opencv-python`
# Only on macOS: `pip install pyobjc-core`
# Only on macOS: `pip install pyobjc`
# `pip install pyautogui`
# `pip install pylive`
# Also install https://github.com/ideoforms/AbletonOSC as a Remote Script
# Only on Windows: you can install https://github.com/p-groarke/wsay/releases to get audio feedback

# Usage:
# Open Ableton Live
# Open the project you want to export
# Check your export settings and make sure that the export folder is set to "stemgen/input"
# Solo the tracks you want to export as stems
# Run `python3 ableton.py`
# Enter the name of the file
# Don't touch your computer until it's done
# Enjoy your stems!

import os
import platform
import sys
import subprocess
import live
import pyautogui
import time
import logging
from metadata import create_metadata_json, ableton_color_index_to_hex

# Settings
NAME = "track"
IS_RETINA = False
OS = "windows" if platform.system() == "Windows" else "macos"
PYTHON_EXEC = sys.executable if not None else "python3"
STEMS = []

# https://github.com/asweigart/pyautogui/issues/790
if OS == "macos":
    import pyscreeze
    import PIL

    __PIL_TUPLE_VERSION = tuple(int(x) for x in PIL.__version__.split("."))
    pyscreeze.PIL__version__ = __PIL_TUPLE_VERSION


def say(text):
    if OS == "windows":
        os.system("wsay " + text)
    else:
        os.system("say " + text)
    return

# Switch to Ableton Live
def switch_to_ableton():
    print("Looking for Ableton Live...")
    if OS == "windows":
        ableton = pyautogui.getWindowsWithTitle("Ableton Live")[0]
        if ableton != None:
            print("Found it!")
            ableton.activate()
            ableton.maximize()
            return

    pyautogui.keyDown("command")
    pyautogui.press("tab")
    time.sleep(1)
    x, y = pyautogui.locateCenterOnScreen(
        "screenshots/" + OS + "/logo.png", confidence=0.9
    )
    print("Found it!")
    if IS_RETINA == True:
        x = x / 2
        y = y / 2
    pyautogui.moveTo(x, y)
    pyautogui.keyUp("command")
    return


# Get the solo-ed tracks locations
def get_solo_tracks_locations():
    print("Looking for solo-ed tracks...")
    locations = pyautogui.locateAllOnScreen(
        "screenshots/" + OS + "/solo.png", confidence=0.95, grayscale=True
    )
    if locations == None:
        pyautogui.alert("You need to solo the tracks you want to export.")
        exit()
    return locations


# Export a track based on a solo location
def export(set, location, count):
    # Solo the track (if not exporting master)
    if count != 0:
        if IS_RETINA == True:
            x = (location[0] + (location[2] / 2)) / 2
            y = (location[1] + (location[3] / 2)) / 2
        else:
            x = location[0] + location[2]
            y = location[1] + location[3]
        pyautogui.moveTo(x, y)
        pyautogui.click()

        # Get the track name and color
        name = ""
        color = ""
        for track in set.tracks:
            if track.solo:
                print(track.name)
                name = track.name
                color = ableton_color_index_to_hex[track.color_index]
                break

        STEMS.append({"color": color, "name": name})

    # Export the track
    if OS == "windows":
        pyautogui.hotkey("ctrl", "shift", "r")
    else:
        pyautogui.hotkey("command", "shift", "r")
    pyautogui.press("enter")
    time.sleep(1)
    pyautogui.typewrite(NAME + "." + str(count) + ".aif")
    pyautogui.press("enter")

    print("Exporting: " + NAME + "." + str(count) + ".aif")

    # Wait for the export to finish
    time.sleep(1)
    while True:
        location = pyautogui.locateOnScreen(
            "screenshots/" + OS + "/export.png", confidence=0.9
        )
        if location != None:
            print("Exporting...")
        else:
            print("Exported: " + NAME + "." + str(count) + ".aif")
            break

    # Unsolo the track (if not exporting master)
    if count != 0:
        pyautogui.moveTo(x, y)
        pyautogui.click()
    return


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d: %(message)s",
        datefmt="%H:%M:%S",
    )
    print("Welcome to Stemgen for Ableton Live!")

    # Get file name
    global NAME
    NAME = pyautogui.prompt(
        text="Enter the name of the file", title="Stemgen for Ableton Live", default=""
    )

    print("File name: " + NAME)

    # Check Retina Display
    if OS == "macos":
        global IS_RETINA
        if (
            subprocess.call(
                "system_profiler SPDisplaysDataType | grep 'Retina'", shell=True
            )
            == 0
        ):
            IS_RETINA = True
        else:
            IS_RETINA = False
        
        print("Retina Display: " + str(IS_RETINA))

    # Get Ableton Live set
    set = live.Set()
    set.scan(scan_clip_names=True, scan_device=True)
    # TODO: resize all tracks so they all fit on the screen

    switch_to_ableton()
    time.sleep(1)

    locations = list(get_solo_tracks_locations())
    if len(locations) == 0:
        print("You need to solo the tracks or groups you want to export as stems.")
        say("Oops")
        exit()

    if len(locations) < 4:
        print("You need to solo at least 4 tracks or groups.")
        say("Oops")
        exit()

    if len(locations) > 8:
        print("You can't create stems with more than 8 tracks or groups.")
        say("Oops")
        exit()

    print("Found " + str(len(locations)) + " solo-ed tracks.")

    # Unsolo the tracks
    pyautogui.keyDown("command")
    for location in locations:
        if IS_RETINA == True:
            x = (location[0] + (location[2] / 2)) / 2
            y = (location[1] + (location[3] / 2)) / 2
        else:
            x = location[0] + location[2]
            y = location[1] + location[3]
        pyautogui.moveTo(x, y)
        pyautogui.click()
    pyautogui.keyUp("command")

    for track in set.tracks:
        if track.solo:
            track.solo = False

    # Export master
    export(set, location, 0)

    # Export stems
    i = 1
    for location in locations:
        export(set, location, i)
        i += 1

    # Switch to Terminal
    if OS == "windows":
        cmd = pyautogui.getWindowsWithTitle("Command Prompt") or pyautogui.getWindowsWithTitle("Windows PowerShell")
        if cmd[0] != None:
            cmd[0].activate()
    else:
        pyautogui.keyDown("command")
        pyautogui.press("tab")
        pyautogui.keyUp("command")

    # Create metadata.part1.json and metadata.part2.json if double stems
    if len(locations) == 8:
        create_metadata_json(STEMS[:4], "metadata.part1.json")
        create_metadata_json(STEMS[4:], "metadata.part2.json")

    # Create the stem file(s)
    if OS == "windows":
        subprocess.run([
            PYTHON_EXEC,
            "stem.py",
            "-i",
            "input/" + NAME + ".0.aif",
            "-f",
            "aac",
        ])
    else:
        subprocess.run([
            PYTHON_EXEC,
            "stem.py",
            "-i",
            "input/" + NAME + ".0.aif"
        ])

    print("Done! Enjoy :)")
    say("Done")
    return


main()

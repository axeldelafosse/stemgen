#!/usr/bin/env python3

# Stemgen for Ableton Live

# Installation:
# `python3 -m pip install opencv-python`
# Only on macOS: `python3 -m pip install pyobjc-core`
# Only on macOS: `python3 -m pip install pyobjc`
# `python3 -m pip install pyautogui`
# `python3 -m pip install pylive`
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
from pathlib import Path
import platform
import sys
import subprocess
import live
import pyautogui
import time
import logging
from metadata import create_metadata_json, ableton_color_index_to_hex
from shutil import which

# Settings
NAME = "track"
IS_RETINA = False
OS = "windows" if platform.system() == "Windows" else "macos"
PYTHON_EXEC = sys.executable if not None else "python3"
INSTALL_DIR = Path(__file__).parent.absolute()
STEMS = []

# https://github.com/asweigart/pyautogui/issues/790
if OS == "macos":
    import pyscreeze
    import PIL

    __PIL_TUPLE_VERSION = tuple(int(x) for x in PIL.__version__.split("."))
    pyscreeze.PIL__version__ = __PIL_TUPLE_VERSION


def say(text):
    if OS == "windows":
        if which("wsay") is not None:
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
        os.path.join(INSTALL_DIR, "screenshots", OS, "logo.png"), confidence=0.9
    )
    print("Found it!")
    if IS_RETINA == True:
        x = x / 2
        y = y / 2
    pyautogui.moveTo(x, y)
    pyautogui.keyUp("command")
    return


# Export a track based on a solo location
def export(track, position):
    # Solo the track (if not exporting master)
    if position != 0:
        track.solo = True

        # Get the track name and color
        print(track.name)
        name = track.name
        color = ableton_color_index_to_hex[track.color_index]

        STEMS.append({"color": color, "name": name})

    # Export the track
    if OS == "windows":
        pyautogui.hotkey("ctrl", "shift", "r")
    else:
        pyautogui.hotkey("command", "shift", "r")
    pyautogui.press("enter")
    time.sleep(1)
    pyautogui.typewrite(NAME + "." + str(position) + ".aif")
    pyautogui.press("enter")

    print("Exporting: " + NAME + "." + str(position) + ".aif")

    # Wait for the export to finish
    time.sleep(1)
    while True:
        location = pyautogui.locateOnScreen(
            os.path.join(INSTALL_DIR, "screenshots", OS, "export.png"), confidence=0.9
        )
        if location != None:
            print("Exporting...")
        else:
            print("Exported: " + NAME + "." + str(position) + ".aif")
            break

    # Unsolo the track (if not exporting master)
    if position != 0:
        track.solo = False
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
    set = live.Set(scan=True)

    switch_to_ableton()
    time.sleep(1)

    # Get the solo-ed tracks
    soloed_tracks = []

    for track in set.tracks:
        if track.solo:
            soloed_tracks.append(track)

    if len(soloed_tracks) == 0:
        print("You need to solo the tracks or groups you want to export as stems.")
        say("Oops")
        exit()

    if len(soloed_tracks) < 4:
        print("You need to solo at least 4 tracks or groups.")
        say("Oops")
        exit()

    if len(soloed_tracks) > 8:
        print("You can't create stems with more than 8 tracks or groups.")
        say("Oops")
        exit()

    print("Found " + str(len(soloed_tracks)) + " solo-ed tracks.")

    # Delete old files using the same file name in `stemgen/input` folder
    for file in os.listdir(os.path.join(INSTALL_DIR, "input")):
        if file.startswith(NAME):
            os.remove(os.path.join(INSTALL_DIR, "input", file))

    # Unsolo the tracks
    for track in set.tracks:
        if track.solo:
            track.solo = False

    # Export master
    export(soloed_tracks, 0)

    # Check if master was exported in `stemgen/input` folder
    if not os.path.exists(os.path.join(INSTALL_DIR, "input", NAME + ".0.aif")):
        print("You need to set `stemgen/input` as the output folder.")
        say("Oops")
        exit()

    # Export stems
    i = 1
    for soloed_track in soloed_tracks:
        export(soloed_track, i)
        i += 1

    # Switch to Terminal
    if OS == "windows":
        cmd = pyautogui.getWindowsWithTitle(
            "Command Prompt"
        ) or pyautogui.getWindowsWithTitle("Windows PowerShell")
        if cmd[0] != None:
            cmd[0].activate()
    else:
        pyautogui.keyDown("command")
        pyautogui.press("tab")
        pyautogui.keyUp("command")

    # Create metadata.part1.json and metadata.part2.json if double stems
    if len(soloed_tracks) == 8:
        create_metadata_json(
            STEMS[:4], os.path.join(INSTALL_DIR, "metadata.part1.json")
        )
        create_metadata_json(
            STEMS[4:], os.path.join(INSTALL_DIR, "metadata.part2.json")
        )
        print("Created or updated metadata files.")

    # Create the stem file(s)
    if OS == "windows":
        subprocess.run(
            [
                PYTHON_EXEC,
                os.path.join(INSTALL_DIR, "stem.py"),
                "-i",
                os.path.join(INSTALL_DIR, "input", NAME + ".0.aif"),
                "-f",
                "aac",
            ]
        )
    else:
        subprocess.run(
            [
                PYTHON_EXEC,
                os.path.join(INSTALL_DIR, "stem.py"),
                "-i",
                os.path.join(INSTALL_DIR, "input", NAME + ".0.aif"),
            ]
        )

    print("Done! Enjoy :)")
    say("Done")
    return


if __name__ == "__main__":
    os.chdir(INSTALL_DIR)
    main()

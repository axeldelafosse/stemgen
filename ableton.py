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
    # These functions have been moved to ableton_utils.py


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

    switch_to_ableton()
    time.sleep(1)

    # Get the solo-ed tracks locations
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

    # Unsolo the tracks
    for track in set.tracks:
        if track.solo:
            track.solo = False

    # Export master
    export(soloed_tracks, 0)

    # Export stems
    i = 1
    for soloed_track in soloed_tracks:
        export(soloed_track, i)
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
    if len(soloed_tracks) == 8:
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

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
# Check your export settings:
# Make sure that the export folder is set to your Desktop folder
# Make sure that the export format is set to AIFF
# Solo the tracks you want to export as stems
# Run `ableton`
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
from stemgen.metadata import create_metadata_json, ableton_color_index_to_hex
from shutil import which, move
import re

# Optional imports for accessibility APIs
if platform.system() == "Windows":
    try:
        from pywinauto import Application as _PyWinApp
    except Exception:
        _PyWinApp = None
else:
    _PyWinApp = None

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


EXPORT_REGEX = re.compile(r"Export\s+Audio(\.|…|/Video)*", re.IGNORECASE)


def _is_export_in_progress() -> bool:
    """Detects if Ableton's export dialog/sheet is currently visible."""
    if platform.system() == "Windows" and _PyWinApp is not None:
        try:
            return _is_export_dialog_open_windows()
        except Exception:
            pass

    try:
        location = pyautogui.locateOnScreen(
            os.path.join(INSTALL_DIR, "screenshots", OS, "export.png"),
            confidence=0.9,
            grayscale=True,
        )
        return location is not None
    except Exception:
        return False

 


def _is_export_dialog_open_windows() -> bool:
    if _PyWinApp is None:
        return False
    try:
        app = _PyWinApp(backend="uia").connect(title_re=".*Ableton.*", timeout=2.0)
    except Exception:
        return False
    try:
        main = app.window(title_re=".*Ableton.*")
    except Exception:
        return False

    try:
        for ctrl in main.descendants(control_type="Text"):
            name = ""
            try:
                name = ctrl.window_text()
            except Exception:
                try:
                    name = getattr(ctrl.element_info, "name", "") or ""
                except Exception:
                    name = ""
            if name and EXPORT_REGEX.search(name):
                return True
    except Exception:
        pass

    try:
        for dlg in app.windows():
            try:
                if EXPORT_REGEX.search(dlg.window_text()):
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


# Switch to Ableton Live
def switch_to_ableton():
    print("Looking for Ableton Live...")
    if OS == "windows":
        ableton = pyautogui.getWindowsWithTitle("Ableton Live")[0]
        if ableton is not None:
            print("Found it!")
            ableton.activate()
            ableton.maximize()
            return

    pyautogui.keyDown("command")
    pyautogui.press("tab")
    time.sleep(1)
    x, y = pyautogui.locateCenterOnScreen(
        os.path.join(INSTALL_DIR, "screenshots", OS, "logo.png"),
        confidence=0.9,
        grayscale=True,
    )
    print("Found it!")
    if IS_RETINA:
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
    pyautogui.typewrite(NAME + "." + str(position))
    pyautogui.press("enter")

    print("Exporting: " + NAME + "." + str(position) + ".aif")

    # Wait for the export to finish
    time.sleep(1)
    while True:
        try:
            exporting = _is_export_in_progress()
            if exporting:
                print("Exporting...")
            else:
                print("Exported: " + NAME + "." + str(position) + ".aif")
                break
        except Exception:
            # If detection fails for any reason, assume export is done to avoid endless loop
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

    # Delete old files using the same file name on Desktop
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    for file in os.listdir(desktop_path):
        if file.startswith(NAME):
            os.remove(os.path.join(desktop_path, file))

    # Unsolo the tracks
    for track in set.tracks:
        if track.solo:
            track.solo = False

    # Export master
    export(soloed_tracks, 0)

    # Check if master was exported on Desktop
    if not os.path.exists(os.path.join(desktop_path, NAME + ".0.aif")):
        if os.path.exists(os.path.join(desktop_path, NAME + ".0.wav")):
            print("You need to export as AIFF instead of WAV.")
        else:
            print("You need to set your Desktop as the output folder.")
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
        if cmd[0] is not None:
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
                os.path.join(desktop_path, NAME + ".0.aif"),
                "-o",
                os.path.join(desktop_path, "output"),
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
                os.path.join(desktop_path, NAME + ".0.aif"),
                "-o",
                os.path.join(desktop_path, "output"),
            ]
        )

    # Move the stems to the Desktop folder
    for file in os.listdir(os.path.join(desktop_path, "output")):
        if file.startswith(NAME):
            move(os.path.join(desktop_path, "output", file), os.path.join(desktop_path, file))

    print("Done! Enjoy :)")
    say("Done")
    return


if __name__ == "__main__":
    os.chdir(INSTALL_DIR)
    main()

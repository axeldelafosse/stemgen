import os
import platform
import pyautogui
import time
from metadata import ableton_color_index_to_hex

# Settings
NAME = "track"
IS_RETINA = False
OS = "windows" if platform.system() == "Windows" else "macos"
PYTHON_EXEC = sys.executable if not None else "python3"
STEMS = []

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
            "screenshots/" + OS + "/export.png", confidence=0.9
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
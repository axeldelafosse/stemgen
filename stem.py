#!/usr/bin/env python3

import argparse
import os
import shutil
import sys
import subprocess
from pathlib import Path
import json
import unicodedata
from metadata import get_cover, get_metadata

LOGO = r"""
 _____ _____ _____ _____ 
|   __|_   _|   __|     |
|__   | | | |   __| | | |
|_____| |_| |_____|_|_|_|

"""

SUPPORTED_FILES = ['.wave', '.wav', '.aiff', '.aif', '.flac']
REQUIRED_PACKAGES = ['ffmpeg']

USAGE = f"""{LOGO}
Stem is a Stem file creator. Convert your multitrack into a stem (or two) and have fun with Traktor.

Usage: python3 stem.py -i [INPUT_PATH] -o [OUTPUT_PATH]

To create a stem, simply pass the master track in input.
Example: python3 stem.py -i track.0.wav

Supported input file format: {SUPPORTED_FILES}

Naming convention for input files: [TRACK_NAME].[TRACK_NUMBER].[FILE_EXTENSION]
TRACK_NAME should be identical for all files.
Please use 0 as the TRACK_NUMBER for the master file.
Example: 'track.0.wav' for the master file then 'track.1.wav' for the first stem, etc...
"""
VERSION = '1.0.0'

parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-i', dest='INPUT_PATH', required=True,
                    help='the path to the input file')
parser.add_argument('-o', dest='OUTPUT_PATH', default='output',
                    help='the path to the output folder')
parser.add_argument('-f', dest='FORMAT', default='alac',
                    help='aac or alac')
parser.add_argument('-v', '--version', action='version', version=VERSION)
args = parser.parse_args()

INPUT_PATH = args.INPUT_PATH
OUTPUT_PATH = args.OUTPUT_PATH
FORMAT = args.FORMAT
DIR = Path(__file__).parent.absolute()
PYTHON_EXEC = sys.executable if not None else "python3"

# CREATION

def create_stem():
    print("Creating stem...")
    cd_root()

    is_double_stem = False

    # Create another stem if we have more than 4 stems in the folder
    if os.path.exists(f"{INPUT_FOLDER}/{FILE_NAME}.5{FILE_EXTENSION}"):
        is_double_stem = True

    if is_double_stem:
        # Open tags.json and edit the title
        with open(f"{OUTPUT_PATH}/{FILE_NAME}/tags.json", "r+") as f:
            tags = json.load(f)
            tags["title"] = f"{tags['title']} (part 1)"
            f.seek(0)
            json.dump(tags, f)
            f.truncate()

        stem_args = [PYTHON_EXEC, "ni-stem/ni-stem", "create", "-s"]
        stem_args += [f"{INPUT_FOLDER}/{FILE_NAME}.1{FILE_EXTENSION}",
                    f"{INPUT_FOLDER}/{FILE_NAME}.2{FILE_EXTENSION}",
                    f"{INPUT_FOLDER}/{FILE_NAME}.3{FILE_EXTENSION}",
                    f"{INPUT_FOLDER}/{FILE_NAME}.4{FILE_EXTENSION}"]
        stem_args += ["-x", INPUT_PATH, "-t", f"{OUTPUT_PATH}/{FILE_NAME}/tags.json",
                    "-m", "metadata.json", "-f", FORMAT,
                    "-o", f"{OUTPUT_PATH}/{FILE_NAME}/{FILE_NAME} (part 1).stem.m4a"]

        subprocess.run(stem_args)

        # Open tags.json and edit the title (again)
        with open(f"{OUTPUT_PATH}/{FILE_NAME}/tags.json", "r+") as f:
            tags = json.load(f)
            tags["title"] = tags['title'].replace(" (part 1)", " (part 2)")
            f.seek(0)
            json.dump(tags, f)
            f.truncate()

        stem_args = [PYTHON_EXEC, "ni-stem/ni-stem", "create", "-s"]
        stem_args += [f"{INPUT_FOLDER}/{FILE_NAME}.5{FILE_EXTENSION}",
                    f"{INPUT_FOLDER}/{FILE_NAME}.6{FILE_EXTENSION}",
                    f"{INPUT_FOLDER}/{FILE_NAME}.7{FILE_EXTENSION}",
                    f"{INPUT_FOLDER}/{FILE_NAME}.8{FILE_EXTENSION}"]
        stem_args += ["-x", INPUT_PATH, "-t", f"{OUTPUT_PATH}/{FILE_NAME}/tags.json",
                    "-m", "metadata.json", "-f", FORMAT,
                    "-o", f"{OUTPUT_PATH}/{FILE_NAME}/{FILE_NAME} (part 2).stem.m4a"]

        subprocess.run(stem_args)
    else:
        stem_args = [PYTHON_EXEC, "ni-stem/ni-stem", "create", "-s"]
        stem_args += [f"{INPUT_FOLDER}/{FILE_NAME}.1{FILE_EXTENSION}",
                    f"{INPUT_FOLDER}/{FILE_NAME}.2{FILE_EXTENSION}",
                    f"{INPUT_FOLDER}/{FILE_NAME}.3{FILE_EXTENSION}",
                    f"{INPUT_FOLDER}/{FILE_NAME}.4{FILE_EXTENSION}"]
        stem_args += ["-x", INPUT_PATH, "-t", f"{OUTPUT_PATH}/{FILE_NAME}/tags.json",
                    "-m", "metadata.json", "-f", FORMAT,
                    "-o", f"{OUTPUT_PATH}/{FILE_NAME}/{FILE_NAME}.stem.m4a"]

        subprocess.run(stem_args)

    print("Done.")

# SETUP

def cd_root():
    os.chdir(DIR)

def setup():
    for package in REQUIRED_PACKAGES:
        if not shutil.which(package):
            print(f"Please install {package} before running Stem.")
            sys.exit(2)

    if not os.path.exists('ni-stem/ni-stem'):
        print("Please install ni-stem before running Stem.")
        sys.exit(2)

    if not os.path.exists(OUTPUT_PATH):
        os.mkdir(OUTPUT_PATH)
        print("Output dir created.")
    else:
        print("Output dir already exists.")

    global BASE_PATH, FILE_EXTENSION
    BASE_PATH = os.path.basename(INPUT_PATH)
    FILE_EXTENSION = os.path.splitext(BASE_PATH)[1]

    if FILE_EXTENSION not in SUPPORTED_FILES:
        print("Invalid input file format. File should be one of:", SUPPORTED_FILES)
        sys.exit(1)

    setup_file()
    get_cover(FILE_EXTENSION, FILE_PATH, OUTPUT_PATH, FILE_NAME)
    get_metadata(DIR, FILE_PATH, OUTPUT_PATH, FILE_NAME)

    print("Ready!")

def run():
    print(f"Creating a Stem file for {FILE_NAME}...")

    create_stem()
    clean_dir()

    print("Success! Have fun :)")

def strip_accents(text):
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore')
    text = text.decode("utf-8")
    return str(text)

def setup_file():
    global FILE_NAME, INPUT_FOLDER, FILE_PATH
    FILE_NAME = BASE_PATH.removesuffix(FILE_EXTENSION).removesuffix(".0")
    INPUT_FOLDER = os.path.dirname(INPUT_PATH)

    if os.path.exists(f"{OUTPUT_PATH}/{FILE_NAME}"):
        print("Working dir already exists.")
    else:
        os.mkdir(f"{OUTPUT_PATH}/{FILE_NAME}")
        print("Working dir created.")

    shutil.copy(INPUT_PATH, f"{OUTPUT_PATH}/{FILE_NAME}/{FILE_NAME}{FILE_EXTENSION}")
    FILE_PATH = f"{OUTPUT_PATH}/{FILE_NAME}/{FILE_NAME}{FILE_EXTENSION}"
    print("Done.")

def clean_dir():
    print("Cleaning...")

    os.chdir(os.path.join(OUTPUT_PATH, FILE_NAME))
    if os.path.isfile(f"{FILE_NAME}.stem.m4a"):
        os.rename(f"{FILE_NAME}.stem.m4a", os.path.join("..", f"{FILE_NAME}.stem.m4a"))
    if os.path.isfile(f"{FILE_NAME} (part 1).stem.m4a"):
        os.rename(f"{FILE_NAME} (part 1).stem.m4a", os.path.join("..", f"{FILE_NAME} (part 1).stem.m4a"))
        if os.path.isfile(f"{FILE_NAME} (part 2).stem.m4a"):
            os.rename(f"{FILE_NAME} (part 2).stem.m4a", os.path.join("..", f"{FILE_NAME} (part 2).stem.m4a"))
    shutil.rmtree(os.path.join(DIR, OUTPUT_PATH + '/' + FILE_NAME))
    input_dir = os.path.join(DIR, INPUT_FOLDER)
    for file in os.listdir(input_dir):
        if file.endswith(".m4a"):
            os.remove(os.path.join(input_dir, file))

    print("Done.")

cd_root()
setup()
run()

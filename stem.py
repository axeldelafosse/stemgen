#!/usr/bin/env python3

import argparse
import os
import shutil
import sys
import subprocess
from pathlib import Path
import json

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

Usage: {__file__} -i [INPUT_PATH] -o [OUTPUT_PATH]

Supported input file format: {SUPPORTED_FILES}

Naming convention for input files: [TRACK_NAME].[TRACK_NUMBER].[FILE_EXTENSION]
TRACK_NAME should be identical for all files.
Please use 0 as the TRACK_NUMBER for the master file. Example:
'track.0.wav' for the master file then 'track.1.wav' for the first stem, etc...
"""
VERSION = '1.0.0'

parser = argparse.ArgumentParser(description=USAGE)
parser.add_argument('-i', dest='INPUT_PATH', required=True,
                    help='the path to the input file')
parser.add_argument('-o', dest='OUTPUT_PATH', default='output',
                    help='the path to the output folder')
parser.add_argument('-v', '--version', action='version', version=VERSION)
args = parser.parse_args()

INPUT_PATH = args.INPUT_PATH
OUTPUT_PATH = args.OUTPUT_PATH
DIR = Path(__file__).parent.absolute()
PYTHON_EXEC = sys.executable if not None else PYTHON_EXEC

def cd_root():
    os.chdir(DIR)

def get_cover():
    print("Extracting cover...")

    if FILE_EXTENSION in ('.wav', '.wave', '.aif', '.aiff'):
        subprocess.run([PYTHON_EXEC, 'ni-stem/extract_cover_art.py', INPUT_PATH, f"{OUTPUT_PATH}/{FILE_NAME}/cover.jpg"])
        print("Cover extracted from APIC tag.")
    else:
        subprocess.run(['ffmpeg', '-i', INPUT_PATH, '-an', '-vcodec', 'copy', f"{OUTPUT_PATH}/{FILE_NAME}/cover.jpg", '-y'])
        print("Cover extracted with ffmpeg.")

    print("Done.")

def get_metadata():
    print("Extracting metadata...")

    subprocess.run(['ffmpeg', '-i', INPUT_PATH, '-f', 'ffmetadata', f"{OUTPUT_PATH}/{FILE_NAME}/metadata.txt", '-y'])

    # Get label from TPUB tag
    if FILE_EXTENSION in ('.wav', '.wave', '.aif', '.aiff'):
        subprocess.run([PYTHON_EXEC, 'ni-stem/extract_label.py', INPUT_PATH, f"{OUTPUT_PATH}/{FILE_NAME}/metadata.txt"])

    # Get genre from TCON tag
    if FILE_EXTENSION in ('.wav', '.wave', '.aif', '.aiff'):
        subprocess.run([PYTHON_EXEC, 'ni-stem/extract_genre.py', INPUT_PATH, f"{OUTPUT_PATH}/{FILE_NAME}/metadata.txt"])

    # Get URL from WXXX tag
    if FILE_EXTENSION in ('.wav', '.wave', '.aif', '.aiff'):
        subprocess.run([PYTHON_EXEC, 'ni-stem/extract_url.py', INPUT_PATH, f"{OUTPUT_PATH}/{FILE_NAME}/metadata.txt"])

    print("Done.")

def create_tags_json():
    print("Creating tags.json...")

    os.chdir(os.path.join(OUTPUT_PATH, FILE_NAME))

    tags = {}

    # Add metadata, e.g. `artist` `genre`
    with open("metadata.txt", "r") as f:
        metadata = f.read().splitlines()
        title = ""
        value = ""
        for tag in metadata:
            if tag.startswith(";FFMETADATA1"):
                continue
            if "=" not in tag:
                tags[title] += tag
                continue
            title, value = tag.split("=", 1)
            title = title.lower()
            if title in ["title", "style", "artist", "remixer", "release", "album",
                        "mix", "producer", "bpm", "genre", "catalog_no", "track_no",
                        "track_count", "track", "date", "year", "isrc", "publisher",
                        "label", "comment", "description", "url_discogs_artist_site",
                        "url_discogs_release_site", "discogs_release_id",
                        "youtube_id", "beatport_id", "qobuz_id",
                        "copyright", "organization", "www", "album_artist",
                        "initialkey", "key", "barcode", "upc", "lyrics", "mood"]:
                tags[title] = value

    # Add `cover`
    if os.path.exists("cover.jpg"):
        tags["cover"] = (f"{os.path.join(DIR, OUTPUT_PATH + '/' + FILE_NAME + '/cover.jpg')}")

    with open("tags.json", "w") as f:
        json.dump(tags, f)

    with open("tags.json", "r") as f:
        print(f.read())

    os.chdir("../../")

    print("Done.")

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
                    "-m", "metadata.json", "-f", "alac",
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
                    "-m", "metadata.json", "-f", "alac",
                    "-o", f"{OUTPUT_PATH}/{FILE_NAME}/{FILE_NAME} (part 2).stem.m4a"]

        subprocess.run(stem_args)
    else:
        stem_args = [PYTHON_EXEC, "ni-stem/ni-stem", "create", "-s"]
        stem_args += [f"{INPUT_FOLDER}/{FILE_NAME}.1{FILE_EXTENSION}",
                    f"{INPUT_FOLDER}/{FILE_NAME}.2{FILE_EXTENSION}",
                    f"{INPUT_FOLDER}/{FILE_NAME}.3{FILE_EXTENSION}",
                    f"{INPUT_FOLDER}/{FILE_NAME}.4{FILE_EXTENSION}"]
        stem_args += ["-x", INPUT_PATH, "-t", f"{OUTPUT_PATH}/{FILE_NAME}/tags.json",
                    "-m", "metadata.json", "-f", "alac"]

        subprocess.run(stem_args)

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

    print("Ready!")

def setup_file():
    global FILE_NAME, INPUT_FOLDER
    FILE_NAME = BASE_PATH.removesuffix(FILE_EXTENSION).removesuffix(".0")
    INPUT_FOLDER = os.path.dirname(INPUT_PATH)

    if os.path.exists(f"{OUTPUT_PATH}/{FILE_NAME}"):
        print("Working dir already exists.")
    else:
        os.mkdir(f"{OUTPUT_PATH}/{FILE_NAME}")
        print("Working dir created.")

def run():
    print(f"Creating a Stem file for {FILE_NAME}...")

    get_cover()
    get_metadata()
    create_tags_json()
    create_stem()
    clean_dir()

    print("Success! Have fun :)")

cd_root()
setup()
run()

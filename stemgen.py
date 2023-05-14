#!/usr/bin/env python3

import argparse
import os
import shutil
import sys
import subprocess
from pathlib import Path
import json
import unicodedata

LOGO = r"""
 _____ _____ _____ _____ _____ _____ _____ 
|   __|_   _|   __|     |   __|   __|   | |
|__   | | | |   __| | | |  |  |   __| | | |
|_____| |_| |_____|_|_|_|_____|_____|_|___|

"""

SUPPORTED_FILES = ['.wave', '.wav', '.aiff', '.aif', '.flac']
REQUIRED_PACKAGES = ['ffmpeg', 'sox']

USAGE = f"""{LOGO}
Stemgen is a Stem file generator. Convert any track into a stem and have fun with Traktor.

Usage: python3 stemgen.py -i [INPUT_PATH] -o [OUTPUT_PATH]

Supported input file format: {SUPPORTED_FILES}
"""
VERSION = '5.0.0'

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

def cd_root():
    os.chdir(DIR)

def get_cover():
    print("Extracting cover...")

    if FILE_EXTENSION in ('.wav', '.wave', '.aif', '.aiff'):
        subprocess.run([PYTHON_EXEC, 'ni-stem/extract_cover_art.py', FILE_PATH, f"{OUTPUT_PATH}/{FILE_NAME}/cover.jpg"])
        print("Cover extracted from APIC tag.")
    else:
        subprocess.run(['ffmpeg', '-i', FILE_PATH, '-an', '-vcodec', 'copy', f"{OUTPUT_PATH}/{FILE_NAME}/cover.jpg", '-y'])
        print("Cover extracted with ffmpeg.")

    print("Done.")

def get_metadata():
    print("Extracting metadata...")

    subprocess.run(['ffmpeg', '-i', FILE_PATH, '-f', 'ffmetadata', f"{OUTPUT_PATH}/{FILE_NAME}/metadata.txt", '-y'])

    # Get label from TPUB tag
    if FILE_EXTENSION in ('.wav', '.wave', '.aif', '.aiff'):
        subprocess.run([PYTHON_EXEC, 'ni-stem/extract_label.py', FILE_PATH, f"{OUTPUT_PATH}/{FILE_NAME}/metadata.txt"])

    # Get genre from TCON tag
    if FILE_EXTENSION in ('.wav', '.wave', '.aif', '.aiff'):
        subprocess.run([PYTHON_EXEC, 'ni-stem/extract_genre.py', FILE_PATH, f"{OUTPUT_PATH}/{FILE_NAME}/metadata.txt"])

    # Get URL from WXXX tag
    if FILE_EXTENSION in ('.wav', '.wave', '.aif', '.aiff'):
        subprocess.run([PYTHON_EXEC, 'ni-stem/extract_url.py', FILE_PATH, f"{OUTPUT_PATH}/{FILE_NAME}/metadata.txt"])

    print("Done.")

def convert():
    print("Converting to wav and/or downsampling...")

    # We downsample to 44.1kHz to avoid problems with the separation software
    # because the models are trained on 44.1kHz audio files

    # QUALITY            WIDTH  REJ dB   TYPICAL USE
    # -v  very high      95%     175     24-bit mastering

    # -M/-I/-L     Phase response = minimum/intermediate/linear(default)
    # -s           Steep filter (band-width = 99%)
    # -a           Allow aliasing above the pass-band

    global BIT_DEPTH
    global SAMPLE_RATE

    converted_file_path = os.path.join(OUTPUT_PATH, FILE_NAME, FILE_NAME+'.wav')

    if BIT_DEPTH == 32:
        # Downconvert to 24-bit
        if FILE_PATH == converted_file_path:
            subprocess.run(['sox', FILE_PATH, '--show-progress', '-b', '24', os.path.join(OUTPUT_PATH, FILE_NAME, FILE_NAME+'.24bit.wav'), 'rate', '-v', '-a', '-I', '-s', '44100'], check=True)
            os.remove(converted_file_path)
            os.rename(os.path.join(OUTPUT_PATH, FILE_NAME, FILE_NAME+'.24bit.wav'), converted_file_path)
        else:
            subprocess.run(['sox', FILE_PATH, '--show-progress', '-b', '24', converted_file_path, 'rate', '-v', '-a', '-I', '-s', '44100'], check=True)
        BIT_DEPTH = 24
    else:
        if (FILE_EXTENSION == ".wav" or FILE_EXTENSION == ".wave") and SAMPLE_RATE == 44100:
            print("No conversion needed.")
        else:
            if FILE_PATH == converted_file_path:
                subprocess.run(['sox', FILE_PATH, '--show-progress', '--no-dither', os.path.join(OUTPUT_PATH, FILE_NAME, FILE_NAME+'.44100Hz.wav'), 'rate', '-v', '-a', '-I', '-s', '44100'], check=True)
                os.remove(converted_file_path)
                os.rename(os.path.join(OUTPUT_PATH, FILE_NAME, FILE_NAME+'.44100Hz.wav'), converted_file_path)
            else:
                subprocess.run(['sox', FILE_PATH, '--show-progress', '--no-dither', converted_file_path, 'rate', '-v', '-a', '-I', '-s', '44100'], check=True)

    print("Done.")

def get_bit_depth():
    print("Extracting bit depth...")

    global BIT_DEPTH

    if FILE_EXTENSION == '.flac':
        BIT_DEPTH = int(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=bits_per_raw_sample", "-of", "default=noprint_wrappers=1:nokey=1", FILE_PATH]))
    else:
        BIT_DEPTH = int(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=bits_per_sample", "-of", "default=noprint_wrappers=1:nokey=1", FILE_PATH]))

    print(f"bits_per_sample={BIT_DEPTH}")
    print("Done.")

def get_sample_rate():
    print("Extracting sample rate...")

    global SAMPLE_RATE

    SAMPLE_RATE = int(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=sample_rate", "-of", "default=noprint_wrappers=1:nokey=1", FILE_PATH]))

    print(f"sample_rate={SAMPLE_RATE}")
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

def split_stems():
    print("Splitting stems...")

    if BIT_DEPTH == 24:
        print("Using 24-bit model...")
        subprocess.run([PYTHON_EXEC, "-m", "demucs", "--int24", "-n", "htdemucs", "-d", "cpu", FILE_PATH, "-o", f"{OUTPUT_PATH}/{FILE_NAME}"])
    else:
        print("Using 16-bit model...")
        subprocess.run([PYTHON_EXEC, "-m", "demucs", "-n", "htdemucs", "-d", "cpu", FILE_PATH, "-o", f"{OUTPUT_PATH}/{FILE_NAME}"])

    print("Done.")

def create_stem():
    print("Creating stem...")
    cd_root()

    stem_args = [PYTHON_EXEC, "ni-stem/ni-stem", "create", "-s"]
    stem_args += [f"{OUTPUT_PATH}/{FILE_NAME}/htdemucs/{FILE_NAME}/drums.wav",
                  f"{OUTPUT_PATH}/{FILE_NAME}/htdemucs/{FILE_NAME}/bass.wav",
                  f"{OUTPUT_PATH}/{FILE_NAME}/htdemucs/{FILE_NAME}/other.wav",
                  f"{OUTPUT_PATH}/{FILE_NAME}/htdemucs/{FILE_NAME}/vocals.wav"]
    stem_args += ["-x", f"{OUTPUT_PATH}/{FILE_NAME}/{FILE_NAME}.wav", "-t", f"{OUTPUT_PATH}/{FILE_NAME}/tags.json",
                  "-m", "metadata.json", "-f", FORMAT]

    subprocess.run(stem_args)

    print("Done.")

def clean_dir():
    print("Cleaning...")

    os.chdir(os.path.join(OUTPUT_PATH, FILE_NAME))
    if os.path.isfile(f"{FILE_NAME}.stem.m4a"):
        os.rename(f"{FILE_NAME}.stem.m4a", os.path.join("..", f"{FILE_NAME}.stem.m4a"))
    shutil.rmtree(os.path.join(DIR, OUTPUT_PATH + '/' + FILE_NAME))
    input_dir = os.path.join(DIR, INPUT_FOLDER)
    for file in os.listdir(input_dir):
        if file.endswith(".m4a"):
            os.remove(os.path.join(input_dir, file))

    print("Done.")

def setup():
    for package in REQUIRED_PACKAGES:
        if not shutil.which(package):
            print(f"Please install {package} before running Stemgen.")
            sys.exit(2)

    if subprocess.run([PYTHON_EXEC, "-m", "demucs", "-h"], capture_output=True, text=True).stdout.strip() == "":
        print("Please install demucs before running Stemgen.")
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
    get_bit_depth()
    get_sample_rate()
    get_cover()
    get_metadata()
    create_tags_json()
    convert()

    print("Ready!")

def strip_accents(text):
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore')
    text = text.decode("utf-8")
    return str(text)

def setup_file():
    global FILE_NAME, INPUT_FOLDER, FILE_PATH
    FILE_NAME = strip_accents(BASE_PATH.removesuffix(FILE_EXTENSION))
    INPUT_FOLDER = os.path.dirname(INPUT_PATH)

    if os.path.exists(f"{OUTPUT_PATH}/{FILE_NAME}"):
        print("Working dir already exists.")
    else:
        os.mkdir(f"{OUTPUT_PATH}/{FILE_NAME}")
        print("Working dir created.")

    shutil.copy(INPUT_PATH, f"{OUTPUT_PATH}/{FILE_NAME}/{FILE_NAME}{FILE_EXTENSION}")
    FILE_PATH = f"{OUTPUT_PATH}/{FILE_NAME}/{FILE_NAME}{FILE_EXTENSION}"
    print("Done.")

def run():
    print(f"Creating a Stem file for {FILE_NAME}...")

    split_stems()
    create_stem()
    clean_dir()

    print("Success! Have fun :)")

cd_root()
setup()
run()

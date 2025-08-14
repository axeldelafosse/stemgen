#!/usr/bin/env python3

import argparse
import os
import shutil
import sys
import subprocess
from pathlib import Path
import unicodedata
import torch
from stemgen.metadata import get_cover, get_metadata

LOGO = r"""
 _____ _____ _____ _____ _____ _____ _____ 
|   __|_   _|   __|     |   __|   __|   | |
|__   | | | |   __| | | |  |  |   __| | | |
|_____| |_| |_____|_|_|_|_____|_____|_|___|

"""

SUPPORTED_FILES = [".wave", ".wav", ".aiff", ".aif", ".flac"]
REQUIRED_PACKAGES = ["ffmpeg", "sox"]

USAGE = f"""{LOGO}
Stemgen is a Stem file generator. Convert any track into a stem and have fun with Traktor.

Usage: stemgen -i [INPUT_PATH] -o [OUTPUT_PATH]

Supported input file format: {SUPPORTED_FILES}
"""
VERSION = "2.0.8"

# Get the package root directory
PACKAGE_DIR = Path(__file__).parent.absolute()
PROCESS_DIR = os.getcwd()

parser = argparse.ArgumentParser(
    description=USAGE, formatter_class=argparse.RawTextHelpFormatter
)
parser.add_argument(
    dest="POSITIONAL_INPUT_PATH", nargs="?", help="the path to the input file"
)
parser.add_argument(
    "-i", "--input", dest="INPUT_PATH", help="the path to the input file"
)
parser.add_argument(
    "-o",
    "--output",
    dest="OUTPUT_PATH",
    default=(
        "output"
        if str(PACKAGE_DIR) == PROCESS_DIR or PACKAGE_DIR.as_posix() == PROCESS_DIR
        else "."
    ),
    help="the path to the output folder",
)
parser.add_argument("-f", "--format", dest="FORMAT", default="alac", help="aac or alac")
parser.add_argument("-d", "--device", dest="DEVICE", help="cpu or cuda or mps")
parser.add_argument("-v", "--version", action="version", version=VERSION)
parser.add_argument(
    "-n", "--model_name", dest="MODEL_NAME", default="bs_roformer", help="name of the model to use"
)
parser.add_argument(
    "-m", "--model_path", dest="MODEL_PATH", help="path to the model to use"
)
parser.add_argument(
    "-s",
    "--model_shifts",
    dest="MODEL_SHIFTS",
    default="1",
    help="number of shifts for demucs to use",
)
args = parser.parse_args()

INPUT_PATH = args.POSITIONAL_INPUT_PATH or args.INPUT_PATH
OUTPUT_PATH = (
    args.OUTPUT_PATH
    if os.path.isabs(args.OUTPUT_PATH)
    else os.path.join(PROCESS_DIR, args.OUTPUT_PATH)
)
FORMAT = args.FORMAT

# Automatically set DEVICE to "cuda" if CUDA is available or "mps" if Metal is available, otherwise set it to "cpu"
DEVICE = (
    args.DEVICE
    if args.DEVICE is not None
    else (
        "cuda"
        if torch.cuda.is_available()
        else "mps" if torch.backends.mps.is_available() else "cpu"
    )
)

if DEVICE == "cuda":
    print("Using GPU for processing.")
elif DEVICE == "mps":
    print("Using Metal for processing.")
else:
    print("Using CPU for processing.")


PYTHON_EXEC = sys.executable if not None else "python3"

MODEL_NAME = args.MODEL_NAME
MODEL_PATH = args.MODEL_PATH
MODEL_SHIFTS = args.MODEL_SHIFTS

# CONVERSION AND GENERATION


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

    converted_file_path = os.path.join(OUTPUT_PATH, WORKING_DIR, FILE_NAME + ".wav")

    if BIT_DEPTH == 32:
        # Downconvert to 24-bit
        if FILE_PATH == converted_file_path:
            subprocess.run(
                [
                    "sox",
                    FILE_PATH,
                    "--show-progress",
                    "-b",
                    "24",
                    os.path.join(OUTPUT_PATH, WORKING_DIR, FILE_NAME + ".24bit.wav"),
                    "rate",
                    "-v",
                    "-a",
                    "-I",
                    "-s",
                    "44100",
                ],
                check=True,
            )
            os.remove(converted_file_path)
            os.rename(
                os.path.join(OUTPUT_PATH, WORKING_DIR, FILE_NAME + ".24bit.wav"),
                converted_file_path,
            )
        else:
            subprocess.run(
                [
                    "sox",
                    FILE_PATH,
                    "--show-progress",
                    "-b",
                    "24",
                    converted_file_path,
                    "rate",
                    "-v",
                    "-a",
                    "-I",
                    "-s",
                    "44100",
                ],
                check=True,
            )
        BIT_DEPTH = 24
    else:
        if (
            FILE_EXTENSION == ".wav" or FILE_EXTENSION == ".wave"
        ) and SAMPLE_RATE == 44100:
            print("No conversion needed.")
        else:
            if FILE_PATH == converted_file_path:
                subprocess.run(
                    [
                        "sox",
                        FILE_PATH,
                        "--show-progress",
                        "--no-dither",
                        os.path.join(
                            OUTPUT_PATH, WORKING_DIR, FILE_NAME + ".44100Hz.wav"
                        ),
                        "rate",
                        "-v",
                        "-a",
                        "-I",
                        "-s",
                        "44100",
                    ],
                    check=True,
                )
                os.remove(converted_file_path)
                os.rename(
                    os.path.join(OUTPUT_PATH, WORKING_DIR, FILE_NAME + ".44100Hz.wav"),
                    converted_file_path,
                )
            else:
                subprocess.run(
                    [
                        "sox",
                        FILE_PATH,
                        "--show-progress",
                        "--no-dither",
                        converted_file_path,
                        "rate",
                        "-v",
                        "-a",
                        "-I",
                        "-s",
                        "44100",
                    ],
                    check=True,
                )

    print("Done.")


def split_stems():
    print("Splitting stems...")

    if MODEL_NAME == "bs_roformer":
        print("Using BS RoFormer...")
        cmd = [
            PYTHON_EXEC,
            "-m",
            "bs_roformer",
            FILE_PATH,
            "--output_folder",
            OUTPUT_PATH,
            "--pcm_type",
            "PCM_24" if BIT_DEPTH == 24 else "PCM_16",
            "--lossless",
        ]

        if MODEL_PATH:
            print(f"Using specified model: {MODEL_PATH}")
            cmd.append("--start_check_point")
            cmd.append(MODEL_PATH)

        subprocess.run(cmd)

        # Create full directory structure to match Demucs
        os.makedirs(f"{OUTPUT_PATH}/{WORKING_DIR}/{MODEL_NAME}/{FILE_NAME}", exist_ok=True)
        stem_files = ["drums", "bass", "other", "vocals"]
        for stem in stem_files:
            src = f"{OUTPUT_PATH}/{FILE_NAME}_{stem}.wav"
            dst = f"{OUTPUT_PATH}/{WORKING_DIR}/{MODEL_NAME}/{FILE_NAME}/{stem}.wav"
            if os.path.exists(src):
                shutil.move(src, dst)
    else:
        print("Using Demucs...")

        if BIT_DEPTH == 24:
            print("Using 24-bit model...")
            subprocess.run(
                [
                    PYTHON_EXEC,
                    "-m",
                    "demucs",
                    "--int24",
                    "-n",
                    MODEL_NAME,
                    "--shifts",
                    MODEL_SHIFTS,
                    "-d",
                    DEVICE,
                    FILE_PATH,
                    "-o",
                    f"{OUTPUT_PATH}/{FILE_NAME}",
                ]
            )
        else:
            print("Using 16-bit model...")
            subprocess.run(
                [
                    PYTHON_EXEC,
                    "-m",
                    "demucs",
                    "-n",
                    MODEL_NAME,
                    "--shifts",
                    MODEL_SHIFTS,
                    "-d",
                    DEVICE,
                    FILE_PATH,
                    "-o",
                    f"{OUTPUT_PATH}/{FILE_NAME}",
                ]
            )

    print("Done.")


def create_stem():
    print("Creating stem...")
    os.chdir(PACKAGE_DIR)

    stem_args = [PYTHON_EXEC, "ni-stem/ni-stem", "create", "-s"]
    stem_args += [
        f"{OUTPUT_PATH}/{WORKING_DIR}/{MODEL_NAME}/{FILE_NAME}/drums.wav",
        f"{OUTPUT_PATH}/{WORKING_DIR}/{MODEL_NAME}/{FILE_NAME}/bass.wav",
        f"{OUTPUT_PATH}/{WORKING_DIR}/{MODEL_NAME}/{FILE_NAME}/other.wav",
        f"{OUTPUT_PATH}/{WORKING_DIR}/{MODEL_NAME}/{FILE_NAME}/vocals.wav",
    ]
    stem_args += [
        "-x",
        f"{OUTPUT_PATH}/{WORKING_DIR}/{FILE_NAME}.wav",
        "-t",
        f"{OUTPUT_PATH}/{WORKING_DIR}/tags.json",
        "-m",
        "metadata.json",
        "-f",
        FORMAT,
    ]

    subprocess.run(stem_args)

    print("Done.")


# SETUP


def setup():
    for package in REQUIRED_PACKAGES:
        if not shutil.which(package):
            print(f"Please install {package} before running Stemgen.")
            sys.exit(2)

    if not os.path.exists(os.path.join(PACKAGE_DIR, "ni-stem/ni-stem")):
        print("Please install ni-stem before running Stemgen.")
        sys.exit(2)

    if MODEL_NAME == "htdemucs":
        try:
            import demucs
        except ImportError:
            print("Please install demucs before running Stemgen.")
            sys.exit(2)

    if MODEL_NAME == "bs_roformer":
        try:
            import bs_roformer
        except ImportError:
            print("Please install Lossless-BS-RoFormer before running Stemgen.")
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
    get_cover(FILE_EXTENSION, FILE_PATH, OUTPUT_PATH, WORKING_DIR)
    get_metadata(FILE_PATH, OUTPUT_PATH, WORKING_DIR, FILE_NAME)
    convert()

    print("Ready!")


def run():
    print(f"Creating a Stem file for {FILE_NAME}...")

    split_stems()
    create_stem()
    clean_dir()

    print("Success! Have fun :)")


def get_bit_depth():
    print("Extracting bit depth...")

    global BIT_DEPTH

    if FILE_EXTENSION == ".flac":
        BIT_DEPTH = int(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "a",
                    "-show_entries",
                    "stream=bits_per_raw_sample",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    FILE_PATH,
                ]
            )
        )
    else:
        BIT_DEPTH = int(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "a",
                    "-show_entries",
                    "stream=bits_per_sample",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    FILE_PATH,
                ]
            )
        )

    print(f"bits_per_sample={BIT_DEPTH}")
    print("Done.")


def get_sample_rate():
    print("Extracting sample rate...")

    global SAMPLE_RATE

    SAMPLE_RATE = int(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=sample_rate",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                FILE_PATH,
            ]
        )
    )

    print(f"sample_rate={SAMPLE_RATE}")
    print("Done.")


def strip_accents(text):
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore")
    text = text.decode("utf-8")
    return str(text)


def setup_file():
    global FILE_NAME, WORKING_DIR, INPUT_DIR, FILE_PATH
    FILE_NAME = strip_accents(BASE_PATH.removesuffix(FILE_EXTENSION))
    WORKING_DIR = FILE_NAME.replace("[", "_").replace("]", "_")
    INPUT_DIR = os.path.join(PROCESS_DIR, os.path.dirname(INPUT_PATH))

    if os.path.exists(f"{OUTPUT_PATH}/{WORKING_DIR}"):
        print("Working dir already exists.")
    else:
        os.mkdir(f"{OUTPUT_PATH}/{WORKING_DIR}")
        print("Working dir created.")

    shutil.copy(INPUT_PATH, f"{OUTPUT_PATH}/{WORKING_DIR}/{FILE_NAME}{FILE_EXTENSION}")
    FILE_PATH = f"{OUTPUT_PATH}/{WORKING_DIR}/{FILE_NAME}{FILE_EXTENSION}"
    print("Done.")


def clean_dir():
    print("Cleaning...")

    os.chdir(OUTPUT_PATH)

    for file in os.listdir(INPUT_DIR):
        if file.endswith(".m4a"):
            os.remove(os.path.join(INPUT_DIR, file))

    if os.path.isfile(os.path.join(OUTPUT_PATH, WORKING_DIR, f"{FILE_NAME}.stem.m4a")):
        os.rename(
            os.path.join(OUTPUT_PATH, WORKING_DIR, f"{FILE_NAME}.stem.m4a"),
            os.path.join(OUTPUT_PATH, f"{FILE_NAME}.stem.m4a"),
        )

    try:
        shutil.rmtree(os.path.join(OUTPUT_PATH, WORKING_DIR))
    except PermissionError:
        print(
            f"Permission error encountered. Directory {os.path.join(OUTPUT_PATH, WORKING_DIR)} might still be in use."
        )

    print("Done.")


def main():
    setup()
    run()


if __name__ == "__main__":
    os.chdir(PROCESS_DIR)
    main()

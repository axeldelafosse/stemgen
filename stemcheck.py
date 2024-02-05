#!/usr/bin/env python3

# Stemcheck lets you check the integrity of a stem file

# Installation:
# `python3 -m pip install ffmpeg-python`

# Usage:
# `python3 stemcheck.py track.stem.m4a`

import argparse
import subprocess

from stempeg.read import Info, read_stems

from os import path as op
import os


def stemsep(
    stems_file,
    outdir=None,
    extension="aiff",
    idx=None,
    start=None,
    duration=None,
    check=True,
):
    print("Reading stem file...")

    info = Info(stems_file)
    S, sr = read_stems(
        stems_file, stem_id=idx, start=start, duration=duration, check=check
    )

    if check:
        print("Done. Integrity check succeeded!")
        return

    print("Done!")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--version", "-v", action="version", version="1.0.0")

    parser.add_argument("filename", metavar="filename", help="Input STEM file")

    parser.add_argument("--check", action="store_true", help="Run an integrity check")

    args = parser.parse_args()

    stemsep(
        args.filename,
        args.check,
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

# Stemsep lets you split a stem file into multiple files

# Installation:
# `python3 -m pip install ffmpeg-python`
# `python3 -m pip install mutagen`

# Usage:
# `python3 stemsep.py track.stem.m4a`

import argparse
import subprocess

from stempeg.read import Info, read_stems
from stempeg.write import write_stems
from stempeg.write import FilesWriter

from os import path as op
import os


def stemsep(
    stems_file,
    outdir=None,
    extension="aiff",
    idx=None,
    start=None,
    duration=None,
    check=False,
):
    bit_depth = get_bit_depth(stems_file)
    codec = get_codec(extension, bit_depth)

    print("Reading stem file...")

    info = Info(stems_file)
    S, sr = read_stems(
        stems_file, stem_id=idx, start=start, duration=duration, check=check
    )

    if check:
        print("Done. Integrity check succeeded!")
        return

    rootpath, filename = op.split(stems_file)

    basename = op.splitext(filename)[0]
    if ".stem" in basename:
        basename = basename.split(".stem")[0]

    if outdir is not None:
        if not op.exists(outdir):
            os.makedirs(outdir)

        rootpath = outdir

    if len(set(info.title_streams)) == len(info.title_streams):
        # titles contain duplicates
        # lets not use the metadata
        stem_names = info.title_streams
    else:
        stem_names = None

    print("Done.")

    print("Writing stems...")

    write_stems(
        (op.join(rootpath, basename), extension),
        S,
        sample_rate=sr,
        writer=FilesWriter(
            multiprocess=False,
            output_sample_rate=sr,
            stem_names=stem_names,
            codec=codec,
        ),
    )

    print("Done!")

    # TODO: write metadata back to .aiff files using Mutagen


def get_codec(extension, bit_depth):
    print("Getting codec...")

    if extension == ".aiff" or extension == ".aif":
        if bit_depth == 16:
            codec = "pcm_s16be"
        elif bit_depth == 24:
            codec = "pcm_s24be"
        elif bit_depth == 32:
            codec = "pcm_s32be"
        else:
            raise ValueError(f"Unsupported bit depth: {bit_depth}")
    elif extension == ".wav" or extension == ".wave":
        if bit_depth == 16:
            codec = "pcm_s16le"
        elif bit_depth == 24:
            codec = "pcm_s24le"
        elif bit_depth == 32:
            codec = "pcm_s32le"
        else:
            raise ValueError(f"Unsupported bit depth: {bit_depth}")
    else:
        raise ValueError(f"Unsupported extension: {extension}")

    print(f"codec={codec}")
    print("Done.")

    return codec


def get_bit_depth(file_path):
    print("Extracting bit depth...")

    bit_depth = int(
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
                file_path,
            ]
        ).split()[0]
    )

    print(f"bits_per_sample={bit_depth}")
    print("Done.")

    return bit_depth


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--version", "-v", action="version", version="1.0.0")

    parser.add_argument("filename", metavar="filename", help="Input STEM file")

    parser.add_argument("--check", action="store_true", help="Run an integrity check")

    parser.add_argument(
        "--extension",
        metavar="extension",
        type=str,
        default=".aiff",
        help="Output extension",
    )

    parser.add_argument(
        "--id", metavar="id", type=int, nargs="+", help="A list of stem_ids"
    )

    parser.add_argument("-s", type=float, nargs="?", help="start offset in seconds")

    parser.add_argument("-t", type=float, nargs="?", help="read duration")

    parser.add_argument("outdir", metavar="outdir", nargs="?", help="Output folder")

    args = parser.parse_args()

    stemsep(
        args.filename,
        args.outdir,
        args.extension,
        args.id,
        args.s,
        args.t,
        args.check,
    )


if __name__ == "__main__":
    main()

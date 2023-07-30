#!/usr/bin/env python3

# Stemsep lets you split a stem file into multiple files

# Installation:
# `pip install ffmpeg-python`

# Usage:
# `python3 stemsep.py track.stem.m4a`

import argparse

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
):
    info = Info(stems_file)
    S, sr = read_stems(stems_file, stem_id=idx, start=start, duration=duration)

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

    write_stems(
        (op.join(rootpath, basename), extension),
        S,
        sample_rate=sr,
        writer=FilesWriter(
            multiprocess=False, output_sample_rate=sr, stem_names=stem_names
        ),
    )

    # TODO: write metadata back to .aiff files using Mutagen


def cli():
    parser = argparse.ArgumentParser()

    parser.add_argument("--version", "-V", action="version", version="1.0.0")

    parser.add_argument("filename", metavar="filename", help="Input STEM file")

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

    stemsep(args.filename, args.outdir, args.extension, args.id, args.s, args.t)


if __name__ == "__main__":
    cli()

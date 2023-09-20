#!/usr/bin/env python3

# This script lets you match a stem file with its matching master file
# and copy over the metadata from the stem file to the master file

# Installation:
# `python3 -m pip install git+https://github.com/wolkenarchitekt/traktor-nml-utils`
# `python3 -m pip install soundfile`
# `python3 -m pip install pyloudnorm`

import argparse
from traktor_nml_utils import TraktorCollection
from pathlib import Path
import soundfile as sf
import pyloudnorm as pyln
from decimal import Decimal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "collection",
        help="Path to Traktor `collection.nml` file",
        default="collection.nml",
    )
    args = parser.parse_args()

    print("Loading collection.nml...")

    collection = TraktorCollection(path=Path(args.collection))

    print("Loaded!")

    print("Matching...")
    for stem in collection.nml.collection.entry:
        # Check if stem file is locked
        if stem.stems and stem.lock == 1 and stem.artist and stem.title:
            print(stem.location.file)

            # Match stem file with regular file
            for regular in collection.nml.collection.entry:
                if regular.stems:
                    continue

                if (
                    (
                        stem.artist == regular.artist
                        or regular.artist
                        and stem.artist in regular.artist
                    )
                    and stem.title == regular.title
                ) or (
                    stem.location.file.removesuffix(".stem.m4a")
                    == regular.location.file.removesuffix(".wav")
                    or stem.location.file.removesuffix(".stem.m4a")
                    == regular.location.file.removesuffix(".wave")
                    or stem.location.file.removesuffix(".stem.m4a")
                    == regular.location.file.removesuffix(".aif")
                    or stem.location.file.removesuffix(".stem.m4a")
                    == regular.location.file.removesuffix(".aiff")
                    or stem.location.file.removesuffix(".stem.m4a")
                    == regular.location.file.removesuffix(".flac")
                    or stem.location.file.removesuffix(".stem.m4a")
                    == regular.location.file.removesuffix(".mp3")
                    or stem.location.file.removesuffix(".stem.mp4")
                    == regular.location.file.removesuffix(".wav")
                    or stem.location.file.removesuffix(".stem.mp4")
                    == regular.location.file.removesuffix(".wave")
                    or stem.location.file.removesuffix(".stem.mp4")
                    == regular.location.file.removesuffix(".aif")
                    or stem.location.file.removesuffix(".stem.mp4")
                    == regular.location.file.removesuffix(".aiff")
                    or stem.location.file.removesuffix(".stem.mp4")
                    == regular.location.file.removesuffix(".flac")
                    or stem.location.file.removesuffix(".stem.mp4")
                    == regular.location.file.removesuffix(".mp3")
                ):
                    print("--> " + regular.location.file)

                    # Write the integrated LUFS to "Comment" (info.comment)
                    try:
                        if (
                            regular.info.comment is None
                            or not regular.info.comment.startswith("LUFS:")
                        ):
                            # TODO: Windows support
                            data, rate = sf.read(
                                "/Volumes/"
                                + regular.location.volume
                                + regular.location.dir.replace(":", "")
                                + regular.location.file
                            )  # load audio (with shape (samples, channels))
                            meter = pyln.Meter(rate)  # create BS.1770 meter
                            loudness = meter.integrated_loudness(
                                data
                            )  # measure loudness
                            lufs = "LUFS: " + str(
                                Decimal(str(loudness)).quantize(Decimal("1.00"))
                            )
                            print(lufs)
                            regular.info.comment = lufs
                            stem.info.comment = lufs
                    except Exception as e:
                        print(e)

                    # Write the open key to "Key Text" (info.key)
                    musical_key_to_open_key = {
                        21: "1m",
                        16: "2m",
                        23: "3m",
                        18: "4m",
                        13: "5m",
                        20: "6m",
                        15: "7m",
                        22: "8m",
                        17: "9m",
                        12: "10m",
                        19: "11m",
                        14: "12m",
                        0: "1d",
                        7: "2d",
                        2: "3d",
                        9: "4d",
                        4: "5d",
                        11: "6d",
                        6: "7d",
                        1: "8d",
                        8: "9d",
                        3: "10d",
                        10: "11d",
                        5: "12d",
                    }
                    open_key = musical_key_to_open_key[stem.musical_key.value_attribute]
                    regular.info.key = open_key
                    stem.info.key = open_key

                    # Copy from stem file to regular file
                    if stem.cue_v2:
                        regular.cue_v2 = stem.cue_v2
                    if stem.title:
                        regular.title = stem.title
                    if stem.artist:
                        regular.artist = stem.artist
                    if stem.album:
                        regular.album = stem.album
                    if stem.tempo:
                        regular.tempo = stem.tempo
                    if stem.musical_key:
                        regular.musical_key = stem.musical_key
                    if stem.info.color:
                        regular.info.color = stem.info.color
                    if stem.info.genre:
                        regular.info.genre = stem.info.genre
                    if stem.info.label:
                        regular.info.label = stem.info.label
                    if stem.info.playcount:
                        regular.info.playcount = stem.info.playcount
                    if stem.info.last_played:
                        regular.info.last_played = stem.info.last_played

                    regular.lock = 1
                    regular.lock_modification_time = stem.lock_modification_time

                    print("OK")

                    break

            print("\n")

    print("Done.")
    print("Saving...")
    collection.save()
    print("Done.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

# Use this script to match the metadata of your double stems by copying
# the metadata from the first part to the second part

# Install `trakor-nml-utils`:
# `pip install git+https://github.com/wolkenarchitekt/traktor-nml-utils`

# They need to follow this naming convention:
# "Artist - Title (Version) [part 1].stem.m4a"
# "Artist - Title (Version) [part 2].stem.m4a"
# where everything before "[part 1]" or "[part 2]" is the same for both files

# First, you need to make sure that the [part1] is correctly analyzed in Traktor
# Then you can run this script:
# `python3 stemcopy.py /Users/Shared/Traktor/collection.nml`
# where `collection.nml` is the path to your Traktor collection file, e.g.

# Please make sure to make a backup of your `collection.nml` file first!

import argparse
from traktor_nml_utils import TraktorCollection
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument(
    "collection",
    help="Path to Traktor `collection.nml` file",
    default="collection.nml",
)
args = parser.parse_args()

collection = TraktorCollection(path=Path(args.collection))

for part1 in collection.nml.collection.entry:
    # Check if part 1 of stem file
    if part1.stems and (
        part1.location.file.endswith("[part 1].stem.m4a")
        or part1.location.file.endswith("[part 1].stem.mp4")
    ):
        print(part1.location.file)

        # Match part 1 with part 2
        for part2 in collection.nml.collection.entry:
            if (
                part2.stems
                and (
                    part2.location.file.endswith("[part 2].stem.m4a")
                    or part2.location.file.endswith("[part 2].stem.mp4")
                )
                and (
                    part1.location.file.removesuffix("[part 1].stem.m4a")
                    == part2.location.file.removesuffix("[part 2].stem.m4a")
                    or part1.location.file.removesuffix("[part 1].stem.mp4")
                    == part2.location.file.removesuffix("[part 2].stem.mp4")
                )
            ):
                print(part2.location.file)

                if part1.cue_v2:
                    part2.cue_v2 = part1.cue_v2
                if part1.tempo:
                    part2.tempo = part1.tempo
                if part1.musical_key:
                    part2.musical_key = part1.musical_key
                if part1.info.genre:
                    part2.info.genre = part1.info.genre
                if part1.info.label:
                    part2.info.label = part1.info.label
                if part1.info.playcount:
                    part2.info.playcount = part1.info.playcount
                if part1.info.last_played:
                    part2.info.last_played = part1.info.last_played
                if part1.info.color:
                    part2.info.color = part1.info.color

                part1.lock = 1
                part2.lock = 1

                print("OK")
                break

        print("\n")

collection.save()
print("Done.")

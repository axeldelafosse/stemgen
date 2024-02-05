#!/usr/bin/env python3

# Install `traktor-nml-utils`:
# `python3 -m pip install git+https://github.com/wolkenarchitekt/traktor-nml-utils`

# Usage:
# `python3 playlists.py /Users/Shared/Traktor/History/history_2023y09m16d_01h29m12s.nml`

# TODO: export playlist to .m3u from history.nml
# TODO: export playlist(s) to .m3u from collection.nml

import argparse
from traktor_nml_utils import TraktorCollection
from pathlib import Path


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

    for track in collection.nml.collection.entry:
        print(track.title)

    print("Done.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

# Install `traktor-nml-utils`:
# `python3 -m pip install git+https://github.com/wolkenarchitekt/traktor-nml-utils`

# Usage:
# `python3 history.py /Users/Shared/Traktor/History/history_2023y09m16d_01h29m12s.nml`

import argparse
from traktor_nml_utils import TraktorHistory
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "history",
        help="Path to Traktor `history.nml` file",
        default="history.nml",
    )
    args = parser.parse_args()

    # Open `history.nml` and remove `<INDEXING></INDEXING>`
    with open(args.history, "r") as f:
        lines = f.readlines()
    with open(args.history, "w") as f:
        for line in lines:
            if line.strip("\n") != "<INDEXING></INDEXING>":
                f.write(line)

    history = TraktorHistory(path=Path(args.history))

    for trackInHistory in history.nml.playlists.node.subnodes.node.playlist.entry:
        # print(trackInHistory.primarykey.key)
        for trackInCollection in history.nml.collection.entry:
            # print(trackInCollection.location.dir)
            if trackInCollection.location.dir in trackInHistory.primarykey.key:
                if trackInCollection.artist and trackInCollection.title:
                    print(
                        "".join(
                            [
                                trackInCollection.artist,
                                " - ",
                                trackInCollection.title,
                                # " - " if trackInCollection.info.label else "",
                                # trackInCollection.info.label
                                # if trackInCollection.info.label
                                # else "",
                            ]
                        )
                    )
                else:
                    print(trackInCollection.title)


if __name__ == "__main__":
    main()

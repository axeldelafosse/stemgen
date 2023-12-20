#!/usr/bin/env python3

# Install `traktor-nml-utils`:
# `python3 -m pip install git+https://github.com/wolkenarchitekt/traktor-nml-utils`

# Usage:
# `python3 collection.py /Users/Shared/Traktor/collection.nml`

import argparse
from traktor_nml_utils import TraktorCollection
from pathlib import Path
import csv
import json


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

    musical_key_to_key = {
        21: "Am",
        16: "Em",
        23: "Bm",
        18: "Gbm",
        13: "Dbm",
        20: "Abm",
        15: "Ebm",
        22: "Bbm",
        17: "Fm",
        12: "Cm",
        19: "Gm",
        14: "Dm",
        0: "C",
        7: "G",
        2: "D",
        9: "A",
        4: "E",
        11: "B",
        6: "Gb",
        1: "Db",
        8: "Ab",
        3: "Eb",
        10: "Bb",
        5: "F",
        -1: "",
    }

    data = [
        [
            "artist",
            "title",
            "remixer",
            "album",
            "label",
            "tempo",
            "key",
            "playcount",
            "comment",
            "genre",
            "last_played",
            "import_date",
            "catalog_no",
        ]
    ]

    for track in collection.nml.collection.entry:
        data.append(
            [
                track.artist or "",
                track.title or "",
                track.info.remixer or "",
                track.album.title if track.album else "",
                track.info.label or "",
                track.tempo.bpm if track.tempo else "",
                musical_key_to_key[
                    track.musical_key.value_attribute if track.musical_key else -1
                ],
                str(track.info.playcount or ""),
                track.info.comment or "",
                track.info.genre or "",
                track.info.last_played or "",
                track.info.import_date or "",
                track.info.catalog_no or "",
            ]
        )

    with open("collection.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(data)

    with open("collection.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print("Done.")


if __name__ == "__main__":
    main()

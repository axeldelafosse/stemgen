#!/usr/bin/env python3

import os
import sys
import subprocess
import json

sys.path.append(os.path.abspath("ni-stem/mutagen"))
import mutagen


def get_cover(FILE_EXTENSION, FILE_PATH, OUTPUT_PATH, FILE_NAME):
    print("Extracting cover...")

    if FILE_EXTENSION in (".wav", ".wave", ".aif", ".aiff"):
        # Open the file
        file = mutagen.File(FILE_PATH)

        # Check if the file contains any cover art
        if "APIC:" in file:
            # Extract the cover art
            cover = file["APIC:"].data

            # Save the cover art to a file
            with open(f"{OUTPUT_PATH}/{FILE_NAME}/cover.jpg", "wb") as f:
                f.write(cover)
                print("Cover extracted from APIC tag.")
        else:
            print("Error: The file does not contain any cover art.")
    else:
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                FILE_PATH,
                "-an",
                "-vcodec",
                "copy",
                f"{OUTPUT_PATH}/{FILE_NAME}/cover.jpg",
                "-y",
            ]
        )
        print("Cover extracted with ffmpeg.")

    print("Done.")


def get_metadata(FILE_PATH, OUTPUT_PATH, FILE_NAME):
    print("Extracting metadata...")

    # Extract metadata with mutagen
    file = mutagen.File(FILE_PATH)
    if file.tags is not None:
        print(file.tags.pprint())

    TAGS = {}

    # `title`
    if "TIT2" in file:
        TAGS["title"] = file["TIT2"].text[0]
    elif "TITLE" in file:
        TAGS["title"] = file["TITLE"][0]
    else:
        TAGS["title"] = FILE_NAME

    # `artist`
    if "TPE1" in file:
        TAGS["artist"] = file["TPE1"].text[0]
    if "ARTIST" in file:
        TAGS["artist"] = file["ARTIST"][0]

    # `album`
    if "TALB" in file:
        TAGS["album"] = file["TALB"].text[0]
    if "ALBUM" in file:
        TAGS["album"] = file["ALBUM"][0]

    # `label`
    if "TPUB" in file:
        TAGS["label"] = file["TPUB"].text[0]
    if "ORGANIZATION" in file:
        TAGS["label"] = file["ORGANIZATION"][0]
    if "LABEL" in file:
        TAGS["label"] = file["LABEL"][0]

    # `genre`
    if "TCON" in file:
        TAGS["genre"] = file["TCON"].text[0]
    if "GENRE" in file:
        TAGS["genre"] = file["GENRE"][0]

    # `url`
    if "WXXX:" in file:
        TAGS["www"] = file["WXXX:"].url
    if "WWW" in file:
        TAGS["www"] = file["WWW"][0]

    # `year` / `date`
    if "TDRC" in file:
        TAGS["year"] = str(file["TDRC"].text[0])
    if "DATE" in file:
        TAGS["year"] = file["DATE"][0]

    # `track`
    if "TRCK" in file:
        TAGS["track_no"] = file["TRCK"].text[0]
    if "TRACKNUMBER" in file:
        TAGS["track_no"] = file["TRACKNUMBER"][0]

    # `track_count`
    if "TOTALTRACKS" in file:
        TAGS["track_count"] = file["TOTALTRACKS"][0]

    # `bpm`
    if "TBPM" in file:
        TAGS["bpm"] = file["TBPM"].text[0]
    if "BPM" in file:
        TAGS["bpm"] = file["BPM"][0]

    # `key`
    if "TKEY" in file:
        TAGS["key"] = file["TKEY"].text[0]
    if "KEY" in file:
        TAGS["key"] = file["KEY"][0]

    # `initialkey`
    if "TKEY" in file:
        TAGS["initialkey"] = file["TKEY"].text[0]
    if "INITIALKEY" in file:
        TAGS["initialkey"] = file["INITIALKEY"][0]

    # `remixer`
    if "TPE4" in file:
        TAGS["remixer"] = file["TPE4"].text[0]
    if "REMIXER" in file:
        TAGS["remixer"] = file["REMIXER"][0]

    # `mix`
    if "TXXX:MIX" in file:
        TAGS["mix"] = file["TXXX:MIX"].text[0]
    if "MIX" in file:
        TAGS["mix"] = file["MIX"][0]

    # `producer`
    if "TXXX:PRODUCER" in file:
        TAGS["producer"] = file["TXXX:PRODUCER"].text[0]
    if "PRODUCER" in file:
        TAGS["producer"] = file["PRODUCER"][0]

    # `catalog_no`
    if "TXXX:CATALOGNUMBER" in file:
        TAGS["catalog_no"] = file["TXXX:CATALOGNUMBER"].text[0]
    if "CATALOGNUMBER" in file:
        TAGS["catalog_no"] = file["CATALOGNUMBER"][0]

    # `discogs_release_id`
    if "TXXX:DISCOGS_RELEASE_ID" in file:
        TAGS["discogs_release_id"] = file["TXXX:DISCOGS_RELEASE_ID"].text[0]
    if "DISCOGS_RELEASE_ID" in file:
        TAGS["discogs_release_id"] = file["DISCOGS_RELEASE_ID"][0]

    # `url_discogs_release_site`
    if "WXXX:DISCOGS_RELEASE_SITE" in file:
        TAGS["url_discogs_release_site"] = file["WXXX:DISCOGS_RELEASE_SITE"].text[0]
    if "URL_DISCOGS_RELEASE_SITE" in file:
        TAGS["url_discogs_release_site"] = file["URL_DISCOGS_RELEASE_SITE"][0]

    # `url_discogs_artist_site`
    if "WXXX:DISCOGS_ARTIST_SITE" in file:
        TAGS["url_discogs_artist_site"] = file["WXXX:DISCOGS_ARTIST_SITE"].text[0]
    if "URL_DISCOGS_ARTIST_SITE" in file:
        TAGS["url_discogs_artist_site"] = file["URL_DISCOGS_ARTIST_SITE"][0]

    # `youtube_id`
    if "TXXX:YOUTUBE_ID" in file:
        TAGS["youtube_id"] = file["TXXX:YOUTUBE_ID"].text[0]
    if "YOUTUBE_ID" in file:
        TAGS["youtube_id"] = file["YOUTUBE_ID"][0]

    # `beatport_id`
    if "TXXX:BEATPORT_ID" in file:
        TAGS["beatport_id"] = file["TXXX:BEATPORT_ID"].text[0]
    if "BEATPORT_ID" in file:
        TAGS["beatport_id"] = file["BEATPORT_ID"][0]

    # `qobuz_id`
    if "TXXX:QOBUZ_ID" in file:
        TAGS["qobuz_id"] = file["TXXX:QOBUZ_ID"].text[0]
    if "QOBUZ_ID" in file:
        TAGS["qobuz_id"] = file["QOBUZ_ID"][0]

    # `lyrics`
    if "USLT" in file:
        TAGS["lyrics"] = file["USLT"].text[0]
    if "LYRICS" in file:
        TAGS["lyrics"] = file["LYRICS"][0]

    # `mood`
    if "TXXX:MOOD" in file:
        TAGS["mood"] = file["TXXX:MOOD"].text[0]
    if "MOOD" in file:
        TAGS["mood"] = file["MOOD"][0]

    # `comment`
    if "COMM" in file:
        TAGS["comment"] = file["COMM"].text[0]
    if "COMMENT" in file:
        TAGS["comment"] = file["COMMENT"][0]

    # `description`
    if "TXXX:DESCRIPTION" in file:
        TAGS["description"] = file["TXXX:DESCRIPTION"].text[0]
    if "DESCRIPTION" in file:
        TAGS["description"] = file["DESCRIPTION"][0]

    # `barcode`
    if "TXXX:BARCODE" in file:
        TAGS["barcode"] = file["TXXX:BARCODE"].text[0]
    if "BARCODE" in file:
        TAGS["barcode"] = file["BARCODE"][0]

    # `upc`
    if "TXXX:UPC" in file:
        TAGS["upc"] = file["TXXX:UPC"].text[0]
    if "UPC" in file:
        TAGS["upc"] = file["UPC"][0]

    # `isrc`
    if "TSRC" in file:
        TAGS["isrc"] = file["TSRC"].text[0]
    if "ISRC" in file:
        TAGS["isrc"] = file["ISRC"][0]

    # `www`
    if "TXXX:WWW" in file:
        TAGS["www"] = file["TXXX:WWW"].text[0]
    if "WWW" in file:
        TAGS["www"] = file["WWW"][0]

    # `album_artist`
    if "TPE2" in file:
        TAGS["album_artist"] = file["TPE2"].text[0]
    if "ALBUMARTIST" in file:
        TAGS["album_artist"] = file["ALBUMARTIST"][0]

    # `style`
    if "TXXX:STYLE" in file:
        TAGS["style"] = file["TXXX:STYLE"].text[0]
    if "STYLE" in file:
        TAGS["style"] = file["STYLE"][0]

    # `track`
    if "TPOS" in file:
        TAGS["track"] = file["TPOS"].text[0]

    # `copyright`
    if "TCOP" in file:
        TAGS["copyright"] = file["TCOP"].text[0]
    if "COPYRIGHT" in file:
        TAGS["copyright"] = file["COPYRIGHT"][0]

    # `media`
    if "TMED" in file:
        TAGS["media"] = file["TMED"].text[0]
    if "MEDIATYPE" in file:
        TAGS["media"] = file["MEDIATYPE"][0]

    # `country`
    if "TXXX:COUNTRY" in file:
        TAGS["country"] = file["TXXX:COUNTRY"].text[0]
    if "COUNTRY" in file:
        TAGS["country"] = file["COUNTRY"][0]

    # `cover`
    if os.path.exists(os.path.join(OUTPUT_PATH, FILE_NAME, "cover.jpg")):
        TAGS["cover"] = f"{os.path.join(OUTPUT_PATH, FILE_NAME, 'cover.jpg')}"

    print(TAGS)

    print("Creating tags.json...")

    with open(os.path.join(OUTPUT_PATH, FILE_NAME, "tags.json"), "w") as f:
        json.dump(TAGS, f)

    print("Done.")


def create_metadata_json(stems, path):
    print(stems)

    metadata = {
        "mastering_dsp": {
            "compressor": {
                "enabled": False,
                "ratio": 3,
                "output_gain": 0.5,
                "release": 0.300000011920929,
                "attack": 0.003000000026077032,
                "input_gain": 0.5,
                "threshold": 0,
                "hp_cutoff": 300,
                "dry_wet": 50,
            },
            "limiter": {
                "enabled": False,
                "release": 0.05000000074505806,
                "threshold": 0,
                "ceiling": -0.3499999940395355,
            },
        },
        "version": 1,
        "stems": stems,
    }

    with open(path, "w") as f:
        json.dump(metadata, f)


ableton_color_index_to_hex = {
    0: "#F099A7",
    1: "#F2A948",
    2: "#C49B40",
    3: "#F7F48D",
    4: "#CBF94F",
    5: "#77FB58",
    6: "#79FBAF",
    7: "#8DFCE8",
    8: "#97C3FA",
    9: "#5E7FDD",
    10: "#96A6F9",
    11: "#CA72DE",
    12: "#D45D9E",
    13: "#FFFFFF",
    14: "#EB4A41",
    15: "#E5742E",
    16: "#937451",
    17: "#FCF15E",
    18: "#A5FC7C",
    19: "#67C039",
    20: "#56BCAF",
    21: "#6DE6FC",
    22: "#4BA1E8",
    23: "#367BBB",
    24: "#836DDD",
    25: "#AD7AC1",
    26: "#EB4CCE",
    27: "#D0D0D0",
    28: "#D36E60",
    29: "#F2A77C",
    30: "#CDAE79",
    31: "#F0FEB7",
    32: "#D5E3A0",
    33: "#BECF7F",
    34: "#A3C392",
    35: "#DCFCE3",
    36: "#D4F0F7",
    37: "#BBC1E0",
    38: "#CABCE1",
    39: "#AA99E0",
    40: "#E3DCE1",
    41: "#A9A9A9",
    42: "#BE948D",
    43: "#AF845D",
    44: "#95846D",
    45: "#BEBA74",
    46: "#ABBD3B",
    47: "#88AF5A",
    48: "#94C0BA",
    49: "#A0B2C2",
    50: "#8BA4BF",
    51: "#8693C7",
    52: "#A296B3",
    53: "#BAA0BC",
    54: "#B27595",
    55: "#7B7B7B",
    56: "#A13D38",
    57: "#9E5639",
    58: "#6D5043",
    59: "#D7C440",
    60: "#889637",
    61: "#669D42",
    62: "#469A8E",
    63: "#356281",
    64: "#1F2E90",
    65: "#37519D",
    66: "#5E4CA7",
    67: "#9850A8",
    68: "#BC3D6D",
    69: "#3C3C3C",
}

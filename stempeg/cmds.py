import re
import subprocess as sp
import logging

FFMPEG_PATH = None
FFPROBE_PATH = None
MP4BOX_PATH = None


def find_cmd(cmd):
    try:
        from shutil import which

        return which(cmd)
    except ImportError:
        import os

        for path in os.environ["PATH"].split(os.pathsep):
            if os.access(os.path.join(path, cmd), os.X_OK):
                return path

    return None


def ffmpeg_and_ffprobe_exists():
    global FFMPEG_PATH, FFPROBE_PATH
    if FFMPEG_PATH is None:
        FFMPEG_PATH = find_cmd("ffmpeg")

    if FFPROBE_PATH is None:
        FFPROBE_PATH = find_cmd("ffprobe")

    return FFMPEG_PATH is not None and FFPROBE_PATH is not None


def mp4box_exists():
    global MP4BOX_PATH
    if MP4BOX_PATH is None:
        MP4BOX_PATH = find_cmd("MP4Box")

    return MP4BOX_PATH is not None


if not ffmpeg_and_ffprobe_exists():
    raise RuntimeError(
        "ffmpeg or ffprobe could not be found! "
        "Please install them before using stempeg. "
        "See: https://github.com/faroit/stempeg"
    )


def check_available_aac_encoders():
    """Returns the available AAC encoders

    Returns:
        list(str): List of available encoder codecs from ffmpeg

    """
    cmd = [FFMPEG_PATH, "-v", "error", "-codecs"]

    output = sp.check_output(cmd)
    aac_codecs = [
        x for x in output.splitlines() if "AAC (Advanced Audio Coding)" in str(x)
    ][0]
    hay = aac_codecs.decode("ascii")
    match = re.findall(r"\(encoders: ([^\)]*) \)", hay)
    if match:
        return match[0].split(" ")
    else:
        return None


def get_aac_codec():
    """Checks codec and warns if `libfdk_aac` codec
     is not available.

    Returns:
        str: ffmpeg aac codec name
    """
    avail = check_available_aac_encoders()
    if avail is not None:
        if "libfdk_aac" in avail:
            codec = "libfdk_aac"
        else:
            logging.warning("For the better audio quality, install `libfdk_aac` codec.")
            codec = "aac"
    else:
        codec = "aac"

    return codec

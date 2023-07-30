"""
Stempeg is a Python package to read and write [STEM](https://www.native-instruments.com/en/specials/stems/) files.
Technically, stems are audio containers that combine multiple audio streams and metadata in a single audio file. This makes it ideal to playback multitrack audio, where users can select the audio sub-stream during playback (e.g. supported by VLC). 

Under the hood, _stempeg_ uses [ffmpeg](https://www.ffmpeg.org/) for reading and writing multistream audio, optionally [MP4Box](https://github.com/gpac/gpac) is used to create STEM files that are compatible with Native Instruments hardware and software.

- `stempeg.read`: reading audio tensors and metadata.
- `stempeg.write`: writing audio tensors.

![stempeg_scheme](https://user-images.githubusercontent.com/72940/102477776-16960a00-405d-11eb-9389-1ea9263cf99d.png)

Please checkout [the Github repository](https://github.com/faroit/stempeg) for more information.
"""

from .read import read_stems
from .read import Info
from .read import StreamsReader, ChannelsReader
from .write import write_stems
from .write import write_audio
from .write import FilesWriter, StreamsWriter, ChannelsWriter, NIStemsWriter
from .cmds import check_available_aac_encoders

import re
import subprocess as sp
import pkg_resources

__version__ = "1.0.0"


def default_metadata():
    """Get the path to included stems metadata.

    Returns
    -------
    filename : str
        Path to the json file
    """
    return pkg_resources.resource_filename(__name__, "../metadata.json")


def ffmpeg_version():
    """Returns the available ffmpeg version

    Returns
    ----------
    version : str
        version number as string
    """

    cmd = ["ffmpeg", "-version"]

    output = sp.check_output(cmd)
    aac_codecs = [x for x in output.splitlines() if "ffmpeg version " in str(x)][0]
    hay = aac_codecs.decode("ascii")
    match = re.findall(r"ffmpeg version \w?(\d+\.)?(\d+\.)?(\*|\d+)", hay)
    if match:
        return "".join(match[0])
    else:
        return None

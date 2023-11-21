"""
Load stems into numpy tensors.
"""

import codecs
import json
import os
import subprocess

import numpy as np
import warnings
import ffmpeg
import pprint
from multiprocessing import Pool
import atexit
from functools import partial
import datetime as dt
from .cmds import mp4box_exists, find_cmd


class Reader(object):
    """Base class for reader

    Holds reader options
    """

    def __init__(self):
        pass


class StreamsReader(Reader):
    """Holding configuration for streams

    This is the default reader. Nothing to be hold
    """

    def __init__(self):
        pass


class ChannelsReader(Reader):
    """Using multichannels to multiplex to stems

    stems will be extracted from multichannel-pairs
    e.g. 8 channels will be converted to 4 stereo pairs


    Args:
        from_channels: int
            number of channels, defaults to `2`.
    """

    def __init__(self, nb_channels=2):
        self.nb_channels = nb_channels


def _read_ffmpeg(
    filename, sample_rate, channels, start, duration, dtype, ffmpeg_format, stem_idx
):
    """Loading data using ffmpeg and numpy

    Args:
        filename (str): filename path
        sample_rate (int): sample rate
        channels (int): metadata info object needed to
            know the channel configuration in advance
        start (float): start position in seconds
        duration (float): duration in seconds
        dtype (numpy.dtype): Type of audio array to be casted into
        stem_idx (int): stream id
        ffmpeg_format (str): ffmpeg intermediate format encoding.
            Choose "f32le" for best compatibility

    Returns:
        (array_like): numpy audio array
    """
    output_kwargs = {"format": ffmpeg_format, "ar": sample_rate}
    if duration is not None:
        output_kwargs["t"] = str(dt.timedelta(seconds=duration))
    if start is not None:
        output_kwargs["ss"] = str(dt.timedelta(seconds=start))

    output_kwargs["map"] = "0:" + str(stem_idx)
    process = (
        ffmpeg.input(filename)
        .output("pipe:", **output_kwargs)
        .run_async(pipe_stdout=True, pipe_stderr=True)
    )
    buffer, _ = process.communicate()

    # decode to raw pcm format
    if ffmpeg_format == "f64le":
        # PCM 64 bit float
        numpy_dtype = "<f8"
    elif ffmpeg_format == "f32le":
        # PCM 32 bit float
        numpy_dtype = "<f4"
    elif ffmpeg_format == "s16le":
        # PCM 16 bit signed int
        numpy_dtype = "<i2"
    else:
        raise NotImplementedError("ffmpeg format is not supported")

    waveform = np.frombuffer(buffer, dtype=numpy_dtype).reshape(-1, channels)

    if not waveform.dtype == np.dtype(dtype):
        # cast to target/output dtype
        waveform = waveform.astype(dtype, order="C")
        # when coming from integer, apply normalization t0 [-1.0, 1.0]
        if np.issubdtype(numpy_dtype, np.integer):
            waveform = waveform / (np.iinfo(numpy_dtype).max + 1.0)
    return waveform


def read_stems(
    filename,
    start=None,
    duration=None,
    stem_id=None,
    always_3d=False,
    dtype=np.float_,
    ffmpeg_format="f32le",
    info=None,
    sample_rate=None,
    reader=StreamsReader(),
    multiprocess=False,
    check=False,
):
    """Read stems into numpy tensor

    This function can read both, multi-stream and single stream audio files.
    If used for reading normal audio, the output is a 1d or 2d (mono/stereo)
    array. When multiple streams are read, the output is a 3d array.

    An option stems_from_multichannel was added to load stems that are
    aggregated into multichannel audio (concatenation of pairs of
    stereo channels), see more info on audio `stempeg.write.write_stems`.

    By default `read_stems` assumes that multiple substreams were used to
    save the stem file (`reader=stempeg.StreamsReader()`). To support
    multistream files on audio formats that do not support multiple streams
    (e.g. WAV), streams can be mapped to multiple pairs of channels. In that
    case, `stempeg.ChannelsReader()`, can be passed. Also see:
    `stempeg.write.ChannelsWriter`.


    Args:
        filename (str): filename of the audio file to load data from.
        start (float): Start offset to load from in seconds.
        duration (float): Duration to load in seconds.
        stem_id (int, optional): substream id,
            defauls to `None` (all substreams are loaded).
        always_3d (bool, optional): By default, reading a
            single-stream audio file will return a
            two-dimensional array.  With ``always_3d=True``, audio data is
            always returned as a three-dimensional array, even if the audio
            file has only one stream.
        dtype (np.dtype, optional): Numpy data type to use, default to `np.float32`.
        info (Info, Optional): Pass ffmpeg `Info` object to reduce number
            of os calls on file.
            This can be used e.g. the sample rate and length of a track is
            already known in advance. Useful for ML training where the
            info objects can be pre-processed, thus audio loading can
            be speed up.
        sample_rate (float, optional): Sample rate of returned audio.
            Defaults to `None` which results in
            the sample rate returned from the mixture.
        reader (Reader): Holds parameters for the reading method.
            One of the following:
                `StreamsReader(...)`
                    Read from a single multistream audio (default).
                `ChannelsReader(...)`
                    Read/demultiplexed from multiple channels.
        multiprocess (bool): Applys multi-processing for reading
            substreams in parallel to speed up reading. Defaults to `True`

    Returns:
        stems (array_like):
            stems tensor of `shape=(stem x samples x channels)`
        rate (float):
            sample rate

    Shape:
        - Output: `[S, T, C']`, with
            `S`, if the file has multiple streams and,
            `C` is the audio has multiple channels.

    >>> audio, sample_rate = stempeg.read_stems("test.stem.mp4")
    >>> audio.shape
    [5, 220500, 2]
    >>> sample_rate
    44100
    """
    if multiprocess:
        _pool = Pool()
        atexit.register(_pool.close)
    else:
        _pool = None

    if not isinstance(filename, str):
        filename = filename.decode()

    # use ffprobe to get info object (samplerate, lengths)
    try:
        if info is None:
            metadata = Info(filename)
        else:
            metadata = info

        ffmpeg.probe(filename)
    except ffmpeg._run.Error as e:
        raise Warning(
            "An error occurs with ffprobe (see ffprobe output below)\n\n{}".format(
                e.stderr.decode()
            )
        )

    # check number of audio streams in file
    if "streams" not in metadata.info or metadata.nb_audio_streams == 0:
        raise Warning("No audio stream found.")

    # using ChannelReader would ignore substreams
    if isinstance(reader, ChannelsReader):
        if metadata.nb_audio_streams != 1:
            raise Warning(
                "stempeg.ChannelsReader() only processes the first substream."
            )
        else:
            if metadata.audio_streams[0]["channels"] % reader.nb_channels != 0:
                raise Warning("Stems should be encoded as multi-channel.")
            else:
                substreams = 0
    else:
        if stem_id is not None:
            substreams = stem_id
        else:
            substreams = metadata.audio_stream_idx()

    if not isinstance(substreams, list):
        substreams = [substreams]

    # if not, get sample rate from mixture
    if sample_rate is None:
        sample_rate = metadata.sample_rate(0)

    _chans = metadata.channels_streams
    # check if all substreams have the same number of channels
    if len(set(_chans)) == 1:
        channels = min(_chans)
    else:
        raise RuntimeError(
            "Stems do not have the same number of channels per substream."
        )

    # set channels to minimum channel per stream
    stems = []

    if _pool:
        results = _pool.map_async(
            partial(
                _read_ffmpeg,
                filename,
                sample_rate,
                channels,
                start,
                duration,
                dtype,
                ffmpeg_format,
            ),
            substreams,
            callback=stems.extend,
        )
        results.wait()
        _pool.terminate()
    else:
        stems = [
            _read_ffmpeg(
                filename,
                sample_rate,
                channels,
                start,
                duration,
                dtype,
                ffmpeg_format,
                stem_idx,
            )
            for stem_idx in substreams
        ]
    stem_durations = np.array([t.shape[0] for t in stems])
    if not (stem_durations == stem_durations[0]).all():
        if check:
            raise RuntimeError("Stems differ in length. Integrity check failed.")
        else:
            warnings.warn(
                "Stems differ in length and were shortend. Something might be wrong!"
            )
        min_length = np.min(stem_durations)
        stems = [t[:min_length, :] for t in stems]

    # aggregate list of stems to numpy tensor
    stems = np.array(stems)

    # If ChannelsReader is used, demultiplex from channels
    if isinstance(reader, (ChannelsReader)) and stems.shape[-1] > 1:
        stems = stems.transpose(1, 0, 2)
        stems = stems.reshape(stems.shape[0], stems.shape[1], -1, reader.nb_channels)
        stems = stems.transpose(2, 0, 3, 1)[..., 0]

    if not always_3d:
        stems = np.squeeze(stems)
    return stems, sample_rate


class Info(object):
    """Audio properties that hold a number of metadata.

    The object is created when can be used when `read_stems` is called.
    This is can be passed, to `read_stems` to reduce loading time.
    """

    def __init__(self, filename):
        super(Info, self).__init__()
        self.info = ffmpeg.probe(filename)
        self.audio_streams = [
            stream for stream in self.info["streams"] if stream["codec_type"] == "audio"
        ]
        # Try to get the stem titles using MP4Box if possible, otherwise fall back to numbered stems
        stem_titles = _read_mp4box_stem_titles(filename)
        if stem_titles is not None:
            for i, stream in enumerate(self.audio_streams):
                stream["tags"]["handler_name"] = stem_titles[i]

    @property
    def nb_audio_streams(self):
        """Returns the number of audio substreams"""
        return len(self.audio_streams)

    @property
    def nb_samples_streams(self):
        """Returns a list of number of samples for each substream"""
        return [self.samples(k) for k, stream in enumerate(self.audio_streams)]

    @property
    def channels_streams(self):
        """Returns the number of channels per substream"""
        return [self.channels(k) for k, stream in enumerate(self.audio_streams)]

    @property
    def duration_streams(self):
        """Returns a list of durations (in s) for all substreams"""
        return [self.duration(k) for k, stream in enumerate(self.audio_streams)]

    @property
    def title_streams(self):
        """Returns stream titles for all substreams"""
        return [stream["tags"].get("handler_name") for stream in self.audio_streams]

    def audio_stream_idx(self):
        """Returns audio substream indices"""
        return [s["index"] for s in self.audio_streams]

    def samples(self, idx):
        """Returns the number of samples for a stream index"""
        return int(self.audio_streams[idx]["duration_ts"])

    def duration(self, idx):
        """Returns the duration (in seconds) for a stream index"""
        return float(self.audio_streams[idx]["duration"])

    def title(self, idx):
        """Return the `handler_name` metadata for a given stream index"""
        return self.audio_streams[idx]["tags"]["handler_name"]

    def rate(self, idx):
        # deprecated from older stempeg version
        return self.sample_rate(idx)

    def sample_rate(self, idx):
        """Return sample rate for a given substream"""
        return int(self.audio_streams[idx]["sample_rate"])

    def channels(self, idx):
        """Returns the number of channels for a gvien substream"""
        return int(self.audio_streams[idx]["channels"])

    def __repr__(self):
        """Print stream information"""
        return pprint.pformat(self.audio_streams)


def _read_mp4box_stem_titles(filepath):
    """Reads a mp4 stem titles file using MP4Box"""
    stem_titles = None
    if mp4box_exists():
        mp4box = find_cmd("MP4Box")

        try:
            callArgs = [mp4box]
            callArgs.extend(["-dump-udta", "0:stem", filepath, "-quiet"])
            subprocess.check_call(callArgs)

        except subprocess.CalledProcessError as e:
            return None

        try:
            filename = os.path.basename(filepath)
            root, ext = os.path.splitext(filepath)
            udtaFile = root + "_stem.udta"
            fileObj = codecs.open(udtaFile, encoding="utf-8")
            _metadata = json.load(fileObj)
            os.remove(udtaFile)

            track_name = filename.removesuffix(".stem" + ext)
            stem_names = []
            for d in _metadata["stems"]:
                stem_names.append(track_name + " {" + d["name"] + "}")

            stem_titles = [track_name] + stem_names

        except FileNotFoundError as e:
            return None

    return stem_titles

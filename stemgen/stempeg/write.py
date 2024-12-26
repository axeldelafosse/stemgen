"""
Save stems to disk. 
"""

import base64
import json
import logging
import tempfile as tmp
import warnings
from itertools import chain
from multiprocessing import Pool
from pathlib import Path
import subprocess as sp
import atexit

import ffmpeg
import numpy as np

import stempeg

from .cmds import FFMPEG_PATH, mp4box_exists, get_aac_codec, find_cmd


def _build_channel_map(nb_stems, nb_channels, stem_names=None):
    """Creates an ffmpeg complex filter string

    The filter is designed to multiplex multiple stems into
    multiple channels.

    In the case of single channel stems a filter is created that maps
        nb_channels = nb_stems
    In the case of stereo stems, the filter maps
        nb_channels = nb_stems * 2

    Args:
        nb_stems: int
            Number of stems.
        nb_channels: int
            Number of channels.
        stem_names: list(str)
            List of stem names, should match number of stems.

    Returns:
        complex_filter: str
    """

    if stem_names is None:
        stem_names = ["Stem_" % str(i + 1) for i in range(nb_stems)]

    if nb_stems != len(stem_names):
        raise RuntimeError("Please provide a stem names for each stream")

    if nb_channels == 1:
        return (
            [
                "-filter_complex",
                # set merging
                ";".join(
                    "[a:0]pan=mono| c0=c%d[a%d]" % (idx, idx) for idx in range(nb_stems)
                ),
            ]
        ) + list(
            chain.from_iterable(
                [
                    [
                        "-map",
                        "[a%d]" % idx,
                        # add title tag (e.g. displayed by VLC)
                        "-metadata:s:a:%d" % idx,
                        "title=%s" % stem_names[idx],
                        # add handler tag (e.g. read by ffmpeg < 4.1)
                        "-metadata:s:a:%d" % idx,
                        "handler=%s" % stem_names[idx],
                        # add handler tag for ffmpeg >= 4.1
                        "-metadata:s:a:%d" % idx,
                        "handler_name=%s" % stem_names[idx],
                    ]
                    for idx in range(nb_stems)
                ]
            )
        )
    elif nb_channels == 2:
        return (
            [
                "-filter_complex",
                # set merging
                ";".join(
                    "[a:0]pan=stereo| c0=c%d | c1=c%d[a%d]"
                    % (idx * 2, idx * 2 + 1, idx)
                    for idx in range(nb_stems)
                ),
            ]
        ) + list(
            chain.from_iterable(
                [
                    [
                        "-map",
                        "[a%d]" % idx,
                        # add title tag (e.g. displayed by VLC)
                        "-metadata:s:a:%d" % idx,
                        "title=%s" % stem_names[idx],
                        # add handler tag (e.g. read by ffmpeg -i)
                        "-metadata:s:a:%d" % idx,
                        "handler=%s" % stem_names[idx],
                        # add handler tag for ffmpeg >= 4.1
                        "-metadata:s:a:%d" % idx,
                        "handler_name=%s" % stem_names[idx],
                    ]
                    for idx in range(nb_stems)
                ]
            )
        )
    else:
        raise NotImplementedError("Stempeg only support mono or stereo stems")


class Writer(object):
    """Base template class for writer

    Takes tensor and writes back to disk
    """

    def __init__(self):
        pass

    def __call__(self, data, path, sample_rate):
        """forward path

        Args:
            data (array): stems tensor of shape `(stems, samples, channel)`
            path (str): path with extension
            sample_rate (float): audio sample rate
        """
        pass


class FilesWriter(Writer):
    r"""Save Stems as multiple files

    Takes stems tensor and write into multiple files.

    Args:
        codec: str
            Specifies ffmpeg codec being used. Defaults to `None` which
            automatically selects default codec for each container
        bitrate: int, optional
            Bitrate in Bits per second. Defaults to `None`
        output_sample_rate: float, optional
            Optionally, applies resampling, if different to `sample_rate`.
            Defaults to `None` which `sample_rate`.
        stem_names: List(str)
            List of stem names to be used for writing. Defaults to `None` which
            results in stem names to be enumerated: `['Stem_1', 'Stem_2', ...]`
        multiprocess: bool
            Enable multiprocessing when writing files.
            Can speed up writing of large files. Defaults to `False`.
        synchronous bool:
            Write multiprocessed synchronous. Defaults to `True`.
    """

    def __init__(
        self,
        codec=None,
        bitrate=None,
        output_sample_rate=44100,
        stem_names=None,
        multiprocess=False,
        synchronous=True,
    ):
        self.codec = codec
        self.bitrate = bitrate
        self.output_sample_rate = output_sample_rate
        self.stem_names = stem_names
        self.synchronous = synchronous
        if multiprocess:
            self._pool = Pool()
            atexit.register(self._pool.close)
        else:
            self._pool = None
        self._tasks = []

    def join(self, timeout=200):
        """Wait for all pending tasks to be finished.

        Args:
            timeout (Optional): int
                task waiting timeout.
        """
        while len(self._tasks) > 0:
            task = self._tasks.pop()
            task.get()
            task.wait(timeout=timeout)

    def __call__(self, data, path, sample_rate):
        """
        Args:
            data: array_like
                stems tensor of shape `(stems, samples, channel)`
            path: str or tuple(str, str)
                path with extension of output folder. Note that the basename
                of the path will be ignored. Wildcard can be used.
                    Example: `path=/stems/*.wav` writes
                             `/stems/Stem_1.wav`, `/stems/Stem_2.wav` ..
                Alternatively a tuple can be used:
                    Example: `path=("/stems", ".wav")`
            sample_rate: float
                audio sample rate
        """
        nb_stems = data.shape[0]

        if self.output_sample_rate is None:
            self.output_sample_rate = sample_rate

        if self.stem_names is None:
            self.stem_names = ["Stem_" + str(k) for k in range(nb_stems)]

        for idx in range(nb_stems):
            if type(path) is tuple:
                stem_filepath = str(Path(path[0], self.stem_names[idx] + path[1]))
            else:
                p = Path(path)
                stem_filepath = str(Path(p.parent, self.stem_names[idx] + p.suffix))
            if self._pool:
                task = self._pool.apply_async(
                    write_audio,
                    (
                        stem_filepath,
                        data[idx],
                        sample_rate,
                        self.output_sample_rate,
                        self.codec,
                        self.bitrate,
                    ),
                )
                self._tasks.append(task)
            else:
                write_audio(
                    path=stem_filepath,
                    data=data[idx],
                    sample_rate=sample_rate,
                    output_sample_rate=self.output_sample_rate,
                    codec=self.codec,
                    bitrate=self.bitrate,
                )
        if self.synchronous and self._pool:
            self.join()


class ChannelsWriter(Writer):
    """Write stems using multichannel audio

    This Writer multiplexes stems into channels. Note, that
    the used container would need support for multichannel audio.
        E.g. `wav` works but `mp3` won't.

    Args:
        codec (str): Specifies ffmpeg codec being used.
            Defaults to `None` which automatically selects default
            codec for each container
        bitrate (int): Bitrate in Bits per second. Defaults to None
        output_sample_rate (float, optional): Optionally, applies
            resampling, if different to `sample_rate`.
            Defaults to `None` which `sample_rate`.
    """

    def __init__(self, codec=None, bitrate=None, output_sample_rate=None):
        self.codec = codec
        self.bitrate = bitrate
        self.output_sample_rate = output_sample_rate

    def __call__(self, data, path, sample_rate):
        """
        For more than one stem, stems will be reshaped
        into the channel dimension, assuming we have
        stereo channels:
            (stems, samples, 2)->(nb_samples=samples, nb_channels=stems*2)
        mono channels:
            (stems, samples, 1)-> (nb_samples=samples, nb_channels=stems)

        Args:
            data (array): stems tensor of shape `(stems, samples, channel)`.
            path (str): path with extension.
            sample_rate (float): audio sample rate.
        """
        # check output sample rate
        if self.output_sample_rate is None:
            self.output_sample_rate = sample_rate

        nb_stems, nb_samples, nb_channels = data.shape

        # (stems, samples, channels) -> (samples, stems, channels)
        data = data.transpose(1, 0, 2)
        # aggregate stem and channels
        data = data.reshape(nb_samples, -1)

        data = np.squeeze(data)
        write_audio(
            path=path,
            data=data,
            sample_rate=sample_rate,
            output_sample_rate=self.output_sample_rate,
            codec=self.codec,
            bitrate=self.bitrate,
        )


class StreamsWriter(Writer):
    """Write stems using multi-stream audio.

    This writer saves the audio into a multistream format. Note,
    that the container needs to have support for multistream audio.
    E.g. supported formats are mp4, ogg.

    The `stem_names` are inserted into the metadata.
    Note that this writer converts to substreams using a
    temporary wav file written to disk. Therefore, writing can be slow.

    Args:
        codec (str): Specifies ffmpeg codec being used.
            Defaults to `None` which automatically selects default
            codec for each container
        bitrate (int): Bitrate in Bits per second. Defaults to None
        output_sample_rate (float): Optionally, applies
            resampling, if different to `sample_rate`.
            Defaults to `None` which `sample_rate`.
        stem_names (str): list of stem names that
            match the number of stems.
    """

    def __init__(
        self, codec=None, bitrate=None, output_sample_rate=None, stem_names=None
    ):
        self.codec = codec
        self.bitrate = bitrate
        self.output_sample_rate = output_sample_rate
        self.stem_names = stem_names

    def __call__(
        self,
        data,
        path,
        sample_rate,
    ):
        """
        Args:
            data (array): stems tensor of shape `(stems, samples, channel)`
            path (str): path with extension
            sample_rate (float): audio sample rate
        """
        nb_stems, nb_samples, nb_channels = data.shape

        if self.output_sample_rate is None:
            self.output_sample_rate = sample_rate

        if self.stem_names is None:
            self.stem_names = ["Stem " + str(k) for k in range(nb_stems)]

        # (stems, samples, channels) -> (samples, stems, channels)
        data = data.transpose(1, 0, 2)
        # aggregate stem and channels
        data = data.reshape(nb_samples, -1)

        # stems as multistream file (real stems)
        # create temporary file and merge afterwards
        with tmp.NamedTemporaryFile(suffix=".wav") as tempfile:
            # write audio to temporary file
            write_audio(
                path=tempfile.name,
                data=data,
                sample_rate=sample_rate,
                output_sample_rate=self.output_sample_rate,
                codec="pcm_s16le",
            )

            # check if path is available and creat it
            Path(path).parent.mkdir(parents=True, exist_ok=True)

            channel_map = _build_channel_map(
                nb_stems=nb_stems, nb_channels=nb_channels, stem_names=self.stem_names
            )

            # convert tempfile to multistem file assuming
            # each stem occupies a pair of channels
            cmd = (
                [FFMPEG_PATH, "-y", "-acodec", "pcm_s%dle" % (16), "-i", tempfile.name]
                + channel_map
                + ["-vn"]
                + (["-c:a", self.codec] if (self.codec is not None) else [])
                + [
                    "-ar",
                    "%d" % self.output_sample_rate,
                    "-strict",
                    "-2",
                    "-loglevel",
                    "error",
                ]
                + (["-ab", str(self.bitrate)] if (self.bitrate is not None) else [])
                + [path]
            )
            try:
                sp.check_call(cmd)
            except sp.CalledProcessError as err:
                raise RuntimeError(err) from None
            finally:
                tempfile.close()


class NIStemsWriter(Writer):
    """Write stems using native instruments stems format

    This writer is similar to `StreamsWriter` except that certain defaults
    and metadata are adjusted to increase compatibility with Native Instruments
    Stems format. This writer should be used when users want to play back stems
    eg. using Traktor DJ.

    By definition, this format only supports _five_ audio streams where
    stream index 0 is the mixture.

    This writer creates intermediate temporary files, which can result in slow
    writing. Therefore, `StemsWriter` should be used in all cases where Traktor
    compatibility is not necessary.

    Process is originally created by Native Instrument as shown here:
    https://github.com/axeldelafosse/stemgen/blob/909d9422af0738457303962262f99072a808d0c1/ni-stem/_internal.py#L38

    Args:
        default_metadata (Dict): Metadata to be injected into the mp4 substream.
            Defaults to `stempeg.default_metadata()`.
        stems_metadata: List
            Set dictory of track names and colors
                `[{'name': str, 'color': str (hex)}, ...]`
            Defaults to `stempeg.default_metadata()['stems']`, which
            sets stem names to the following order:
                `['mixture', 'drums', 'bass', 'other', 'vocals']`
        codec: str
            Specifies ffmpeg codec being used. Defaults to `aac` and,
            for best quality, will try to use `libfdk_aac` if availability.
        bitrate: int
            Bitrate in Bits per second. Defaults to None
        output_sample_rate Optional: float
            Optionally, applies resampling, if different to `sample_rate`.
            Defaults to `None` which `sample_rate`.
    """

    def __init__(
        self,
        default_metadata=None,
        stems_metadata=None,
        codec="aac",
        bitrate=256000,
        output_sample_rate=44100,
    ):
        if not mp4box_exists():
            raise RuntimeError(
                "MP4Box could not be found! "
                "Please install them before using NIStemsWriter()."
                "See: https://github.com/faroit/stempeg"
            )
        self.mp4boxcli = find_cmd("MP4Box")
        self.bitrate = bitrate
        self.default_metadata = default_metadata
        self.stems_metadata = stems_metadata
        self.output_sample_rate = output_sample_rate
        self._suffix = ".m4a"  # internal suffix for temporarly file
        if codec == "aac":
            self.codec = get_aac_codec()
        else:
            self.codec = codec

    def __call__(self, data, path, sample_rate):
        """
        Args:
            data: array
                stems tensor of shape `(5, samples, channel)`
            path: str
                path with extension
            sample_rate: float
                audio sample rate
        """
        if data.ndim != 3:
            raise RuntimeError("Please pass multiple stems")

        if data.shape[2] % 2 != 0:
            raise RuntimeError("Only stereo stems are supported")

        if data.shape[0] != 5:
            raise RuntimeError(
                "NI Stems requires 5 streams, where stream 0 is the mixture."
            )

        if data.shape[1] % 1024 != 0:
            logging.warning(
                "Number of samples does not divide by 1024, be aware that "
                "the AAC encoder add silence to the input signal"
            )

        # write m4a files to temporary folder
        with tmp.TemporaryDirectory() as tempdir:
            write_stems(
                Path(tempdir, "tmp" + self._suffix),
                data,
                sample_rate=sample_rate,
                writer=FilesWriter(
                    codec=self.codec,
                    bitrate=self.bitrate,
                    output_sample_rate=self.output_sample_rate,
                    stem_names=[str(k) for k in range(data.shape[0])],
                ),
            )
            # add metadata for NI compabtibility
            if self.default_metadata is None:
                with open(stempeg.default_metadata()) as f:
                    metadata = json.load(f)
            else:
                metadata = self.default_metadata

            # replace stems metadata from dict
            if self.stems_metadata is not None:
                metadata["stems"] = self.stems_metadata

            callArgs = [self.mp4boxcli]
            callArgs.extend(["-add", str(Path(tempdir, "0.m4a#ID=Z")), path])
            for s in range(1, data.shape[0]):
                callArgs.extend(
                    [
                        "-add",
                        str(Path(tempdir, str(s) + self._suffix + "#ID=Z:disable")),
                    ]
                )
            callArgs.extend(
                [
                    "-brand",
                    "M4A:0",
                    "-rb",
                    "isom",
                    "-rb",
                    "iso2",
                    "-udta",
                    "0:type=stem:src=base64,"
                    + base64.b64encode(json.dumps(metadata).encode()).decode(),
                    "-quiet",
                ]
            )
            try:
                sp.check_call(callArgs)
            except sp.CalledProcessError as err:
                raise RuntimeError(err) from None


def write_audio(
    path, data, sample_rate=44100.0, output_sample_rate=None, codec=None, bitrate=None
):
    """Write multichannel audio from numpy tensor

    Audio writer for multi-channel but not multi-stream audio.
    Can be used directly, when stems are not required.

    Args:
        path (str): Output file name.
            Extension sets container (and default codec).
        data (array_like): Audio tensor. The data shape is formatted as
            `shape=(samples, channels)` or `(samples,)`.
        sample_rate (float): Samplerate. Defaults to 44100.0 Hz.
        output_sample_rate (float): Applies resampling, if different
            to `sample_rate`. Defaults to `None` which uses `sample_rate`.
        codec (str): Specifies ffmpeg codec being used.
            Defaults to `None` which automatically selects default
            codec for each container
        bitrate (int): Bitrate in Bits per second. Defaults to None
    """

    # check if path is available and creat it
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    if output_sample_rate is None:
        output_sample_rate = sample_rate

    if data.ndim == 1:
        nb_channels = 1
    elif data.ndim == 2:
        nb_channels = data.shape[-1]
    else:
        raise RuntimeError("Number of channels not supported")

    input_kwargs = {"ar": sample_rate, "ac": nb_channels}
    output_kwargs = {"ar": output_sample_rate, "strict": "-2"}
    if bitrate:
        output_kwargs["audio_bitrate"] = bitrate
    if codec is not None:
        output_kwargs["codec"] = codec
    process = (
        ffmpeg.input("pipe:", format="f32le", **input_kwargs)
        .output(path, **output_kwargs)
        .overwrite_output()
        .run_async(pipe_stdin=True, pipe_stderr=True, quiet=True)
    )
    try:
        process.stdin.write(data.astype("<f4").tobytes())
        process.stdin.close()
        process.wait()
    except IOError:
        raise Warning(f"FFMPEG error: {process.stderr.read()}")


def write_stems(path, data, sample_rate=44100, writer=StreamsWriter(stem_names=None)):
    """Write a stems numpy tensor to audio file(s).

    Args:
        path (str): Output file_name of the stems file. Note
            that the extension of the path determines the used
            output container format (e.g. mp4) which can differ
            from the `codec`.
        data (array_like or dict): The tensor of stems.
            The data shape is formatted as
                `(stems, samples, channels)`.
            If a `dict` is provided, we assume:
                `{ "name": array_like of shape (samples, channels), ...}`
        sample_rate (int): Output samplerate. Defaults to 44100 Hz.
        writer (Writer): Stempeg supports four methods to save
            multi-stream audio.
            Each of the method has different number of parameters.
            To select a method one of the following setting and be passed:

            `stempeg.FilesWriter`
                Stems will be saved into multiple files. For the naming,
                `basename(path)` is ignored and just the
                parent of `path`  and its `extension` is used.

            `stempeg.ChannelsWriter`
                Stems will be saved as multiple channels.

            `stempeg.StreamsWriter` **(default)**.
                Stems will be saved into a single a multi-stream file.

            `stempeg.NIStemsWriter`
                Stem will be saved into a single multistream audio.
                Additionally Native Instruments Stems compabible
                Metadata is added. This requires the installation of
                `MP4Box`. See [Readme](../README.md) for more info.
    Notes:
        Note that file ending of `path` sets the container but not the codec!
        The support for different stem writers depends on the specified output
        container format (aka. the `path` extension/appendix).

        We differentiate between

        ### Container supports multiple stems (`mp4/m4a`, `opus`, `mka`)

        - `stempeg.StreamsWriter` and `stempeg.NIStemsWriter`
            stems will be saved as sub-streams.
        - `stempeg.ChannelsWriter`
            stems will be multiplexed into channels and saved as a single
            multichannel file. E.g. an `audio` tensor of `shape=(stems, samples, 2)`
            will be converted to a single-stem multichannel audio
            `(samples, stems*2)`.
        - `stempeg.FilesWriter` so that multiple files will be created when
            stems_as_files` is active.


        ### A container does not support multiple stems there

        - `stempeg.ChannelsWriter` when the container supports multi-channel
            audio. E.g. works for `wav` and `flac`.
        - `stempeg.FilesWriter` so that multiple files will be created when
            stems_as_files` is active.

        ## Example 1: Write a stems file

        Write `stems` tensor as multi-stream audio.

        >>> stempeg.write_stems(
        >>>     "test.stem.m4a",
        >>>     data=stems,
        >>>     sample_rate=44100.0
        >>> )

        ## Example 2: Advanced Example

        Writing a dictionary as a bunch of MP3s,
        instead of a single file.
        We use `stempeg.FilesWriter`, outputs are named
        ["output/mix.mp3", "output/drums.mp3", ...],
        we pass `stem_names`; also apply multiprocessing.

        >>> stems = {
        >>>    "mix": stems[0], "drums": stems[1],
        >>>    "bass": stems[2], "other": stems[3],
        >>>    "vocals": stems[4],
        >>> }
        >>> stempeg.write_stems(
        >>> ("output", ".mp3"),
        >>> stems,
        >>> sample_rate=rate,
        >>> writer=stempeg.FilesWriter(
        >>>         multiprocess=True,
        >>>         output_sample_rate=48000,
        >>>         stem_names=["mix", "drums", "bass", "other", "vocals"]
        >>>     )
        >>> )



    """
    # check if ffmpeg installed
    if int(stempeg.ffmpeg_version()[0]) < 3:
        warnings.warn(
            "Writing stems with FFMPEG version < 3 is unsupported", UserWarning
        )

    if isinstance(data, dict):
        keys = data.keys()
        values = data.values()
        data = np.array(list(values))
        stem_names = list(keys)
        if not isinstance(writer, (ChannelsWriter)):
            writer.stem_names = stem_names

    if data.ndim != 3:
        raise RuntimeError("Input tensor dimension should be 3d")

    return writer(path=path, data=data, sample_rate=sample_rate)

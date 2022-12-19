import codecs
import json
import base64
import mutagen
import mutagen.mp4
import mutagen.id3
from urllib.request import urlopen
import os
import platform
import subprocess
import sys

stemDescription  = 'stem-meta'
stemOutExtension = ".m4a"

_windows = platform.system() == "Windows"
_linux = platform.system() == "Linux"

_supported_files_no_conversion = [".m4a", ".mp4", ".m4p"]
_supported_files_conversion = [".wav", ".wave", ".aif", ".aiff", ".flac"]
_supported_files = _supported_files_no_conversion + _supported_files_conversion

def _removeFile(path):
    if os.path.lexists(path):
        if os.path.isfile(path):
            os.remove(path)
        else:
            raise RuntimeError("Cannot remove " + path + ": not a file")

def _getProgramPath():
    folderPath = os.path.dirname(os.path.realpath(__file__))
    if os.path.isfile(folderPath):
        # When packaging the script with py2exe, os.path.realpath returns the path to the object file within
        # the .exe, so we have to apply os.path.dirname() one more time
        folderPath = os.path.dirname(folderPath)
    return folderPath

def _findCmd(cmd):
    try:
        from shutil import which
        return which(cmd)
    except ImportError:
        import os
        for path in os.environ["PATH"].split(os.pathsep):
            if os.access(os.path.join(path, cmd), os.X_OK):
                return path
    return None

class StemCreator:

    _defaultMetadata = [
        {"name": "Drums" , "color" : "#009E73"},
        {"name": "Bass"  , "color" : "#D55E00"},
        {"name": "Other", "color" : "#CC79A7"},
        {"name": "Vox" , "color" : "#56B4E9"}
    ]

    def __init__(self, mixdownTrack, stemTracks, fileFormat, metadataFile = None, tags = None):
        self._mixdownTrack = mixdownTrack
        self._stemTracks   = stemTracks
        self._format       = fileFormat if fileFormat else "alac"
        self._tags         = json.load(open(tags)) if tags else {}

        # Mutagen complains gravely if we do not explicitly convert the tag values to a
        # particular encoding. We chose UTF-8, others would work as well.
        # for key, value in self._tags.iteritems(): self._tags[key] = repr(value).encode('utf-8')

        metaData = []
        if metadataFile:
            fileObj = codecs.open(metadataFile, encoding="utf-8")
            try:
                metaData = json.load(fileObj)
            except IOError:
                raise
            except Exception as e:
                raise RuntimeError("Error while reading metadata file")
            finally:
                fileObj.close()

        numStems       = len(stemTracks)
        numMetaEntries = len(metaData["stems"])

        self._metadata = metaData

        # If the input JSON file contains less metadata entries than there are stem tracks, we use the default
        # entries. If even those are not enough, we pad the remaining entries with the following default value:
        # {"name" : "Stem_${TRACK#}", "color" : "#000000"}

        if numStems > numMetaEntries:
            print("missing stem metadata for stems " + str(numMetaEntries) + " - " + str(numStems))
            numDefaultEntries = len(self._defaultMetadata)
            self._metadata.extend(self._defaultMetadata["stems"][numMetaEntries:min(numStems, numDefaultEntries)])
            self._metadata["stems"].extend([{"name" :"".join(["Stem_", str(i + numDefaultEntries)]), "color" : "#000000"} \
                for i in range(numStems - numDefaultEntries)])

    def _convertToFormat(self, trackPath, format):
        trackName, fileExtension = os.path.splitext(trackPath)

        if fileExtension in _supported_files_no_conversion:
            return trackPath

        if fileExtension in _supported_files_conversion:
            print("\nconverting " + trackPath + " to " + self._format + "...")
            sys.stdout.flush()

            newPath = trackName + ".m4a"
            _removeFile(newPath)

            converter = os.path.join(_getProgramPath(), "avconv_win", "avconv.exe") if _windows else "ffmpeg" if _linux else "afconvert"
            converterArgs = [converter]

            if _windows or _linux:
                converterArgs.extend(["-i"  , trackPath])
                if self._format == "aac":
                    converterArgs.extend(["-b", "256k"])
                else:
                    converterArgs.extend(["-c:a", self._format])
            else:
                converterArgs.extend(["-d"  , self._format])
                if self._format == "aac":
                    converterArgs.extend(["-b", "256000"])
                converterArgs.extend([trackPath])

            converterArgs.extend([newPath])
            subprocess.check_call(converterArgs)
            return newPath
        else:
            print("invalid input file format \"" + fileExtension + "\"")
            print("valid input file formats are " + ", ".join(_supported_files_conversion))
            sys.exit()

    def save(self, outputFilePath = None):
        # When using mp4box, in order to get a playable file, the initial file
        # extension has to be .m4a -> this gets renamed at the end of the method.
        if not outputFilePath:
            root, ext = os.path.splitext(self._mixdownTrack)
            root += ".stem"
        else:
            root, ext = os.path.splitext(outputFilePath)

        outputFilePath = "".join([root, stemOutExtension])
        _removeFile(outputFilePath)

        folderName = "GPAC_win"   if _windows else "GPAC_mac"
        executable = "mp4box.exe" if _windows else "MP4Box"
        mp4box     = _findCmd(executable) if _linux else os.path.join(_getProgramPath(), folderName, executable)
        
        print("\n[Done 0/6]\n")
        sys.stdout.flush()
        
        callArgs = [mp4box]
        callArgs.extend(["-add", self._convertToFormat(self._mixdownTrack, format) + "#ID=Z", outputFilePath])
        print("\n[Done 1/6]\n")
        sys.stdout.flush()
        conversionCounter = 1
        for stemTrack in self._stemTracks:
            callArgs.extend(["-add", self._convertToFormat(stemTrack, format) + "#ID=Z:disable"])
            conversionCounter += 1
            print("\n[Done " + str(conversionCounter) + "/6]\n")
            sys.stdout.flush()

        metadata = json.dumps(self._metadata)
        metadata = base64.b64encode(metadata.encode("utf-8"))
        metadata = "0:type=stem:src=base64," + metadata.decode("utf-8")
        callArgs.extend(["-udta", metadata])
        subprocess.check_call(callArgs)
        sys.stdout.flush()

        # https://picard-docs.musicbrainz.org/en/appendices/tag_mapping.html
        # http://www.jthink.net/jaudiotagger/tagmapping.html
        # https://mutagen.readthedocs.io/en/latest/api/mp4.html

        tags = mutagen.mp4.Open(outputFilePath)
        # name
        if ("title" in self._tags):
            tags["\xa9nam"] = self._tags["title"]
        # artist
        if ("artist" in self._tags):
            tags["\xa9ART"] = self._tags["artist"]
        # album
        if ("release" in self._tags):
            tags["\xa9alb"] = self._tags["release"]
        # remixer
        if ("remixer" in self._tags):
            tags["----:com.apple.iTunes:REMIXER"] = mutagen.mp4.MP4FreeForm(self._tags["remixer"].encode("utf-8"))
        # mix
        if ("mix" in self._tags):
            tags["----:com.apple.iTunes:MIXER"] = mutagen.mp4.MP4FreeForm(self._tags["mix"].encode("utf-8"))
        # producer
        if ("producer" in self._tags):
            tags["----:com.apple.iTunes:PRODUCER"] = mutagen.mp4.MP4FreeForm(self._tags["producer"].encode("utf-8"))
        # label
        if ("label" in self._tags):
            tags["----:com.apple.iTunes:LABEL"] = mutagen.mp4.MP4FreeForm(self._tags["label"].encode("utf-8"))
        # genre
        if ("style" in self._tags):
            tags["\xa9gen"] = self._tags["style"]
        if ("genre" in self._tags):
            tags["\xa9gen"] = self._tags["genre"]
        # trkn
        if ("track" in self._tags):
            if ("track_count" in self._tags):
                tags["trkn"] = [(int(self._tags["track"]), int(self._tags["track_count"]))]
        if ("track_no" in self._tags):
            if ("track_count" in self._tags):
                tags["trkn"] = [(int(self._tags["track_no"]), int(self._tags["track_count"]))]
        # catalog number
        if ("catalog_no" in self._tags):
            tags["----:com.apple.iTunes:CATALOGNUMBER"] = mutagen.mp4.MP4FreeForm(self._tags["catalog_no"].encode("utf-8"))
        # date
        if ("year" in self._tags):
            tags["\xa9day"] = self._tags["year"]
        if ("date" in self._tags):
            tags["\xa9day"] = self._tags["date"]
        # isrc
        if ("isrc" in self._tags):
            tags["----:com.apple.iTunes:ISRC"] = mutagen.mp4.MP4FreeForm(self._tags["isrc"].encode("utf-8"), mutagen.mp4.AtomDataType.ISRC)
        # barcode
        if ("upc" in self._tags):
            tags["----:com.apple.iTunes:BARCODE"] = mutagen.mp4.MP4FreeForm(str(self._tags["upc"]).encode("utf-8"), mutagen.mp4.AtomDataType.UPC)
        # cover
        if ("cover" in self._tags):
            coverPath = self._tags["cover"]
            f = urlopen(coverPath)
            tags["covr"] = [mutagen.mp4.MP4Cover(f.read(),
              mutagen.mp4.MP4Cover.FORMAT_PNG if coverPath.endswith('png') else
              mutagen.mp4.MP4Cover.FORMAT_JPEG
            )]
            f.close()
        # description (long description)
        if ("description" in self._tags):
            tags["ldes"] = self._tags["description"]
        # comment
        if ("comment" in self._tags):
            tags["\xa9cmt"] = self._tags["comment"]
        # bpm
        if ("bpm" in self._tags):
            tags["tmpo"] = [int(self._tags["bpm"])]
        # initial key
        if ("initialkey" in self._tags):
            tags["----:com.apple.iTunes:initialkey"] = mutagen.mp4.MP4FreeForm(self._tags["initialkey"].encode("utf-8"))
        # key
        if ("key" in self._tags):
            tags["----:com.apple.iTunes:KEY"] = mutagen.mp4.MP4FreeForm(self._tags["key"].encode("utf-8"))
        # album
        if ("album" in self._tags):
            tags["\xa9alb"] = self._tags["album"]
        # mood
        if ("mood" in self._tags):
            tags["----:com.apple.iTunes:MOOD"] = mutagen.mp4.MP4FreeForm(self._tags["mood"].encode("utf-8"))
        # grouping
        if ("grouping" in self._tags):
            tags["\xa9grp"] = self._tags["grouping"]
        # composer
        if ("composer" in self._tags):
            tags["\xa9wrt"] = self._tags["composer"]
        # barcode
        if ("barcode" in self._tags):
            tags["----:com.apple.iTunes:BARCODE"] = mutagen.mp4.MP4FreeForm(str(self._tags["barcode"]).encode("utf-8"), mutagen.mp4.AtomDataType.UPC)
        # lyrics
        if ("lyrics" in self._tags):
            tags["\xa9lyr"] = self._tags["lyrics"]
        # copyright
        if ("copyright" in self._tags):
            tags["cprt"] = self._tags["copyright"]
        # url_discogs_artist_site
        if ("url_discogs_artist_site" in self._tags):
            tags["----:com.apple.iTunes:URL_DISCOGS_ARTIST_SITE"] = mutagen.mp4.MP4FreeForm(self._tags["url_discogs_artist_site"].encode("utf-8"))
        # url_discogs_release_site
        if ("url_discogs_release_site" in self._tags):
            tags["----:com.apple.iTunes:URL_DISCOGS_RELEASE_SITE"] = mutagen.mp4.MP4FreeForm(self._tags["url_discogs_release_site"].encode("utf-8"))
        # youtube_id
        if ("youtube_id" in self._tags):
            tags["----:com.apple.iTunes:YouTube Id"] = mutagen.mp4.MP4FreeForm(self._tags["youtube_id"].encode("utf-8"))
        # beatport_id
        if ("beatport_id" in self._tags):
            tags["----:com.apple.iTunes:Beatport Id"] = mutagen.mp4.MP4FreeForm(self._tags["beatport_id"].encode("utf-8"))
        # qobuz_id
        if ("qobuz_id" in self._tags):
            tags["----:com.apple.iTunes:Qobuz Id"] = mutagen.mp4.MP4FreeForm(self._tags["qobuz_id"].encode("utf-8"))

        tags["TAUT"] = "STEM"
        tags.save(outputFilePath)
        
        print("\n[Done 6/6]\n")
        sys.stdout.flush()

        print("creating " + outputFilePath + " was successful!")


class StemMetadataViewer:

    def __init__(self, stemFile):
        self._metadata = {}

        if stemFile:
            folderName = "GPAC_win"   if _windows else "GPAC_mac"
            executable = "mp4box.exe" if _windows else "MP4Box"
            mp4box     = _findCmd(executable) if _linux else os.path.join(_getProgramPath(), folderName, executable)

            callArgs = [mp4box]
            callArgs.extend(["-dump-udta", "0:stem", stemFile])
            subprocess.check_call(callArgs)

            root, ext = os.path.splitext(stemFile)
            udtaFile = root + "_stem.udta"
            fileObj = codecs.open(udtaFile, encoding="utf-8")
            fileObj.seek(8)
            self._metadata = json.load(fileObj)
            os.remove(udtaFile)

    def dump(self, metadataFile = None, reportFile = None):
        if metadataFile:
            fileObj = codecs.open(metadataFile, mode="w", encoding="utf-8")
            try:
                fileObj.write(json.dumps(self._metadata))
            except Exception as e:
                raise e
            finally:
                fileObj.close()

        if reportFile:
            fileObj = codecs.open(reportFile, mode="w", encoding="utf-8")
            try:
                for i, value in enumerate(self._metadata["stems"]):
                    line = u"Track {:>3}      name: {:>15}     color: {:>8}\n".format(i + 1, value["name"], value["color"])
                    fileObj.write(line)
            except Exception as e:
                raise e
            finally:
                fileObj.close()

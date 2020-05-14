import codecs
import json
import base64
import mutagen
import mutagen.mp4
import mutagen.id3
import urllib2 as urllib
import os
import platform
import subprocess
import sys

stemDescription  = 'stem-meta'
stemOutExtension = ".m4a"

_windows = platform.system() == "Windows"

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


class StemCreator:

    _defaultMetadata = [
        {"name": "Drums" , "color" : "#FF0000"},
        {"name": "Bass"  , "color" : "#00FF00"},
        {"name": "Synths", "color" : "#FFFF00"},
        {"name": "Other" , "color" : "#0000FF"}
    ]

    def __init__(self, mixdownTrack, stemTracks, fileFormat, metadataFile = None, tags = None):
        self._mixdownTrack = mixdownTrack
        self._stemTracks   = stemTracks
        self._format       = fileFormat if fileFormat else "aac"
        self._tags         = json.load(open(tags)) if tags else {}

        # Mutagen complains gravely if we do not explicitly convert the tag values to a
        # particular encoding. We chose UTF-8, others would work as well.
        for key, value in self._tags.iteritems(): self._tags[key] = value.encode('utf-8')

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

            converter = os.path.join(_getProgramPath(), "avconv_win", "avconv.exe") if _windows else "afconvert"
            converterArgs = [converter]

            if _windows:
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
        executable = "mp4box.exe" if _windows else "mp4box"
        mp4box     = os.path.join(_getProgramPath(), folderName, executable)
        
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
        callArgs.extend(["-udta", "0:type=stem:src=base64," + base64.b64encode(json.dumps(self._metadata))])
        subprocess.check_call(callArgs)
        sys.stdout.flush()

        tags = mutagen.mp4.Open(outputFilePath)
        if ("track" in self._tags) and (len(self._tags["track"]) > 0):
            tags["\xa9nam"] = self._tags["track"]
        if ("artist" in self._tags) and (len(self._tags["artist"]) > 0):
            tags["\xa9ART"] = self._tags["artist"]
        if ("release" in self._tags) and (len(self._tags["release"]) > 0):
            tags["\xa9alb"] = self._tags["release"]
        if ("remixer" in self._tags) and (len(self._tags["remixer"]) > 0):
            tags["----:com.apple.iTunes:REMIXER"] = mutagen.mp4.MP4FreeForm(self._tags["remixer"])
        if ("mix" in self._tags) and (len(self._tags["mix"]) > 0):
            tags["----:com.apple.iTunes:MIXER"] = mutagen.mp4.MP4FreeForm(self._tags["mix"])
        if ("producer" in self._tags) and (len(self._tags["producer"]) > 0):
            tags["----:com.apple.iTunes:PRODUCER"] = self._tags["producer"]
        if ("label" in self._tags) and (len(self._tags["label"]) > 0):
            tags["----:com.apple.iTunes:LABEL"] = mutagen.mp4.MP4FreeForm(self._tags["label"])
        if ("genre" in self._tags) and (len(self._tags["genre"]) > 0):
            tags["\xa9gen"] = self._tags["genre"]
        if ("track_no" in self._tags) and (len(self._tags["track_no"]) > 0):
            if ("track_count" in self._tags) and (len(self._tags["track_count"]) > 0):
                tags["trkn"] = [(int(self._tags["track_no"]), int(self._tags["track_count"]))] #self._tags["track_no"]
        if ("catalog_no" in self._tags) and (len(self._tags["catalog_no"]) > 0):
            tags["----:com.apple.iTunes:CATALOGNUMBER"] = mutagen.mp4.MP4FreeForm(self._tags["catalog_no"])
        if ("year" in self._tags) and (len(self._tags["year"]) > 0):
            tags["\xa9day"] = self._tags["year"]
        if ("isrc" in self._tags) and (len(self._tags["isrc"]) > 0):
            tags["TSRC"] = mutagen.id3.TSRC(encoding=None, text=self._tags["isrc"])
            tags["----:com.apple.iTunes:ISRC"] = mutagen.mp4.MP4FreeForm(self._tags["isrc"])
        if ("cover" in self._tags) and (len(self._tags["cover"]) > 0):
            coverPath = self._tags["cover"]
            f = urllib.urlopen(coverPath)
            tags["covr"] = [mutagen.mp4.MP4Cover(f.read(),
              mutagen.mp4.MP4Cover.FORMAT_PNG if coverPath.endswith('png') else
              mutagen.mp4.MP4Cover.FORMAT_JPEG
            )]
            f.close()

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
            executable = "mp4box.exe" if _windows else "mp4box"
            mp4box     = os.path.join(_getProgramPath(), folderName, executable)

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

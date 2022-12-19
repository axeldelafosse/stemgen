# 🎛 Stemgen

Stemgen is a Stem file generator. Convert any track into a Stem and have fun with Traktor.

A [Stem](https://www.native-instruments.com/en/specials/stems/) file is an open, multi-channel audio file that contains a track split into four musical elements – bass, drums, vocals, and melody, for example. With each element available independently, you have more control over the music you play.

Stemgen uses `demucs` to separate the 4 stems and `ni-stem` to create the Stem file.

![Screenshot Before](./screenshots/before.png)
![Screenshot After](./screenshots/after.png)

Our new file contains four stems: bass, drums, vocals and other.

## Why?

> "It's no secret that I'm fully behind the approach to encourage individuality in creativity and for artists to play differently. Stems is a new format that mirrors my constant quest for spontaneity to drive the art of performance forwards. I hope that releasing my album From My Mind To Yours in this format, mastered by LANDR, inspires others to support the approach and bring even more flexibility to the art of DJing amongst its most progressive supporters." – Richie Hawtin

Stems are fun but nobody's releasing them. Stemgen is a way to create your own stems with only one command.

## Requirement

- demucs https://github.com/facebookresearch/demucs or spleeter https://github.com/deezer/spleeter
- ffmpeg https://www.ffmpeg.org
- sox https://sox.sourceforge.net
- ni-stem (improved version provided in this repo or available at https://www.stems-music.com/stems-is-for-developers)
- jo https://github.com/jpmens/jo
- imagemagick https://imagemagick.org if you want to crop covers

## Usage

- Clone this repo (downloading instead of cloning loses permissions to execute files)
- `$ ./stemgen -i track.wav` or drag and drop a track on `stemgen-droplet`
- Have fun! Your new `.stem.m4a` file is in `output` dir
- Supported input file format are `.wav` `.wave` `.aif` `.aiff` `.flac`

## Quick install on macOS

- `brew install coreutils ffmpeg sox jo imagemagick`
- `pip install demucs` or `pip install spleeter`
- `echo "alias stemgen=/Documents/stemgen/stemgen" >> ~/.zshrc`

## How to customize and create the droplet

I included a slightly modified version of AppleScript-droplet. You can learn more on the repo https://github.com/RichardBronosky/AppleScript-droplet

- Edit `stemgen` with the OUTPUT_PATH you want for example
- Drag and drop `stemgen` on the `script2droplet-droplet` file in Finder

## How to use the droplet

Pro tip: you can put the droplet in your dock

- Drag and drop a single track, multiple tracks or a directory on the `stemgen-droplet`

## Performance

- Stemgen supports 16-bit and 24-bit audio files!
- Stemgen needs to downsample the track to 44.1kHz to avoid problems with the separation software because the models are trained on 44.1kHz audio files.
- You may notice that the output file is pretty big. Apple Lossless Codec (ALAC) for audio encoding is used for lossless audio compression at the cost of increased file size.

![Screenshot Input](./screenshots/flac.png)
![Screenshot Output](./screenshots/alac.png)

## Disclaimer

If you plan to use Stemgen on copyrighted material, make sure you get proper authorization from right owners beforehand.

## License

MIT

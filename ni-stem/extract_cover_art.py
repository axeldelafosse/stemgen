import sys
import os
sys.path.append(os.path.abspath("mutagen"))
from mutagen.wave import WAVE

def extract_cover_art(input_path, output_path):
    # Open the WAVE file using the WAVE class
    wave_file = WAVE(input_path)

    # Check if the WAVE file contains any cover art
    if "APIC:" in wave_file:
        # Extract the cover art from the WAVE file
        cover = wave_file["APIC:"].data

        # Save the cover art to a file
        with open(output_path, "wb") as f:
            f.write(cover)
    else:
        print("Error: The WAVE file does not contain any cover art")

# Read the input and output paths from the command line arguments
input_path = sys.argv[1]
output_path = sys.argv[2]

# Extract the cover art
extract_cover_art(input_path, output_path)

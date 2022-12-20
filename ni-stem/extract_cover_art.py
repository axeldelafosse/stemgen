import sys
import os
sys.path.append(os.path.abspath("mutagen"))
import mutagen

def extract_cover_art(input_path, output_path):
    # Open the file
    file = mutagen.File(input_path)

    # Check if the WAVE file contains any cover art
    if "APIC:" in file:
        # Extract the cover art
        cover = file["APIC:"].data

        # Save the cover art to a file
        with open(output_path, "wb") as f:
            f.write(cover)
    else:
        print("Error: The file does not contain any cover art")

# Read the input and output paths from the command line arguments
input_path = sys.argv[1]
output_path = sys.argv[2]

# Extract the cover art
extract_cover_art(input_path, output_path)

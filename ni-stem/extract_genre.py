import sys
import os
sys.path.append(os.path.abspath("mutagen"))
import mutagen

def extract_genre(input_path, output_path):
    # Open the file
    file = mutagen.File(input_path)

    # Check if the file contains a genre
    if "TCON" in file:
        # Extract the genre
        genre = file["TCON"]

        # Append the genre to a file
        with open(output_path, "a") as f:
            f.write(f"genre={genre}\n")
    else:
        print("Error: The file does not contain a genre")

# Read the input and output paths from the command line arguments
input_path = sys.argv[1]
output_path = sys.argv[2]

# Extract the genre
extract_genre(input_path, output_path)

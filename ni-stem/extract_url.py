import sys
import os
sys.path.append(os.path.abspath("mutagen"))
import mutagen

def extract_url(input_path, output_path):
    # Open the file
    file = mutagen.File(input_path)

    # Check if the file contains a URL
    if "WXXX:" in file:
        # Extract the URL
        url = file["WXXX:"]

        # Append the URL to a file
        with open(output_path, "a") as f:
            f.write(f"url_discogs_release_site={url}\n")
    else:
        print("Error: The file does not contain a URL")

# Read the input and output paths from the command line arguments
input_path = sys.argv[1]
output_path = sys.argv[2]

# Extract the URL
extract_url(input_path, output_path)

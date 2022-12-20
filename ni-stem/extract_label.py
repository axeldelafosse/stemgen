import sys
import os
sys.path.append(os.path.abspath("mutagen"))
import mutagen

def extract_label(input_path, output_path):
    # Open the file using the WAVE class
    file = mutagen.File(input_path)

    # Check if the file contains a label
    if "TPUB" in file:
        # Extract the label
        label = file["TPUB"]

        # Append the label to a file
        with open(output_path, "a") as f:
            f.write(f"label={label}\n")
    else:
        print("Error: The file does not contain a label")

# Read the input and output paths from the command line arguments
input_path = sys.argv[1]
output_path = sys.argv[2]

# Extract the label
extract_label(input_path, output_path)

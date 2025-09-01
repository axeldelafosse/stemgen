import modal
import subprocess
import time
import urllib.request
import unicodedata
from pathlib import Path

volume = modal.Volume.from_name("stemgen", create_if_missing=True)
STEMGEN_DIR = Path("/stemgen")
STEMGEN_INPUT_DIR = STEMGEN_DIR / "input"
STEMGEN_OUTPUT_DIR = STEMGEN_DIR / "output"
STEMGEN_MODELS_DIR = STEMGEN_DIR / "models"

BS_ROFORMER_MODEL_URL = "https://github.com/ZFTurbo/Music-Source-Separation-Training/releases/download/v1.0.12/model_bs_roformer_ep_17_sdr_9.6568.ckpt"
BS_ROFORMER_MODEL_PATH = STEMGEN_MODELS_DIR / "model_bs_roformer_ep_17_sdr_9.6568.ckpt"

image = (
    modal.Image.debian_slim()
    .pip_install(
        "stemgen==2.1.0",
        "Lossless-BS-RoFormer",
        "mutagen",
        "torch"
    )
    .run_commands(
        "apt-get update && apt-get install -y ffmpeg sox git build-essential pkg-config zlib1g-dev",
        "git clone https://github.com/gpac/gpac.git && cd gpac && ./configure && make -j && make install && cd ..",   
    )
)

app = modal.App("stemgen", image=image)

def download_model(url: str, dest_path: Path):
    """Download the model file if it doesn't exist."""
    if not dest_path.exists():
        print(f"Downloading model to {dest_path}...")
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, dest_path)
        print("Model downloaded successfully!")
    else:
        print("Model already exists, skipping download.")

def strip_accents(text):
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore")
    text = text.decode("utf-8")
    return str(text)

@app.function(
    gpu="A10G", # L40S
    timeout=900, # 15 minutes
    volumes={
        STEMGEN_DIR: volume
    },
)
def process_stems(
    input_file_path: str,
):
    """
    Process audio file using Stemgen.
    
    Args:
        input_file_path: Path to the input audio file
    
    Returns:
        dict: Path to the created stem file and additional info
    """    
    STEMGEN_INPUT_DIR.mkdir(exist_ok=True)
    STEMGEN_OUTPUT_DIR.mkdir(exist_ok=True)
    STEMGEN_MODELS_DIR.mkdir(exist_ok=True)
    
    input_path = STEMGEN_INPUT_DIR / input_file_path
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found in volume: {input_path}")

    output_file = STEMGEN_OUTPUT_DIR / strip_accents(f"{input_path.stem}.stem.m4a") 
    if output_file.exists():
        print(f"Using existing output file: {output_file}")
        return {
            "stem_file": str(output_file),
        }

    download_model(BS_ROFORMER_MODEL_URL, BS_ROFORMER_MODEL_PATH)

    cmd = [
        "stemgen",
        "-m",
        str(BS_ROFORMER_MODEL_PATH),
        "-o",
        str(STEMGEN_OUTPUT_DIR),
        str(input_path)
    ]

    print(f"Running command: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )

        while True:
            output = process.stdout.readline()
            error = process.stderr.readline()
            
            if output:
                print(output.rstrip())
            if error:
                print(error.rstrip())
            
            if output == '' and error == '' and process.poll() is not None:
                break
        
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd)
        
        if not output_file.exists():
            raise FileNotFoundError(f"Expected output file not found: {output_file}")
        
        return {
            "stem_file": str(output_file),
        }
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Stemgen failed with error code {e.returncode}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise

@app.local_entrypoint()
def main(
    input_file: str,
):
    """
    Local entrypoint for running stem processing from command line.
    
    Example usage:
    modal run remote.py --input-file path/to/audio.wav
    """
    try:
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found locally: {input_file}")

        remote_path = "/input/" + input_path.name
        print(f"Uploading file to volume: {remote_path}")
        try:
            with volume.batch_upload() as upload:
                upload.put_file(
                    input_path,
                    remote_path
                )
        except Exception as e:
            print(e)

        result = process_stems.remote(
            input_path.name
        )
        
        print("\nStem file created successfully! Waiting 20 seconds before downloading...")

        time.sleep(20)

        remote_stem_file = Path(result['stem_file'])
        cmd = ["modal", "volume", "get", "stemgen", str(remote_stem_file.relative_to(STEMGEN_DIR))]
        print(f"\nDownloading stem file using: {' '.join(cmd)}")
        
        try:
            subprocess.run(cmd, check=True)
            print(f"\nStem file downloaded successfully!")
        except subprocess.CalledProcessError as e:
            print(f"\nError downloading stem file: {e}")

        print("Removing files from volume...")            
        volume.remove_file(remote_path)
        volume.remove_file(str(remote_stem_file.relative_to(STEMGEN_DIR)))
        print("Done :)")
        
    except Exception as e:
        print(f"Error: {e}")

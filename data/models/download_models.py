import urllib.request
import os
from pathlib import Path

def download_file(url, filename):
    """Download a file from a URL to the models directory"""
    try:
        print(f"Downloading {filename}...")
        urllib.request.urlretrieve(url, filename)
        print(f"Successfully downloaded {filename}")
        return True
    except Exception as e:
        print(f"Error downloading {filename}: {e}")
        return False

def main():
    # Create models directory if it doesn't exist
    models_dir = Path(__file__).parent
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Change to models directory
    os.chdir(models_dir)
    
    # Files to download
    files = {
        'coco.names': 'https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names',
        'yolov3.cfg': 'https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3.cfg',
        'yolov3.weights': 'https://pjreddie.com/media/files/yolov3.weights'
    }
    
    # Download each file
    for filename, url in files.items():
        if not Path(filename).exists():
            download_file(url, filename)
        else:
            print(f"{filename} already exists, skipping...")

if __name__ == "__main__":
    main()

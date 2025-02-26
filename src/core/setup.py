import urllib.request
import subprocess
import sys
import os
from pathlib import Path

def download_file(url, output_path):
    print(f"Downloading {output_path}...")
    urllib.request.urlretrieve(url, output_path)
    print(f"Downloaded {output_path} successfully")

def setup_environment():
    # Créer les répertoires nécessaires
    directories = ['recordings', 'known_faces', 'detections', 'backups', 'logs']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"Created directory: {directory}")

    # Installer les dépendances
    print("Installing required packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def download_models():
    # URLs for the files
    yolov3_weights_url = 'https://pjreddie.com/media/files/yolov3.weights'
    yolov3_cfg_url = 'https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3.cfg'
    coco_names_url = 'https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names'

    # Output paths
    yolov3_weights_path = 'yolov3.weights'
    yolov3_cfg_path = 'yolov3.cfg'
    coco_names_path = 'coco.names'

    # Download the files
    files_to_download = [
        (yolov3_weights_url, yolov3_weights_path),
        (yolov3_cfg_url, yolov3_cfg_path),
        (coco_names_url, coco_names_path)
    ]

    for url, path in files_to_download:
        if not os.path.exists(path):
            download_file(url, path)
        else:
            print(f"File {path} already exists, skipping download")

def main():
    try:
        print("Setting up Child Safety System...")
        setup_environment()
        download_models()
        print("\nSetup completed successfully!")
        print("\nYou can now run the application using: python GUI.py")
    except Exception as e:
        print(f"Error during setup: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

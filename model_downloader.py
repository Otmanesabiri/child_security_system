import urllib.request
import os
from pathlib import Path
import sys
import hashlib

def calculate_md5(filename):
    """Calculate MD5 hash of file"""
    hash_md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def download_file(url, filename, expected_md5=None):
    """Download a file with progress bar"""
    try:
        print(f"Downloading {filename}...")
        
        def progress(count, block_size, total_size):
            percent = min(int(count * block_size * 100 / total_size), 100)
            sys.stdout.write(f"\r... {percent}% complete")
            sys.stdout.flush()
            
        urllib.request.urlretrieve(url, filename, reporthook=progress)
        print(f"\nSuccessfully downloaded {filename}")
        
        if expected_md5:
            md5 = calculate_md5(filename)
            if md5 != expected_md5:
                print(f"Warning: MD5 checksum mismatch for {filename}")
                print(f"Expected: {expected_md5}")
                print(f"Got: {md5}")
        
        return True
    except Exception as e:
        print(f"\nError downloading {filename}: {e}")
        return False

def main():
    # Create models directory
    models_dir = Path("data") / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Files to download with their URLs
    files = {
       # 'coco.names': 'https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names',
       # 'yolov3.cfg': 'https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3.cfg',
        'yolov3.weights': 'https://pjreddie.com/media/files/yolov3.weights'
    }
    
    # Expected MD5 checksums
    checksums = {
        'yolov3.weights': '520878f12e97cf820529daea502acca3'  # YOLO v3 weights MD5
    }
    
    # Download each file
    for filename, url in files.items():
        filepath = models_dir / filename
        if not filepath.exists():
            print(f"{filename} not found. Downloading...")
            download_file(url, filepath, checksums.get(filename))
        else:
            print(f"{filename} already exists at {filepath}")
            
            # Verify checksum for weights file
            if filename in checksums:
                md5 = calculate_md5(filepath)
                if md5 != checksums[filename]:
                    print(f"Warning: MD5 checksum mismatch for {filename}")
                    choice = input("Do you want to re-download this file? (y/n): ")
                    if choice.lower() == 'y':
                        download_file(url, filepath, checksums.get(filename))
    
    print("\nAll files downloaded successfully!")
    print(f"Model files are located in: {models_dir.absolute()}")

if __name__ == "__main__":
    main()

from pathlib import Path

required_files = {
    'yolov3.weights': 'https://pjreddie.com/media/files/yolov3.weights',
    'yolov3.cfg': 'https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3.cfg',
    'coco.names': 'https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names'
}

def check_models():
    models_dir = Path(__file__).parent
    missing_files = []
    
    for file_name in required_files:
        if not (models_dir / file_name).exists():
            missing_files.append(file_name)
    
    if missing_files:
        print("Missing required model files:")
        for file_name in missing_files:
            print(f"- {file_name}: Download from {required_files[file_name]}")
        return False
    return True

if __name__ == "__main__":
    check_models()

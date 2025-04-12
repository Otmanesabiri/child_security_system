import sys
from pathlib import Path
import logging
import os
import subprocess

# Add the project root directory to Python path
ROOT_DIR = Path(__file__).parent.absolute()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Configure logging before imports to ensure all modules use the same configuration
os.makedirs('logs', exist_ok=True)  # Create logs directory if it doesn't exist
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join('logs', 'app.log'), mode='a')
    ]
)

logger = logging.getLogger('run')

# Create other required directories
os.makedirs('alerts', exist_ok=True)  # For alert images
os.makedirs('data', exist_ok=True)    # For application data

# Before importing the GUI, check if required packages are installed
try:
    from src.gui.main_window import DangerDetectionApp
    from PyQt5.QtWidgets import QApplication
    from src.core.camera_utils import list_available_cameras, diagnose_camera_issues
except ImportError as e:
    logger.critical(f"Failed to import required modules: {str(e)}")
    print(f"Error: Missing required modules. {str(e)}")
    print("Please install required packages with: pip install PyQt5 opencv-python numpy")
    sys.exit(1)

def check_model_files():
    """Check if required YOLO model files exist"""
    model_dir = ROOT_DIR / 'models'
    os.makedirs(model_dir, exist_ok=True)
    
    required_files = {
        'yolov3.weights': 'https://pjreddie.com/media/files/yolov3.weights',
        'yolov3.cfg': 'https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3.cfg',
        'coco.names': 'https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names'
    }
    
    missing_files = []
    for filename, url in required_files.items():
        filepath = model_dir / filename
        if not filepath.exists():
            missing_files.append((filename, url))
    
    return model_dir, missing_files

def download_file(url, destination):
    """Download a file from URL to destination"""
    try:
        print(f"Downloading {url} to {destination}...")
        if sys.platform.startswith('win'):
            # Windows
            subprocess.check_call(
                ['powershell', '-Command', 
                f"Invoke-WebRequest -Uri '{url}' -OutFile '{destination}'"],
                stderr=subprocess.STDOUT
            )
        else:
            # Linux/Mac
            subprocess.check_call(
                ['wget', '-O', str(destination), url],
                stderr=subprocess.STDOUT
            )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Download failed: {str(e)}")
        return False

def check_camera_availability():
    """Check if any cameras are available"""
    cameras = list_available_cameras()
    if not cameras:
        logger.warning("No cameras detected on the system")
        print("Warning: No cameras detected. Camera functionality will not be available.")
        diagnosis = diagnose_camera_issues()
        print("\nCamera troubleshooting suggestions:")
        for i, suggestion in enumerate(diagnosis['suggestions'], 1):
            print(f"{i}. {suggestion}")
    else:
        logger.info(f"Found {len(cameras)} camera(s): {cameras}")
        print(f"Found {len(cameras)} camera(s): {cameras}")
    return bool(cameras)

def create_default_config():
    """Create default configuration file if it doesn't exist"""
    config_dir = ROOT_DIR / 'config'
    config_path = config_dir / 'config.json'
    os.makedirs(config_dir, exist_ok=True)
    
    if not config_path.exists():
        import json
        default_config = {
            "detection": {
                "dangerous_objects": ["knife", "scissors", "gun", "bottle"],
                "confidence_threshold": 0.5,
                "alert_timeout": 60
            },
            "camera": {
                "preferred_source": 0,
                "resolution": [640, 480],
                "fps": 30
            },
            "notification": {
                "save_alerts": True,
                "send_email": False,
                "email_settings": {
                    "smtp_server": "",
                    "smtp_port": 587,
                    "sender_email": "",
                    "receiver_email": "",
                    "password": ""
                }
            }
        }
        
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        logger.info(f"Created default configuration file at {config_path}")
    
    # Create default style file if it doesn't exist
    style_path = config_dir / 'style.qss'
    if not style_path.exists():
        default_style = """
/* Main Window */
QMainWindow {
    background-color: #f0f0f0;
}

/* Buttons */
QPushButton {
    background-color: #0078d7;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
}

QPushButton:hover {
    background-color: #1084e0;
}

QPushButton:pressed {
    background-color: #006cc1;
}

QPushButton:disabled {
    background-color: #cccccc;
    color: #888888;
}

/* Labels */
QLabel {
    color: #333333;
}

/* Alert messages */
QLabel#alertLabel {
    color: #d32f2f;
    font-weight: bold;
}

/* Status bar */
QStatusBar {
    background-color: #f5f5f5;
    color: #333333;
}
"""
        with open(style_path, 'w') as f:
            f.write(default_style)
        logger.info(f"Created default style file at {style_path}")
    
    return config_path, style_path

def main():
    # Create default config files if needed
    config_path, style_path = create_default_config()
    
    # Check for model files
    model_dir, missing_files = check_model_files()
    if missing_files:
        print(f"Missing required model files. Downloading to {model_dir}...")
        for filename, url in missing_files:
            if not download_file(url, model_dir / filename):
                print(f"Failed to download {filename}. Please download manually from {url}")
                sys.exit(1)
    
    # Check camera availability
    has_cameras = check_camera_availability()
    
    # Initialize QApplication
    app = QApplication(sys.argv)
    
    # Load style
    try:
        with open(style_path, "r") as f:
            app.setStyleSheet(f.read())
        logger.info(f"Loaded style sheet from {style_path}")
    except Exception as e:
        logger.error(f"Error loading style sheet: {str(e)}")
    
    # Create and show main window
    try:
        window = DangerDetectionApp(
            config_path=str(config_path),
            model_dir=str(model_dir),
            has_cameras=has_cameras
        )
        window.show()
        return app.exec_()
    except Exception as e:
        logger.critical(f"Failed to start application: {str(e)}", exc_info=True)
        print(f"Error: Failed to start application: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

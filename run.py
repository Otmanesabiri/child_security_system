import sys
from pathlib import Path
import logging

# Add the project root directory to Python path
ROOT_DIR = Path(__file__).parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.gui import DangerDetectionApp
from PyQt5.QtWidgets import QApplication

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,  # Set logging level to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

def main():
    app = QApplication(sys.argv)
    logger = logging.getLogger('run')
    
    # Load style
    style_path = ROOT_DIR / 'config' / 'style.qss'
    try:
        with open(style_path, "r") as f:
            app.setStyleSheet(f.read())
        logger.info(f"Loaded style sheet from {style_path}")
    except Exception as e:
        logger.error(f"Error loading style sheet: {str(e)}")
        print(f"Error loading style sheet: {str(e)}")
        print(f"Looking for style file at: {style_path}")
    
    window = DangerDetectionApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

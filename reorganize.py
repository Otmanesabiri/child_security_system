import os
import shutil
from pathlib import Path

def create_directory_structure():
    base_path = Path.cwd()
    
    # Définir la structure des dossiers
    directories = [
        'src/core',
        'src/gui',
        'src/utils',
        'src/services',
        'config',
        'data/models',
        'data/database',
        'logs',
        'recordings',
        'exports',
        'backups'
    ]
    
    # Créer les dossiers
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")

def move_files():
    # Définir les déplacements de fichiers
    file_moves = {
        'GUI.py': 'src/gui/main_window.py',
        'setup.py': 'src/core/setup.py',
        'main.py': 'src/core/detection.py',
        'face_recognition_manager.py': 'src/core/face_recognition.py',
        'log_manager.py': 'src/utils/log_manager.py',
        'notification_manager.py': 'src/services/notification_service.py',
        'analytics_manager.py': 'src/services/analytics_service.py',
        'backup_manager.py': 'src/utils/backup_manager.py',
        'style.qss': 'config/style.qss',
        'settings.json': 'config/settings.json',
        'cloud_config.json': 'config/cloud_config.json'
    }
    
    # Déplacer les fichiers
    for source, dest in file_moves.items():
        if os.path.exists(source):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.move(source, dest)
            print(f"Moved {source} to {dest}")

def create_init_files():
    # Créer les fichiers __init__.py dans chaque package
    python_dirs = [
        'src',
        'src/core',
        'src/gui',
        'src/utils',
        'src/services'
    ]
    
    for directory in python_dirs:
        init_file = Path(directory) / '__init__.py'
        if not init_file.exists():
            init_file.touch()
            print(f"Created {init_file}")

def main():
    print("Starting project reorganization...")
    create_directory_structure()
    move_files()
    create_init_files()
    print("Project reorganization completed!")

if __name__ == "__main__":
    main()

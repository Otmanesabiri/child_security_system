import requests
import json
import hashlib
import os
import sys
import logging
import subprocess
from pathlib import Path
import shutil
from datetime import datetime

class SystemUpdater:
    def __init__(self, config_path='config.json'):
        self.setup_logging()
        self.version_file = 'version.json'
        self.backup_dir = Path('backups/system')
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def setup_logging(self):
        self.logger = logging.getLogger('DangerDetection.Updater')
        
    def check_for_updates(self, current_version):
        """Vérifie si des mises à jour sont disponibles"""
        try:
            # Dans une version réelle, ceci vérifierait un serveur distant
            # Pour l'exemple, nous utilisons un fichier local
            if os.path.exists(self.version_file):
                with open(self.version_file, 'r') as f:
                    latest_version = json.load(f)
                    
                if latest_version['version'] > current_version:
                    return True, latest_version
            return False, None
            
        except Exception as e:
            self.logger.error(f"Failed to check for updates: {str(e)}")
            return False, None
            
    def backup_current_system(self):
        """Crée une sauvegarde du système actuel"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = self.backup_dir / f"system_backup_{timestamp}"
            
            # Sauvegarder les fichiers importants
            files_to_backup = [
                '*.py',
                '*.json',
                '*.qss',
                'requirements.txt',
                'README.md'
            ]
            
            for pattern in files_to_backup:
                for file in Path('.').glob(pattern):
                    if file.is_file():
                        dest = backup_path / file.name
                        shutil.copy2(file, dest)
                        
            self.logger.info(f"System backup created at: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            self.logger.error(f"Backup failed: {str(e)}")
            return None
            
    def verify_file_integrity(self, file_path, expected_hash):
        """Vérifie l'intégrité d'un fichier"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            return file_hash == expected_hash
        except Exception as e:
            self.logger.error(f"Integrity check failed for {file_path}: {str(e)}")
            return False
            
    def update_system(self, update_info):
        """Met à jour le système"""
        try:
            # Créer une sauvegarde avant la mise à jour
            backup_path = self.backup_current_system()
            if not backup_path:
                raise Exception("Failed to create backup")
                
            # Dans une version réelle, téléchargerait les fichiers depuis un serveur
            # Pour l'exemple, nous simulons une mise à jour locale
            
            # Mettre à jour les dépendances si nécessaire
            if 'requirements' in update_info:
                self._update_requirements()
                
            # Mettre à jour la configuration si nécessaire
            if 'config_updates' in update_info:
                self._update_config(update_info['config_updates'])
                
            # Mettre à jour la version
            self._update_version(update_info['version'])
            
            self.logger.info("System updated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Update failed: {str(e)}")
            if backup_path:
                self.restore_backup(backup_path)
            return False
            
    def _update_requirements(self):
        """Met à jour les dépendances Python"""
        try:
            subprocess.check_call([
                sys.executable, 
                "-m", 
                "pip", 
                "install", 
                "-r", 
                "requirements.txt"
            ])
            self.logger.info("Dependencies updated successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to update dependencies: {str(e)}")
            raise
            
    def _update_config(self, config_updates):
        """Met à jour le fichier de configuration"""
        try:
            config_path = 'config.json'
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    current_config = json.load(f)
                    
                # Mettre à jour la configuration récursivement
                self._update_dict_recursive(current_config, config_updates)
                
                with open(config_path, 'w') as f:
                    json.dump(current_config, f, indent=4)
                    
            self.logger.info("Configuration updated successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to update configuration: {str(e)}")
            raise
            
    def _update_dict_recursive(self, current, updates):
        """Met à jour un dictionnaire de manière récursive"""
        for key, value in updates.items():
            if key in current and isinstance(current[key], dict) and isinstance(value, dict):
                self._update_dict_recursive(current[key], value)
            else:
                current[key] = value
                
    def _update_version(self, new_version):
        """Met à jour le fichier de version"""
        try:
            version_info = {
                'version': new_version,
                'update_date': datetime.now().isoformat()
            }
            
            with open(self.version_file, 'w') as f:
                json.dump(version_info, f, indent=4)
                
            self.logger.info(f"Version updated to {new_version}")
            
        except Exception as e:
            self.logger.error(f"Failed to update version: {str(e)}")
            raise
            
    def restore_backup(self, backup_path):
        """Restaure une sauvegarde du système"""
        try:
            backup_path = Path(backup_path)
            if not backup_path.exists():
                raise Exception("Backup path does not exist")
                
            # Restaurer tous les fichiers
            for file in backup_path.glob('*'):
                if file.is_file():
                    shutil.copy2(file, Path('.') / file.name)
                    
            self.logger.info(f"System restored from backup: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore backup: {str(e)}")
            return False
            
    def cleanup_old_backups(self, max_backups=5):
        """Nettoie les anciennes sauvegardes du système"""
        try:
            backups = sorted(self.backup_dir.glob('system_backup_*'))
            if len(backups) > max_backups:
                for backup in backups[:-max_backups]:
                    shutil.rmtree(backup)
                    self.logger.info(f"Removed old backup: {backup}")
                    
        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups: {str(e)}")

def main():
    """Point d'entrée pour les mises à jour manuelles"""
    updater = SystemUpdater()
    current_version = "1.0.0"  # À récupérer depuis version.json
    
    print("Checking for updates...")
    has_update, update_info = updater.check_for_updates(current_version)
    
    if has_update:
        print(f"New version available: {update_info['version']}")
        response = input("Do you want to update? (y/n): ")
        
        if response.lower() == 'y':
            if updater.update_system(update_info):
                print("Update completed successfully!")
            else:
                print("Update failed. System restored to previous version.")
    else:
        print("No updates available.")

if __name__ == "__main__":
    main()
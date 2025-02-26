import shutil
import sqlite3
from datetime import datetime
import json
import logging
from pathlib import Path
import threading
import schedule
import time
import os

class BackupManager:
    def __init__(self, config_path='config.json'):
        self.load_config(config_path)
        self.setup_logging()
        self.setup_backup_scheduler()
        
    def load_config(self, config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
            self.backup_config = config['database']['backup']
            self.db_path = config['database']['path']
            
    def setup_logging(self):
        self.logger = logging.getLogger('DangerDetection.Backup')
        
    def setup_backup_scheduler(self):
        """Configure le planificateur de sauvegardes"""
        if self.backup_config['enabled']:
            schedule.every(self.backup_config['interval_hours']).hours.do(self.create_backup)
            
            # Démarrer le thread du planificateur
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()
            
    def _run_scheduler(self):
        """Exécute le planificateur en arrière-plan"""
        while True:
            schedule.run_pending()
            time.sleep(60)
            
    def create_backup(self):
        """Crée une sauvegarde de la base de données"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = Path(self.backup_config['backup_path'])
            backup_dir.mkdir(exist_ok=True)
            
            # Nom du fichier de sauvegarde
            backup_path = backup_dir / f"backup_{timestamp}.db"
            
            # Créer une copie de la base de données
            with sqlite3.connect(self.db_path) as src_conn:
                # Vider le cache et forcer l'écriture sur le disque
                src_conn.execute("PRAGMA wal_checkpoint(FULL)")
                
            # Copier le fichier
            shutil.copy2(self.db_path, backup_path)
            
            # Compresser la sauvegarde
            self._compress_backup(backup_path)
            
            # Nettoyer les anciennes sauvegardes
            self._cleanup_old_backups()
            
            self.logger.info(f"Backup created successfully: {backup_path}.gz")
            return True
            
        except Exception as e:
            self.logger.error(f"Backup failed: {str(e)}")
            return False
            
    def _compress_backup(self, backup_path):
        """Compresse le fichier de sauvegarde"""
        try:
            # Compresser avec gzip
            with open(backup_path, 'rb') as f_in:
                with open(f"{backup_path}.gz", 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
                    
            # Supprimer le fichier non compressé
            os.remove(backup_path)
            
        except Exception as e:
            self.logger.error(f"Compression failed: {str(e)}")
            
    def _cleanup_old_backups(self):
        """Nettoie les anciennes sauvegardes"""
        try:
            backup_dir = Path(self.backup_config['backup_path'])
            backups = sorted(backup_dir.glob("*.gz"))
            
            # Garder seulement le nombre spécifié de sauvegardes
            max_backups = self.backup_config['max_backups']
            if len(backups) > max_backups:
                for backup in backups[:-max_backups]:
                    os.remove(backup)
                    self.logger.info(f"Removed old backup: {backup}")
                    
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            
    def restore_backup(self, backup_path):
        """Restaure une sauvegarde"""
        try:
            # Vérifier si le fichier est compressé
            if backup_path.endswith('.gz'):
                # Décompresser d'abord
                uncompressed_path = backup_path[:-3]
                with open(backup_path, 'rb') as f_in:
                    with open(uncompressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                backup_path = uncompressed_path
            
            # Créer une sauvegarde de la base actuelle avant la restauration
            current_backup = self.create_backup()
            if not current_backup:
                raise Exception("Failed to backup current database")
            
            # Restaurer la sauvegarde
            shutil.copy2(backup_path, self.db_path)
            
            # Nettoyer le fichier décompressé si nécessaire
            if os.path.exists(backup_path) and backup_path.endswith('.db'):
                os.remove(backup_path)
                
            self.logger.info(f"Backup restored successfully from: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Restore failed: {str(e)}")
            return False
            
    def list_backups(self):
        """Liste toutes les sauvegardes disponibles"""
        try:
            backup_dir = Path(self.backup_config['backup_path'])
            backups = []
            
            for backup in backup_dir.glob("*.gz"):
                backup_info = {
                    'path': str(backup),
                    'size': os.path.getsize(backup),
                    'date': datetime.fromtimestamp(os.path.getmtime(backup))
                }
                backups.append(backup_info)
                
            return sorted(backups, key=lambda x: x['date'], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Failed to list backups: {str(e)}")
            return []
            
    def verify_backup(self, backup_path):
        """Vérifie l'intégrité d'une sauvegarde"""
        try:
            # Décompresser temporairement si nécessaire
            temp_path = None
            if backup_path.endswith('.gz'):
                temp_path = backup_path[:-3]
                with open(backup_path, 'rb') as f_in:
                    with open(temp_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                backup_path = temp_path
            
            # Vérifier si le fichier est une base SQLite valide
            with sqlite3.connect(backup_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()[0]
                
            # Nettoyer le fichier temporaire
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
                
            is_valid = result == "ok"
            if is_valid:
                self.logger.info(f"Backup verified successfully: {backup_path}")
            else:
                self.logger.warning(f"Backup verification failed: {backup_path}")
                
            return is_valid
            
        except Exception as e:
            self.logger.error(f"Backup verification failed: {str(e)}")
            return False
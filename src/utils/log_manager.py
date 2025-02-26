import logging
import logging.handlers
from pathlib import Path
import json
from datetime import datetime
import os
import gzip
import shutil
import cv2  # Added import for cv2

class LogManager:
    def __init__(self, config_path='config.json'):
        self.load_config(config_path)
        self.setup_logging()
        
    def load_config(self, config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
            self.log_level = config['system']['log_level']
            self.save_debug_frames = config['system']['save_debug_frames']
            
    def setup_logging(self):
        # Créer le dossier logs s'il n'existe pas
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # Configuration du logger principal
        logger = logging.getLogger('DangerDetection')
        logger.setLevel(getattr(logging, self.log_level))
        
        # Handler pour tous les logs
        main_handler = logging.handlers.TimedRotatingFileHandler(
            'logs/danger_detection.log',
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        main_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(main_handler)
        
        # Handler spécifique pour les erreurs
        error_handler = logging.handlers.RotatingFileHandler(
            'logs/errors.log',
            maxBytes=1024*1024,  # 1MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n'
            'Exception:\n%(exc_info)s'
        ))
        logger.addHandler(error_handler)
        
        # Handler pour la console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        self.logger = logger
        
    def compress_old_logs(self):
        """Compresse les anciens fichiers de log"""
        log_dir = Path('logs')
        for log_file in log_dir.glob('*.log.*'):
            if not log_file.name.endswith('.gz'):
                with open(log_file, 'rb') as f_in:
                    with gzip.open(f'{log_file}.gz', 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(log_file)
                
    def save_debug_frame(self, frame, event_type):
        """Sauvegarde une image pour le débogage"""
        if self.save_debug_frames:
            debug_dir = Path('logs/debug_frames')
            debug_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{event_type}_{timestamp}.jpg"
            path = debug_dir / filename
            
            try:
                cv2.imwrite(str(path), frame)
                self.logger.debug(f"Saved debug frame: {filename}")
            except Exception as e:
                self.logger.error(f"Failed to save debug frame: {str(e)}")
                
    def log_detection(self, object_name, confidence, location):
        """Log une détection d'objet"""
        self.logger.info(
            f"Detection: {object_name} (confidence: {confidence:.2f}) "
            f"at location: {location}"
        )
        
    def log_face_recognition(self, name, confidence):
        """Log une reconnaissance faciale"""
        self.logger.info(
            f"Face recognized: {name} (confidence: {confidence:.2f})"
        )
        
    def log_system_status(self, cpu_usage, memory_usage, fps):
        """Log les statistiques système"""
        self.logger.debug(
            f"System Status - CPU: {cpu_usage}%, Memory: {memory_usage}MB, "
            f"FPS: {fps:.1f}"
        )
        
    def log_error(self, error_type, message, exc_info=None):
        """Log une erreur avec les détails de l'exception"""
        self.logger.error(
            f"Error ({error_type}): {message}",
            exc_info=exc_info if exc_info else False
        )
        
    def log_notification(self, notification_type, status, details=None):
        """Log l'envoi d'une notification"""
        self.logger.info(
            f"Notification ({notification_type}) - Status: {status}"
            + (f", Details: {details}" if details else "")
        )
        
    def cleanup_old_logs(self, days=30):
        """Nettoie les vieux fichiers de log"""
        log_dir = Path('logs')
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        for log_file in log_dir.glob('**/*'):
            if log_file.is_file():
                if log_file.stat().st_mtime < cutoff:
                    try:
                        os.remove(log_file)
                        self.logger.debug(f"Removed old log file: {log_file}")
                    except Exception as e:
                        self.logger.error(f"Failed to remove old log: {str(e)}")

    def get_recent_events(self, minutes=30):
        """Récupère les événements récents des logs"""
        events = []
        try:
            with open('logs/danger_detection.log', 'r', encoding='utf-8') as f:
                for line in f:
                    if ' - Detection:' in line or ' - Face recognized:' in line:
                        events.append(line.strip())
        except Exception as e:
            self.logger.error(f"Failed to get recent events: {str(e)}")
        return events[-50:]  # Retourne les 50 derniers événements
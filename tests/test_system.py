import pytest
import os
import json
import sqlite3
from pathlib import Path

@pytest.fixture
def test_db():
    """Crée une base de données temporaire pour les tests"""
    db_path = "test_danger_detection.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Créer les tables nécessaires
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY,
            object TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            confidence REAL,
            location TEXT
        )
    ''')
    
    conn.commit()
    
    yield db_path
    
    # Nettoyage
    conn.close()
    os.remove(db_path)

@pytest.fixture
def test_config():
    """Crée une configuration de test"""
    config = {
        "detection": {
            "confidence_threshold": 0.5,
            "dangerous_objects": ["knife", "scissors"],
            "alert_timeout": 5
        },
        "face_recognition": {
            "enabled": True,
            "confidence_threshold": 0.6
        },
        "camera": {
            "primary": {
                "id": 0,
                "resolution": {"width": 640, "height": 480}
            }
        }
    }
    
    config_path = "test_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f)
        
    yield config_path
    
    # Nettoyage
    os.remove(config_path)

@pytest.fixture
def test_dirs():
    """Crée les répertoires temporaires pour les tests"""
    dirs = ["test_recordings", "test_backups", "test_logs"]
    for d in dirs:
        Path(d).mkdir(exist_ok=True)
        
    yield dirs
    
    # Nettoyage
    for d in dirs:
        shutil.rmtree(d, ignore_errors=True)

# Tests pour ObjectDetector
def test_object_detector_initialization(test_config):
    from main import ObjectDetector
    detector = ObjectDetector(test_config)
    assert detector.confidence_threshold == 0.5
    assert "knife" in detector.dangerous_objects

# Tests pour FaceRecognitionManager
def test_face_recognition_manager(test_dirs):
    from face_recognition_manager import FaceRecognitionManager
    manager = FaceRecognitionManager(known_faces_dir=test_dirs[0])
    assert Path(test_dirs[0]).exists()

# Tests pour BackupManager
def test_backup_manager(test_config, test_dirs):
    from backup_manager import BackupManager
    manager = BackupManager(test_config)
    assert manager.backup_config['enabled'] == True

# Tests pour StatsAnalyzer
def test_stats_analyzer(test_db):
    from stats_analyzer import StatsAnalyzer
    analyzer = StatsAnalyzer(db_path=test_db)
    stats = analyzer.generate_alerts_summary()
    assert isinstance(stats, dict)

# Tests pour LogManager
def test_log_manager(test_config, test_dirs):
    from log_manager import LogManager
    manager = LogManager(test_config)
    assert Path("logs").exists()

# Tests pour SystemUpdater
def test_system_updater(test_config):
    from updater import SystemUpdater
    updater = SystemUpdater(test_config)
    has_update, _ = updater.check_for_updates("0.9.0")
    assert isinstance(has_update, bool)

# Tests d'intégration
def test_full_system_integration(test_config, test_db, test_dirs):
    from main import ObjectDetector
    from face_recognition_manager import FaceRecognitionManager
    from backup_manager import BackupManager
    
    # Initialiser tous les composants
    detector = ObjectDetector(test_config)
    face_manager = FaceRecognitionManager(test_dirs[0])
    backup_manager = BackupManager(test_config)
    
    # Vérifier que tout est correctement initialisé
    assert detector.is_running == False
    assert Path(test_dirs[0]).exists()
    assert backup_manager is not None
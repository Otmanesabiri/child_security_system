import sqlite3
from datetime import datetime, timedelta
import json
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import logging

class AnalyticsManager:
    def __init__(self, db_path='danger_detection.db', config_path='config.json'):
        self.db_path = db_path
        self.config = self._load_config(config_path)
        self.setup_logging()
        self.init_database()
        
    def _load_config(self, config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def setup_logging(self):
        logging.basicConfig(
            filename='analytics.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def init_database(self):
        """Initialise la base de données avec des tables améliorées"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Table des alertes améliorée
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY,
                        object TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        image_path TEXT,
                        notification_sent BOOLEAN DEFAULT FALSE,
                        location TEXT,
                        processed BOOLEAN DEFAULT FALSE
                    )
                ''')
                
                # Table des statistiques journalières
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS daily_stats (
                        date DATE PRIMARY KEY,
                        total_alerts INTEGER,
                        unique_objects INTEGER,
                        avg_confidence REAL
                    )
                ''')
                
                conn.commit()
                logging.info("Database initialized successfully")
                
        except Exception as e:
            logging.error(f"Database initialization failed: {str(e)}")
    
    def add_alert(self, object_name, confidence, image_path=None, location=None):
        """Ajoute une nouvelle alerte dans la base de données"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO alerts (object, confidence, image_path, location)
                    VALUES (?, ?, ?, ?)
                ''', (object_name, confidence, image_path, location))
                conn.commit()
                logging.info(f"Alert added: {object_name}")
                return cursor.lastrowid
        except Exception as e:
            logging.error(f"Failed to add alert: {str(e)}")
            return None
    
    def get_daily_statistics(self):
        """Retourne les statistiques du jour"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                today = datetime.now().strftime('%Y-%m-%d')
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        COUNT(DISTINCT object) as unique_objects,
                        AVG(confidence) as avg_confidence
                    FROM alerts
                    WHERE date(timestamp) = ?
                ''', (today,))
                return cursor.fetchone()
        except Exception as e:
            logging.error(f"Failed to get daily statistics: {str(e)}")
            return (0, 0, 0.0)
    
    def generate_weekly_report(self, output_dir='reports'):
        """Génère un rapport hebdomadaire avec graphiques"""
        try:
            Path(output_dir).mkdir(exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                # Charger les données dans un DataFrame
                df = pd.read_sql_query('''
                    SELECT 
                        date(timestamp) as date,
                        object,
                        confidence
                    FROM alerts
                    WHERE timestamp >= date('now', '-7 days')
                ''', conn)
                
                # Créer des graphiques
                plt.figure(figsize=(15, 10))
                
                # Graphique 1: Détections par jour
                plt.subplot(2, 2, 1)
                df['date'].value_counts().sort_index().plot(kind='bar')
                plt.title('Détections par jour')
                plt.xticks(rotation=45)
                
                # Graphique 2: Types d'objets détectés
                plt.subplot(2, 2, 2)
                df['object'].value_counts().plot(kind='pie', autopct='%1.1f%%')
                plt.title('Distribution des objets détectés')
                
                # Graphique 3: Niveau de confiance moyen par objet
                plt.subplot(2, 2, 3)
                df.groupby('object')['confidence'].mean().plot(kind='bar')
                plt.title('Niveau de confiance moyen par objet')
                plt.xticks(rotation=45)
                
                # Sauvegarder le rapport
                timestamp = datetime.now().strftime('%Y%m%d')
                report_path = Path(output_dir) / f'weekly_report_{timestamp}.pdf'
                plt.tight_layout()
                plt.savefig(report_path)
                plt.close()
                
                logging.info(f"Weekly report generated: {report_path}")
                return str(report_path)
                
        except Exception as e:
            logging.error(f"Failed to generate weekly report: {str(e)}")
            return None
    
    def cleanup_old_records(self):
        """Nettoie les anciennes entrées selon la configuration"""
        try:
            retention_days = self.config['database']['retention_days']
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM alerts 
                    WHERE timestamp < datetime('now', ?)
                ''', (f'-{retention_days} days',))
                conn.commit()
                logging.info(f"Cleaned up records older than {retention_days} days")
        except Exception as e:
            logging.error(f"Failed to cleanup old records: {str(e)}")
    
    def export_alerts(self, start_date=None, end_date=None, format='csv'):
        """Exporte les alertes dans différents formats"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = 'SELECT * FROM alerts WHERE 1=1'
                params = []
                
                if start_date:
                    query += ' AND timestamp >= ?'
                    params.append(start_date)
                if end_date:
                    query += ' AND timestamp <= ?'
                    params.append(end_date)
                
                df = pd.read_sql_query(query, conn, params=params)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                if format == 'csv':
                    output_path = f'exports/alerts_export_{timestamp}.csv'
                    df.to_csv(output_path, index=False)
                elif format == 'excel':
                    output_path = f'exports/alerts_export_{timestamp}.xlsx'
                    df.to_excel(output_path, index=False)
                elif format == 'json':
                    output_path = f'exports/alerts_export_{timestamp}.json'
                    df.to_json(output_path, orient='records')
                
                logging.info(f"Alerts exported to {output_path}")
                return output_path
                
        except Exception as e:
            logging.error(f"Failed to export alerts: {str(e)}")
            return None
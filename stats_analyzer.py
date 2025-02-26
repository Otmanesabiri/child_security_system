import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
import json
import logging
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import io

class StatsAnalyzer:
    def __init__(self, db_path='danger_detection.db', config_path='config.json'):
        self.db_path = db_path
        self.load_config(config_path)
        self.setup_logging()
        
    def load_config(self, config_path):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
            
    def setup_logging(self):
        self.logger = logging.getLogger('DangerDetection.Stats')
        
    def get_connection(self):
        return sqlite3.connect(self.db_path)
        
    def generate_daily_report(self):
        """Génère un rapport quotidien des détections"""
        try:
            with self.get_connection() as conn:
                df = pd.read_sql_query("""
                    SELECT 
                        object,
                        strftime('%Y-%m-%d', timestamp) as date,
                        COUNT(*) as count
                    FROM alerts 
                    WHERE timestamp >= date('now', '-30 days')
                    GROUP BY object, date
                    ORDER BY date DESC
                """, conn)
                
                # Créer le graphique
                fig = Figure(figsize=(12, 6))
                ax = fig.add_subplot(111)
                
                pivot_table = df.pivot(index='date', columns='object', values='count').fillna(0)
                pivot_table.plot(kind='bar', stacked=True, ax=ax)
                
                ax.set_title('Détections par jour et par type d\'objet')
                ax.set_xlabel('Date')
                ax.set_ylabel('Nombre de détections')
                plt.xticks(rotation=45)
                
                # Sauvegarder le graphique
                reports_dir = Path('reports')
                reports_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d')
                fig.savefig(f'reports/daily_report_{timestamp}.png', 
                          bbox_inches='tight', dpi=300)
                
                return self.generate_summary_stats(df)
                
        except Exception as e:
            self.logger.error(f"Error generating daily report: {str(e)}")
            return None
            
    def generate_summary_stats(self, df):
        """Génère des statistiques résumées"""
        stats = {
            'total_detections': int(df['count'].sum()),
            'unique_objects': len(df['object'].unique()),
            'most_common_object': df.groupby('object')['count'].sum().idxmax(),
            'busiest_day': df.groupby('date')['count'].sum().idxmax(),
            'average_daily_detections': float(df.groupby('date')['count'].sum().mean())
        }
        return stats
        
    def generate_heatmap(self, days=7):
        """Génère une heatmap des détections par heure et jour"""
        try:
            with self.get_connection() as conn:
                df = pd.read_sql_query("""
                    SELECT 
                        strftime('%w', timestamp) as day_of_week,
                        strftime('%H', timestamp) as hour,
                        COUNT(*) as count
                    FROM alerts 
                    WHERE timestamp >= date('now', ?)
                    GROUP BY day_of_week, hour
                """, conn, params=(f'-{days} days',))
                
                # Créer la heatmap
                pivot_table = df.pivot(index='day_of_week', 
                                     columns='hour', 
                                     values='count').fillna(0)
                
                fig = Figure(figsize=(12, 8))
                ax = fig.add_subplot(111)
                
                sns.heatmap(pivot_table, annot=True, fmt='.0f', 
                          cmap='YlOrRd', ax=ax)
                
                ax.set_title('Heatmap des détections')
                ax.set_xlabel('Heure')
                ax.set_ylabel('Jour de la semaine')
                
                # Sauvegarder la heatmap
                timestamp = datetime.now().strftime('%Y%m%d')
                fig.savefig(f'reports/heatmap_{timestamp}.png', 
                          bbox_inches='tight', dpi=300)
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error generating heatmap: {str(e)}")
            return False
            
    def get_trend_analysis(self, days=30):
        """Analyse les tendances des détections"""
        try:
            with self.get_connection() as conn:
                df = pd.read_sql_query("""
                    SELECT 
                        object,
                        timestamp,
                        COUNT(*) as count
                    FROM alerts 
                    WHERE timestamp >= date('now', ?)
                    GROUP BY object, date(timestamp)
                """, conn, params=(f'-{days} days',))
                
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                trends = {}
                for obj in df['object'].unique():
                    obj_data = df[df['object'] == obj]
                    if len(obj_data) > 1:
                        # Calculer la tendance (croissante/décroissante)
                        z = np.polyfit(range(len(obj_data)), 
                                     obj_data['count'], 1)
                        trend = 'croissante' if z[0] > 0 else 'décroissante'
                        
                        # Calculer le changement en pourcentage
                        first_week = obj_data.head(7)['count'].mean()
                        last_week = obj_data.tail(7)['count'].mean()
                        if first_week > 0:
                            change_pct = ((last_week - first_week) / first_week) * 100
                        else:
                            change_pct = 0
                            
                        trends[obj] = {
                            'trend': trend,
                            'change_percentage': change_pct,
                            'average_daily': obj_data['count'].mean(),
                            'max_daily': obj_data['count'].max(),
                            'total_detections': obj_data['count'].sum()
                        }
                
                return trends
                
        except Exception as e:
            self.logger.error(f"Error analyzing trends: {str(e)}")
            return None
            
    def generate_alerts_summary(self):
        """Génère un résumé des alertes pour l'interface"""
        try:
            with self.get_connection() as conn:
                today = datetime.now().strftime('%Y-%m-%d')
                
                # Statistiques du jour
                today_stats = pd.read_sql_query("""
                    SELECT object, COUNT(*) as count
                    FROM alerts 
                    WHERE date(timestamp) = ?
                    GROUP BY object
                """, conn, params=(today,))
                
                # Statistiques de la semaine
                week_stats = pd.read_sql_query("""
                    SELECT object, COUNT(*) as count
                    FROM alerts 
                    WHERE timestamp >= date('now', '-7 days')
                    GROUP BY object
                """, conn)
                
                return {
                    'today': {
                        'total': int(today_stats['count'].sum()),
                        'by_object': today_stats.set_index('object')['count'].to_dict()
                    },
                    'week': {
                        'total': int(week_stats['count'].sum()),
                        'by_object': week_stats.set_index('object')['count'].to_dict(),
                        'daily_average': float(week_stats['count'].sum() / 7)
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error generating alerts summary: {str(e)}")
            return None
            
    def export_statistics(self, start_date=None, end_date=None, format='csv'):
        """Exporte les statistiques dans différents formats"""
        try:
            with self.get_connection() as conn:
                query = """
                    SELECT 
                        object,
                        timestamp,
                        COUNT(*) as count
                    FROM alerts 
                    WHERE 1=1
                """
                params = []
                
                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(start_date)
                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(end_date)
                    
                query += " GROUP BY object, date(timestamp)"
                
                df = pd.read_sql_query(query, conn, params=params)
                
                # Créer le dossier d'export
                export_dir = Path('exports')
                export_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                if format == 'csv':
                    output_path = export_dir / f'stats_export_{timestamp}.csv'
                    df.to_csv(output_path, index=False)
                elif format == 'excel':
                    output_path = export_dir / f'stats_export_{timestamp}.xlsx'
                    df.to_excel(output_path, index=False)
                elif format == 'json':
                    output_path = export_dir / f'stats_export_{timestamp}.json'
                    df.to_json(output_path, orient='records')
                    
                return str(output_path)
                
        except Exception as e:
            self.logger.error(f"Error exporting statistics: {str(e)}")
            return None
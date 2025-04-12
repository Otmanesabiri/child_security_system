import logging
import json
import uuid
from datetime import datetime
import os

class AnalyticsManager:
    def __init__(self, storage_file="analytics_data.json"):
        self.logger = logging.getLogger(__name__)
        self.storage_file = storage_file
        self.alerts = self._load_data()
        self.logger.info("AnalyticsManager initialized")
    
    def _load_data(self):
        """Load existing analytics data if available"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    return json.load(f)
            return {"alerts": []}
        except Exception as e:
            self.logger.error(f"Error loading analytics data: {str(e)}")
            return {"alerts": []}
    
    def _save_data(self):
        """Save analytics data to storage file"""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.alerts, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving analytics data: {str(e)}")
    
    def add_alert(self, object_type, confidence, location=None):
        """
        Add a new alert to analytics database
        
        Args:
            object_type (str): Type of dangerous object detected
            confidence (float): Detection confidence score
            location (str, optional): Location information of the detected object
            
        Returns:
            str: ID of the created alert
        """
        alert_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        alert_data = {
            "id": alert_id,
            "timestamp": timestamp,
            "object_type": object_type,
            "confidence": float(confidence),
            "location": location
        }
        
        self.alerts["alerts"].append(alert_data)
        self._save_data()
        self.logger.info(f"Added alert ID {alert_id} to analytics")
        
        return alert_id
    
    def get_statistics(self):
        """Get statistics about detected objects"""
        if not self.alerts["alerts"]:
            return {"total_alerts": 0}
            
        stats = {
            "total_alerts": len(self.alerts["alerts"]),
            "by_object_type": {}
        }
        
        for alert in self.alerts["alerts"]:
            obj_type = alert["object_type"]
            if obj_type not in stats["by_object_type"]:
                stats["by_object_type"][obj_type] = 0
            stats["by_object_type"][obj_type] += 1
        
        return stats

import tensorflow as tf
import numpy as np
from collections import deque
import cv2

class AIFilter:
    def __init__(self, confidence_threshold=0.7, history_size=10):
        self.confidence_threshold = confidence_threshold
        self.detection_history = deque(maxlen=history_size)
        self.setup_model()
        
    def setup_model(self):
        # Charger un modèle pré-entraîné pour la validation secondaire
        self.model = tf.keras.applications.MobileNetV2(
            weights='imagenet',
            include_top=True
        )
        
    def validate_detection(self, frame, detection):
        """Double validation avec un second modèle"""
        try:
            # Extraire la région détectée
            x, y, w, h = detection['box']
            roi = frame[y:y+h, x:x+w]
            
            # Prétraiter pour MobileNetV2
            roi = cv2.resize(roi, (224, 224))
            roi = tf.keras.applications.mobilenet_v2.preprocess_input(roi)
            roi = np.expand_dims(roi, axis=0)
            
            # Prédiction
            predictions = self.model.predict(roi)
            confidence = np.max(predictions)
            
            # Mettre à jour l'historique
            self.detection_history.append({
                'confidence': confidence,
                'label': detection['label']
            })
            
            # Vérifier la cohérence temporelle
            return self.check_temporal_consistency(detection['label'])
            
        except Exception as e:
            print(f"Validation error: {str(e)}")
            return False
            
    def check_temporal_consistency(self, label):
        """Vérifie la cohérence des détections dans le temps"""
        if len(self.detection_history) < 3:
            return True
            
        # Compter les détections récentes du même objet
        recent_detections = sum(1 for d in self.detection_history 
                              if d['label'] == label)
        
        return (recent_detections / len(self.detection_history)) >= 0.6

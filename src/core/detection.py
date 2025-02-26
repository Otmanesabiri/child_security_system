import cv2
import numpy as np
import json
from pathlib import Path
from notification_manager import NotificationManager
from analytics_manager import AnalyticsManager
import logging
from datetime import datetime
import threading
import queue

class ObjectDetector:
    def __init__(self, config_path='config.json'):
        self.load_config(config_path)
        self.setup_logging()
        self.init_yolo()
        self.notification_manager = NotificationManager()
        self.analytics_manager = AnalyticsManager()
        self.frame_queue = queue.Queue(maxsize=30)
        self.detection_thread = None
        self.is_running = False
        self.last_detections = {}  # Pour éviter les alertes répétées
        
    def load_config(self, config_path):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
            self.dangerous_objects = set(self.config['detection']['dangerous_objects'])
            self.confidence_threshold = self.config['detection']['confidence_threshold']
            self.alert_timeout = self.config['detection']['alert_timeout']
    
    def setup_logging(self):
        logging.basicConfig(
            filename='detection.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def init_yolo(self):
        try:
            self.net = cv2.dnn.readNet("yolov3.weights", "yolov3.cfg")
            self.layer_names = self.net.getLayerNames()
            self.output_layers = [self.layer_names[i - 1] for i in self.net.getUnconnectedOutLayers().flatten()]
            
            with open("coco.names", "r") as f:
                self.classes = [line.strip() for line in f.readlines()]
                
            logging.info("YOLO model initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize YOLO model: {str(e)}")
            raise
    
    def start_detection(self):
        self.is_running = True
        self.detection_thread = threading.Thread(target=self._detection_loop)
        self.detection_thread.start()
    
    def stop_detection(self):
        self.is_running = False
        if self.detection_thread:
            self.detection_thread.join()
    
    def _detection_loop(self):
        while self.is_running:
            try:
                frame = self.frame_queue.get(timeout=1)
                self.process_frame(frame)
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"Error in detection loop: {str(e)}")
    
    def add_frame(self, frame):
        try:
            if self.frame_queue.full():
                self.frame_queue.get_nowait()  # Remove oldest frame
            self.frame_queue.put_nowait(frame)
        except queue.Full:
            pass
    
    def process_frame(self, frame):
        # Resize frame to smaller dimensions for faster processing
        frame = cv2.resize(frame, (416, 416))
        
        # Convert to float16 for reduced memory usage
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False).astype(np.float16)
        
        # Use asyncio for non-blocking detection
        async def detect_objects():
            self.net.setInput(blob)
            return self.net.forward(self.output_layers)
        
        height, width = frame.shape[:2]
        outs = self.net.forward(self.output_layers)
        
        class_ids = []
        confidences = []
        boxes = []
        
        # Détection des objets
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                
                if confidence > self.confidence_threshold:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)
        
        indexes = cv2.dnn.NMSBoxes(boxes, confidences, self.confidence_threshold, 0.4)
        now = datetime.now()
        
        for i in range(len(boxes)):
            if i in indexes:
                x, y, w, h = boxes[i]
                label = self.classes[class_ids[i]]
                confidence = confidences[i]
                
                if label in self.dangerous_objects:
                    # Vérifier si assez de temps s'est écoulé depuis la dernière détection
                    last_detection = self.last_detections.get(label)
                    if (last_detection is None or 
                        (now - last_detection).total_seconds() > self.alert_timeout):
                        
                        # Mettre à jour le timestamp de dernière détection
                        self.last_detections[label] = now
                        
                        # Dessiner le rectangle de détection
                        color = (0, 0, 255)  # Rouge pour les objets dangereux
                        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                        cv2.putText(frame, f"{label} ({confidence:.2f})", 
                                  (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 
                                  0.6, color, 2)
                        
                        # Sauvegarder l'alerte
                        alert_id = self.analytics_manager.add_alert(
                            label, confidence,
                            location=f"x:{x},y:{y},w:{w},h:{h}"
                        )
                        
                        # Envoyer la notification avec l'image
                        self.notification_manager.send_alert(
                            label, confidence, frame.copy()
                        )
                        
                        logging.info(f"Dangerous object detected: {label} "
                                   f"(confidence: {confidence:.2f})")
        
        return frame

def main():
    try:
        # Initialiser le détecteur
        detector = ObjectDetector()
        detector.start_detection()
        
        # Initialiser la caméra
        cap = cv2.VideoCapture(0)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                logging.error("Failed to grab frame")
                break
            
            # Ajouter le frame à la queue de détection
            detector.add_frame(frame.copy())
            
            # Afficher le frame
            cv2.imshow("Danger Detection System", frame)
            
            # Sortir avec 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # Nettoyage
        detector.stop_detection()
        cap.release()
        cv2.destroyAllWindows()
        
    except Exception as e:
        logging.error(f"Main loop error: {str(e)}")
        raise

if __name__ == "__main__":
    main()

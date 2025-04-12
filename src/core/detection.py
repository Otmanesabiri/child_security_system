import cv2
import numpy as np
import json
from pathlib import Path
import sys
import logging
from datetime import datetime
import threading
import queue
import os

# Fix imports by using relative imports instead of absolute
from .notification_manager import NotificationManager
from .analytics_manager import AnalyticsManager

class ObjectDetector:
    def __init__(self, config_path='config.json', camera_source=0,
                 yolo_weights="yolov3.weights", 
                 yolo_cfg="yolov3.cfg", 
                 coco_names="coco.names"):
        self.camera_source = camera_source
        self.yolo_weights = yolo_weights
        self.yolo_cfg = yolo_cfg
        self.coco_names = coco_names
        self.load_config(config_path)
        self.setup_logging()
        self.init_yolo()
        self.notification_manager = NotificationManager()
        self.analytics_manager = AnalyticsManager()
        self.frame_queue = queue.Queue(maxsize=30)
        self.detection_thread = None
        self.is_running = False
        self.last_detections = {}  # Pour éviter les alertes répétées
        self.camera = None
        
    def load_config(self, config_path):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
            self.dangerous_objects = set(self.config['detection']['dangerous_objects'])
            self.confidence_threshold = self.config['detection']['confidence_threshold']
            self.alert_timeout = self.config['detection']['alert_timeout']
    
    def setup_logging(self):
        # Use existing logger
        self.logger = logging.getLogger(__name__)
    
    def init_yolo(self):
        try:
            # Check if model files exist
            for file_path in [self.yolo_weights, self.yolo_cfg, self.coco_names]:
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"YOLO model file not found: {file_path}")
            
            self.net = cv2.dnn.readNet(self.yolo_weights, self.yolo_cfg)
            self.layer_names = self.net.getLayerNames()
            
            # Handle output layers correctly for different OpenCV versions
            try:
                # Newer OpenCV versions
                output_layers = self.net.getUnconnectedOutLayers().flatten()
            except:
                # Older OpenCV versions
                output_layers = self.net.getUnconnectedOutLayers()
                
            self.output_layers = [self.layer_names[i - 1] for i in output_layers]
            
            with open(self.coco_names, "r") as f:
                self.classes = [line.strip() for line in f.readlines()]
                
            self.logger.info("YOLO model initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize YOLO model: {str(e)}")
            raise
    
    def start_detection(self):
        """Start the detection thread and open the camera"""
        self.is_running = True
        # Try to open the camera before starting the detection thread
        if not self.open_camera():
            self.is_running = False
            return False
            
        self.detection_thread = threading.Thread(target=self._detection_loop)
        self.detection_thread.start()
        return True
    
    def open_camera(self):
        """
        Open the camera with the specified source
        
        Returns:
            bool: True if camera opened successfully, False otherwise
        """
        # Close any existing camera first
        if self.camera is not None:
            self.camera.release()
            
        try:
            # Try string path if camera_source is a string (file or URL)
            if isinstance(self.camera_source, str):
                if os.path.exists(self.camera_source):
                    self.logger.info(f"Opening camera from file: {self.camera_source}")
                else:
                    self.logger.info(f"Opening camera from URL/string source: {self.camera_source}")
            else:
                self.logger.info(f"Opening camera with index: {self.camera_source}")
                
            self.camera = cv2.VideoCapture(self.camera_source)
            
            if not self.camera.isOpened():
                self.logger.error(f"Failed to open camera source: {self.camera_source}")
                return False
                
            # Get camera information
            width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.camera.get(cv2.CAP_PROP_FPS)
            
            self.logger.info(f"Camera opened successfully: {width}x{height} at {fps} FPS")
            return True
            
        except Exception as e:
            self.logger.error(f"Error opening camera: {str(e)}")
            return False
    
    def set_camera_source(self, source):
        """
        Change the camera source
        
        Args:
            source: Camera index (int) or file/URL path (str)
        """
        self.camera_source = source
        was_running = self.is_running
        
        # Stop current detection if running
        if was_running:
            self.stop_detection()
            
        # Reopen with new source
        success = self.open_camera()
        
        # Restart detection if it was running before
        if was_running and success:
            self.start_detection()
            
        return success
            
    def stop_detection(self):
        """Stop detection thread and release camera"""
        self.is_running = False
        if self.detection_thread:
            self.detection_thread.join()
            
        # Release the camera
        if self.camera is not None and self.camera.isOpened():
            self.camera.release()
            self.camera = None
    
    def _detection_loop(self):
        while self.is_running:
            try:
                frame = self.frame_queue.get(timeout=1)
                self.process_frame(frame)
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in detection loop: {str(e)}")
    
    def add_frame(self, frame):
        try:
            if self.frame_queue.full():
                self.frame_queue.get_nowait()  # Remove oldest frame
            self.frame_queue.put_nowait(frame)
        except queue.Full:
            pass
            
    def get_frame(self):
        """
        Get a frame from the camera
        
        Returns:
            tuple: (success, frame) - success is True if frame was read successfully
        """
        if self.camera is None or not self.camera.isOpened():
            if not self.open_camera():
                return False, None
                
        success, frame = self.camera.read()
        return success, frame
    
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
        # Create models directory if it doesn't exist
        models_dir = "models"
        os.makedirs(models_dir, exist_ok=True)
        
        # Check for model files
        model_files = {
            os.path.join(models_dir, "yolov3.weights"): "https://pjreddie.com/media/files/yolov3.weights",
            os.path.join(models_dir, "yolov3.cfg"): "https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3.cfg",
            os.path.join(models_dir, "coco.names"): "https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names"
        }
        
        for file_path, url in model_files.items():
            if not os.path.exists(file_path):
                print(f"Required model file missing: {file_path}")
                print(f"Please download from: {url}")
                return
        
        # Initialize detector with model files in the models directory
        detector = ObjectDetector(
            yolo_weights=os.path.join(models_dir, "yolov3.weights"),
            yolo_cfg=os.path.join(models_dir, "yolov3.cfg"),
            coco_names=os.path.join(models_dir, "coco.names"),
            camera_source=0
        )
        
        # Try to start detection and gracefully handle failure
        if not detector.start_detection():
            # If camera 0 fails, try some alternatives
            alternative_sources = [1, 2, '/dev/video0', '/dev/video1']
            success = False
            
            for alt_source in alternative_sources:
                logging.info(f"Trying alternative camera source: {alt_source}")
                if detector.set_camera_source(alt_source):
                    success = True
                    break
                    
            if not success:
                logging.error("Could not open any camera source")
                print("Error: Could not open camera. Make sure a camera is connected and not in use by another application.")
                return
        
        # Main loop - use detector.get_frame() instead of direct camera access
        while True:
            ret, frame = detector.get_frame()
            if not ret:
                logging.error("Failed to grab frame")
                print("Error grabbing frame, trying to reconnect...")
                # Try to reopen the camera
                if not detector.open_camera():
                    print("Failed to reconnect to camera. Exiting.")
                    break
                continue
            
            # Ajouter le frame à la queue de détection
            detector.add_frame(frame.copy())
            
            # Afficher le frame
            cv2.imshow("Danger Detection System", frame)
            
            # Sortir avec 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # Nettoyage
        detector.stop_detection()
        cv2.destroyAllWindows()
        
    except Exception as e:
        logging.error(f"Main loop error: {str(e)}")
        print(f"An error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main()

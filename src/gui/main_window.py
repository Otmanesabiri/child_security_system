import sys
import cv2
import numpy as np
import sqlite3
import requests
import csv
import json
import logging
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from pathlib import Path

# Corriger l'import en utilisant le chemin complet
from src.core.camera_manager import CameraManager
from src.gui.camera_dialog import CameraDialog  # Add this import statement

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

TELEGRAM_BOT_TOKEN = "Your_Bot_Token"
TELEGRAM_CHAT_ID = "Your_Chat_ID"

class VideoRecorder(QThread):
    """Thread for video recording"""
    finished = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_recording = False
        self.output_path = None

    def start_recording(self, output_path):
        self.output_path = output_path
        self.is_recording = True
        self.start()

    def stop_recording(self):
        self.is_recording = False

    def run(self):
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(self.output_path, fourcc, 20.0, (640,480))
        cap = cv2.VideoCapture(0)
        
        while self.is_recording:
            ret, frame = cap.read()
            if ret:
                out.write(frame)
        
        cap.release()
        out.release()
        self.finished.emit(self.output_path)

class AlertRecorder:
    """Class for recording alerts"""
    def __init__(self):
        self.is_recording = False
        self.recorded_alerts = []

    def start_recording(self):
        self.is_recording = True
        self.recorded_alerts = []

    def stop_recording(self):
        self.is_recording = False
        return self.recorded_alerts

    def add_alert(self, alert_data):
        if self.is_recording:
            self.recorded_alerts.append(alert_data)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Paramètres")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Telegram settings
        telegram_group = QGroupBox("Paramètres Telegram")
        telegram_layout = QFormLayout()
        self.bot_token = QLineEdit()
        self.chat_id = QLineEdit()
        telegram_layout.addRow("Bot Token:", self.bot_token)
        telegram_layout.addRow("Chat ID:", self.chat_id)
        telegram_group.setLayout(telegram_layout)
        
        # Detection settings
        detection_group = QGroupBox("Paramètres de détection")
        detection_layout = QFormLayout()
        self.confidence_threshold = QSpinBox()
        self.confidence_threshold.setRange(1, 100)
        self.confidence_threshold.setValue(50)
        detection_layout.addRow("Seuil de confiance (%):", self.confidence_threshold)
        detection_group.setLayout(detection_layout)
        
        # Add to main layout
        layout.addWidget(telegram_group)
        layout.addWidget(detection_group)
        
        # Buttons
        buttons = QHBoxLayout()
        save_btn = QPushButton("Enregistrer")
        cancel_btn = QPushButton("Annuler")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setLayout(layout)

class DangerDetectionApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Initialize logger
        self.logger = logging.getLogger('DangerDetectionApp')
        
        # Élargir la liste des objets dangereux et leurs synonymes
        self.dangerous_objects = {
            "camera", "cell phone", "mobile", "phone",
            "knife", "blade", "scissors", "cutter",
            "bottle", "gun", "weapon", "pistol"
        }
        self.detection_active = False
        self.recording = False
        self.load_settings()
        self.initUI()
        # Lazy loading of YOLO
        self.net = None
        self.classes = None
        self.output_layers = None
        
        self.init_camera()
        self.init_db()
        self.video_recorder = None  # Initialize only when needed
        self.alert_recorder = AlertRecorder()  # Initialize alert recorder
        self.camera_manager = CameraManager()
        self.models_dir = Path(__file__).parent.parent.parent / 'data' / 'models'
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def load_settings(self):
        try:
            with open('settings.json', 'r') as f:
                self.settings = json.load(f)
        except:
            self.settings = {
                'confidence_threshold': 0.5,
                'telegram_bot_token': '',
                'telegram_chat_id': ''
            }

    def save_settings(self):
        with open('settings.json', 'w') as f:
            json.dump(self.settings, f)

    def initUI(self):
        self.setWindowTitle("Advanced Danger Detection System")
        self.setGeometry(100, 100, 1000, 700)
        
        # Load external style sheet
        try:
            with open("style.qss", "r") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Error loading style sheet: {str(e)}")

        # Central tab widget
        self.tab_widget = QTabWidget()
        
        # Detection tab
        self.detection_tab = QWidget()
        self.setup_detection_tab()
        
        # Alerts tab
        self.alerts_tab = QWidget()
        self.setup_alerts_tab()
        
        self.tab_widget.addTab(self.detection_tab, "Live Detection")
        self.tab_widget.addTab(self.alerts_tab, "Alert History")

        self.setCentralWidget(self.tab_widget)

        # Add new menu items
        self.create_menu_bar()
        
        # Add status bar widgets
        self.create_status_bar()
        
        # Add recording controls
        self.add_recording_controls()
        
        # Add statistics panel
        self.add_statistics_panel()

        # Status bar
        self.statusBar().showMessage('System Ready')

    def setup_detection_tab(self):
        """Setup the main detection tab"""
        layout = QVBoxLayout()
        
        # Video and controls layout
        video_layout = QHBoxLayout()
        
        # Create a frame for video feed with border
        video_frame = QFrame()
        video_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        video_frame.setLineWidth(2)
        video_frame.setStyleSheet("""
            QFrame {
                border: 3px solid #2a82da;
                border-radius: 5px;
                background-color: #232323;
            }
        """)
        
        # Video feed
        self.video_label = QLabel()
        self.video_label.setFixedSize(640, 480)
        
        # Add video label to frame
        video_frame_layout = QVBoxLayout()
        video_frame_layout.addWidget(self.video_label)
        video_frame_layout.setContentsMargins(5, 5, 5, 5)
        video_frame.setLayout(video_frame_layout)
        
        video_layout.addWidget(video_frame)
        
        # Control panel
        control_layout = QVBoxLayout()
        
        # Confidence threshold slider
        self.confidence_slider = QSlider(Qt.Vertical)
        self.confidence_slider.setRange(10, 90)
        self.confidence_slider.setValue(50)
        self.confidence_slider.valueChanged.connect(self.update_confidence_threshold)
        control_layout.addWidget(QLabel("Confidence Threshold"))
        control_layout.addWidget(self.confidence_slider)
        
        # Dangerous objects input
        self.danger_input = QLineEdit(self)
        self.danger_input.setPlaceholderText("Enter dangerous objects (comma-separated)")
        control_layout.addWidget(self.danger_input)
        
        # Update objects button
        self.update_button = QPushButton("Update Danger Objects")
        self.update_button.clicked.connect(self.update_danger_objects)
        control_layout.addWidget(self.update_button)
        
        # Alert box
        self.alert_box = QTextEdit(self)
        self.alert_box.setReadOnly(True)
        control_layout.addWidget(self.alert_box)
        
        # Record alerts button
        self.record_button = QPushButton("Start Recording Alerts")
        self.record_button.clicked.connect(self.toggle_alert_recording)
        control_layout.addWidget(self.record_button)
        
        video_layout.addLayout(control_layout)
        
        layout.addLayout(video_layout)
        self.detection_tab.setLayout(layout)

    def setup_alerts_tab(self):
        """Create alerts history tab"""
        layout = QVBoxLayout()
        
        # Alerts table
        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(3)
        self.alerts_table.setHorizontalHeaderLabels(["Object", "Timestamp", "Location"])
        layout.addWidget(self.alerts_table)
        
        # Export button
        export_button = QPushButton("Export Alerts")
        export_button.clicked.connect(self.export_alerts)
        layout.addWidget(export_button)
        
        self.alerts_tab.setLayout(layout)

    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('Fichier')
        
        export_action = QAction('Exporter les alertes', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.export_alerts)
        
        settings_action = QAction('Paramètres', self)
        settings_action.setShortcut('Ctrl+P')
        settings_action.triggered.connect(self.show_settings)
        
        file_menu.addAction(export_action)
        file_menu.addAction(settings_action)
        file_menu.addSeparator()
        
        exit_action = QAction('Quitter', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu('Affichage')
        
        toggle_detection = QAction('Activer/Désactiver la détection', self)
        toggle_detection.setShortcut('Ctrl+D')
        toggle_detection.triggered.connect(self.toggle_detection)
        view_menu.addAction(toggle_detection)
        
        # Ajouter menu Caméra
        camera_menu = menubar.addMenu('Caméra')
        
        config_camera_action = QAction('Configurer Caméra', self)
        config_camera_action.triggered.connect(self.show_camera_config)
        camera_menu.addAction(config_camera_action)

    def show_camera_config(self):
        dialog = CameraDialog(self.camera_manager, self)
        dialog.exec_()

    def create_status_bar(self):
        self.status_label = QLabel()
        self.statusBar().addPermanentWidget(self.status_label)
        self.update_status("Système prêt")

    def update_status(self, message):
        self.status_label.setText(message)

    def add_recording_controls(self):
        control_layout = self.detection_tab.layout().itemAt(0).layout().itemAt(1).layout()
        
        record_group = QGroupBox("Enregistrement")
        record_layout = QVBoxLayout()
        
        self.record_video_btn = QPushButton("Démarrer l'enregistrement")
        self.record_video_btn.clicked.connect(self.toggle_recording)
        
        record_layout.addWidget(self.record_video_btn)
        record_group.setLayout(record_layout)
        control_layout.addWidget(record_group)

    def add_statistics_panel(self):
        stats_group = QGroupBox("Statistiques")
        stats_layout = QVBoxLayout()
        
        self.total_alerts_label = QLabel("Alertes totales: 0")
        self.today_alerts_label = QLabel("Alertes aujourd'hui: 0")
        
        stats_layout.addWidget(self.total_alerts_label)
        stats_layout.addWidget(self.today_alerts_label)
        stats_group.setLayout(stats_layout)
        
        self.detection_tab.layout().itemAt(0).layout().itemAt(1).layout().addWidget(stats_group)

    def toggle_recording(self):
        if not hasattr(self, 'video_recorder') or self.video_recorder is None:
            self.video_recorder = VideoRecorder()
        if not self.recording:
            filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.avi"
            path = str(Path.cwd() / "recordings" / filename)
            Path("recordings").mkdir(exist_ok=True)
            
            self.video_recorder.start_recording(path)
            self.record_video_btn.setText("Arrêter l'enregistrement")
            self.recording = True
        else:
            self.video_recorder.stop_recording()
            self.record_video_btn.setText("Démarrer l'enregistrement")
            self.recording = False

    def show_settings(self):
        dialog = SettingsDialog(self)
        dialog.bot_token.setText(self.settings['telegram_bot_token'])
        dialog.chat_id.setText(self.settings['telegram_chat_id'])
        dialog.confidence_threshold.setValue(int(self.settings['confidence_threshold'] * 100))
        
        if dialog.exec_():
            self.settings['telegram_bot_token'] = dialog.bot_token.text()
            self.settings['telegram_chat_id'] = dialog.chat_id.text()
            self.settings['confidence_threshold'] = dialog.confidence_threshold.value() / 100
            self.save_settings()

    def toggle_detection(self):
        if not self.detection_active:
            # Load YOLO only when detection is activated
            self.load_yolo()
        self.detection_active = not self.detection_active
        status = "activée" if self.detection_active else "désactivée"
        self.update_status(f"Détection {status}")

    def update_statistics(self):
        # Update total alerts
        self.cursor.execute('SELECT COUNT(*) FROM alerts')
        total = self.cursor.fetchone()[0]
        self.total_alerts_label.setText(f"Alertes totales: {total}")
        
        # Update today's alerts
        today = datetime.now().strftime('%Y-%m-%d')
        self.cursor.execute('SELECT COUNT(*) FROM alerts WHERE date(timestamp) = ?', (today,))
        today_count = self.cursor.fetchone()[0]
        self.today_alerts_label.setText(f"Alertes aujourd'hui: {today_count}")

    def init_camera(self):
        """Initialize camera with error handling"""
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise IOError("Cannot open webcam")
            
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_frame)
            self.timer.start(30)
        except Exception as e:
            self.alert_box.append(f"Camera Error: {str(e)}")

    def update_confidence_threshold(self, value):
        """Update detection confidence threshold"""
        self.confidence_threshold = value / 100.0
        self.statusBar().showMessage(f"Confidence Threshold: {value}%")

    def toggle_alert_recording(self):
        """Toggle alert recording"""
        if not hasattr(self, 'alert_recorder') or self.alert_recorder is None:
            self.alert_recorder = AlertRecorder()
            
        if not self.alert_recorder.is_recording:
            self.alert_recorder.start_recording()
            self.record_button.setText("Stop Recording")
        else:
            self.alert_recorder.stop_recording()
            self.record_button.setText("Start Recording Alerts")

    def export_alerts(self):
        """Export alerts to CSV"""
        filename, _ = QFileDialog.getSaveFileName(self, "Export Alerts", "", "CSV Files (*.csv)")
        if filename:
            try:
                with open(filename, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(["Object", "Timestamp", "Location"])
                    # Add logic to write alerts from database
            except Exception as e:
                self.alert_box.append(f"Export Error: {str(e)}")

    def update_danger_objects(self):
        """Mise à jour des objets dangereux"""
        user_input = self.danger_input.text().strip().lower()  # Convertir en minuscules
        if user_input:
            new_objects = {obj.strip() for obj in user_input.split(",")}
            self.dangerous_objects.update(new_objects)  # Ajouter aux objets existants
            self.alert_box.append(f"✅ Liste des objets dangereux mise à jour : {', '.join(self.dangerous_objects)}\n")

    def update_frame(self):
        if not self.detection_active:
            return

        frame = self.camera_manager.get_frame()
        if frame is None:
            return

        # Process object detection if active
        if self.detection_active:
            frame = self.process_frame(frame)

        # Convert frame to Qt format and display
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, _ = frame.shape
        qt_img = QImage(frame.data, width, height, width * 3, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_img))

    def process_frame(self, frame):
        if frame is None:
            return None

        try:
            height, width = frame.shape[:2]
            
            # Draw detection status on frame
            cv2.putText(frame, f"Detection: {'ON' if self.detection_active else 'OFF'}", 
                      (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Check if YOLO is loaded
            if self.net is None:
                cv2.putText(frame, "YOLO not loaded - Press Ctrl+D to start", 
                          (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                return frame
                
            # Pre-process frame for YOLO
            blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
            self.net.setInput(blob)
            
            # Get detections
            outs = self.net.forward(self.output_layers)
            self.logger.debug(f"Number of output layers: {len(outs)}")
            
            # Process detections
            class_ids = []
            confidences = []
            boxes = []
            
            for i, out in enumerate(outs):
                self.logger.debug(f"Processing output layer {i} with shape {out.shape}")
                for detection in out:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]
                    
                    if confidence > 0.2:  # Lower threshold
                        # Convert relative coordinates to absolute
                        center_x = int(detection[0] * width)
                        center_y = int(detection[1] * height)
                        w = int(detection[2] * width)
                        h = int(detection[3] * height)
                        x = int(center_x - w/2)
                        y = int(center_y - h/2)
                        
                        class_ids.append(class_id)
                        confidences.append(float(confidence))
                        boxes.append([x, y, w, h])
            
            # Apply non-maximum suppression
            indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.2, 0.3)
            
            # Draw detected objects
            detected_danger = False
            detected_objects = []
            
            # Ensure indexes is iterable and not None
            if indexes is not None and len(indexes) > 0:
                if isinstance(indexes, tuple):
                    indexes = indexes[0]
                
                for i in indexes:
                    try:
                        x, y, w, h = boxes[i]
                        label = str(self.classes[class_ids[i]]).lower()
                        confidence = confidences[i]
                        
                        detected_objects.append(f"{label} ({confidence:.2f})")
                        
                        # Check if object is dangerous
                        is_dangerous = any(obj in label for obj in self.dangerous_objects)
                        
                        if is_dangerous:
                            detected_danger = True
                            color = (0, 0, 255)  # Red for dangerous
                            self.alert_box.append(f"⚠️ ALERT: {label} detected! (Confidence: {confidence:.2f})")
                            self.send_telegram_alert(label)
                        else:
                            color = (0, 255, 0)  # Green for safe
                        
                        # Draw rectangle and label
                        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                        cv2.putText(frame, f"{label} ({confidence:.2f})", 
                                  (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    except IndexError as e:
                        self.logger.error(f"IndexError in process_frame: {str(e)}")
                        continue
            
            # Display total objects detected
            cv2.putText(frame, f"Objects: {len(indexes) if indexes is not None else 0}", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Log detections
            if detected_objects:
                self.logger.info(f"Detected: {', '.join(detected_objects)}")
                
            if detected_danger:
                # Draw danger warning
                cv2.putText(frame, "DANGER DETECTED!", 
                          (width // 2 - 100, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                
            return frame
            
        except Exception as e:
            self.logger.error(f"Error processing frame: {str(e)}")
            # Return original frame with error message
            cv2.putText(frame, f"Detection Error: {str(e)}", 
                      (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            return frame

    def save_alert_to_db(self, label):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute('INSERT INTO alerts (object, timestamp) VALUES (?, ?)', (label, timestamp))
        self.conn.commit()
        self.update_statistics()

    def send_telegram_alert(self, label):
        """ Send alert to Telegram """
        message = f"⚠️ ALERT: {label} detected!"
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

    def load_yolo(self):
        """Lazy loading of YOLO model with correct paths"""
        if self.net is None:
            try:
                self.logger.info("Loading YOLO model...")
                weights_path = self.models_dir / 'yolov3.weights'
                cfg_path = self.models_dir / 'yolov3.cfg'
                names_path = self.models_dir / 'coco.names'
                
                # Check if model files exist
                if not weights_path.exists():
                    self.alert_box.append(f"Error: yolov3.weights not found at {weights_path}")
                    self.logger.error(f"yolov3.weights not found at {weights_path}")
                    return False
                    
                if not cfg_path.exists():
                    self.alert_box.append(f"Error: yolov3.cfg not found at {cfg_path}")
                    self.logger.error(f"yolov3.cfg not found at {cfg_path}")
                    return False
                
                if not names_path.exists():
                    self.alert_box.append(f"Error: coco.names not found at {names_path}")
                    self.logger.error(f"coco.names not found at {names_path}")
                    return False
                
                # Load the model
                self.net = cv2.dnn.readNet(str(weights_path), str(cfg_path))
                layer_names = self.net.getLayerNames()
                self.logger.info(f"YOLO model read successfully from {weights_path} and {cfg_path}")
                try:
                    # Handle different OpenCV versions
                    self.output_layers = [layer_names[i[0] - 1] for i in self.net.getUnconnectedOutLayers()]
                except:
                    self.output_layers = [layer_names[i - 1] for i in self.net.getUnconnectedOutLayers().flatten()]
                
                with open(names_path, "r") as f:
                    self.classes = [line.strip() for line in f.readlines()]
                
                self.logger.info("YOLO model loaded successfully")
                self.alert_box.append("✅ YOLO model loaded successfully")
                return True
            except Exception as e:
                self.alert_box.append(f"Error loading YOLO model: {str(e)}")
                self.logger.error(f"Failed to load YOLO model: {str(e)}")
                return False
        return True

    def init_db(self):
        """ Initialize the SQLite database """
        self.conn = sqlite3.connect('danger_detection.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY,
                object TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def closeEvent(self, event):
        self.timer.stop()
        self.camera_manager.stop()
        if self.camera_manager.camera is not None:
            self.camera_manager.camera.release()
        self.conn.close()
        cv2.destroyAllWindows()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Load external style sheet for the entire application
    try:
        with open("style.qss", "r") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        print(f"Error loading style sheet: {str(e)}")
    
    window = DangerDetectionApp()
    window.show()
    sys.exit(app.exec_())
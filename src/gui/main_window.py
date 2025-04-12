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
import os

# Corriger l'import en utilisant le chemin complet
from src.core.camera_manager import CameraManager
from src.gui.camera_dialog import CameraDialog

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

# Add the missing AlertRecorder class
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

class VideoRecorder(QThread):
    """Thread for video recording"""
    finished = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger('VideoRecorder')
        self.is_recording = False
        self.output_path = None
        self.cap = None
        self.out = None
        self.camera_index = 0

    def start_recording(self, output_path, camera_index=0):
        self.output_path = output_path
        self.is_recording = True
        self.camera_index = camera_index
        self.start()

    def stop_recording(self):
        self.is_recording = False

    def run(self):
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                self.logger.error(f"Failed to open camera {self.camera_index} for recording")
                return
                
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 20.0 # Default FPS if camera doesn't provide it
                
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.out = cv2.VideoWriter(self.output_path, fourcc, fps, (width, height))
            
            while self.is_recording:
                ret, frame = self.cap.read()
                if ret:
                    self.out.write(frame)
                else:
                    # Break if camera fails
                    break
                    
        except Exception as e:
            self.logger.error(f"Error during recording: {str(e)}")
        finally:
            if self.cap:
                self.cap.release()
            if self.out:
                self.out.release()
            self.finished.emit(self.output_path)

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
    def __init__(self, config_path='config/config.json', model_dir='models', has_cameras=True):
        """
        Initialize the main application window
        
        Args:
            config_path (str): Path to the configuration file
            model_dir (str): Path to the directory containing model files
            has_cameras (bool): Whether cameras are available
        """
        super().__init__()
        # Initialize logger
        self.logger = logging.getLogger('DangerDetectionApp')
        self.logger.info(f"Initializing app with config: {config_path}, models: {model_dir}")
        
        # Store parameters
        self.config_path = config_path
        self.model_dir = Path(model_dir)
        self.has_cameras = has_cameras
        
        # Load settings from config file
        self.load_config()
        
        # Initialize UI
        self.initUI()
        
        # Lazy loading of YOLO
        self.net = None
        self.classes = None
        self.output_layers = None
        
        # Initialize database
        self.init_db()
        
        # Initialize camera if available
        if self.has_cameras:
            self.camera_manager = CameraManager()
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_frame)
            self.timer.start(30)
        else:
            self.logger.warning("No cameras available")
            self.statusBar().showMessage("No cameras detected")
            
        self.video_recorder = None  # Initialize only when needed
        self.alert_recorder = AlertRecorder()  # Initialize alert recorder

    def load_config(self):
        """Load configuration from config file"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
                
            # Initialize dangerous objects from config
            self.dangerous_objects = set(self.config['detection']['dangerous_objects'])
            self.confidence_threshold = self.config['detection']['confidence_threshold']
            self.alert_timeout = self.config['detection']['alert_timeout']
            
            self.logger.info(f"Loaded config from {self.config_path}")
            self.logger.info(f"Dangerous objects: {self.dangerous_objects}")
        except Exception as e:
            self.logger.error(f"Error loading config: {str(e)}")
            # Set default values
            self.dangerous_objects = {
                "knife", "scissors", "gun", "bottle", "cell phone"
            }
            self.confidence_threshold = 0.5
            self.alert_timeout = 60
            
        # Set detection state
        self.detection_active = False
        self.recording = False

    def initUI(self):
        self.setWindowTitle("Advanced Danger Detection System")
        self.setGeometry(100, 100, 1000, 700)
        
        # Load external style sheet
        try:
            style_path = os.path.join(os.path.dirname(self.config_path), "style.qss")
            if os.path.exists(style_path):
                with open(style_path, "r") as f:
                    self.setStyleSheet(f.read())
            else:
                self.logger.warning(f"Style sheet not found at {style_path}")
        except Exception as e:
            self.logger.error(f"Error loading style sheet: {str(e)}")

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
        self.control_layout = QVBoxLayout()
        
        # Confidence threshold slider
        self.confidence_slider = QSlider(Qt.Vertical)
        self.confidence_slider.setRange(10, 90)
        self.confidence_slider.setValue(50)
        self.confidence_slider.valueChanged.connect(self.update_confidence_threshold)
        self.control_layout.addWidget(QLabel("Confidence Threshold"))
        self.control_layout.addWidget(self.confidence_slider)
        
        # Dangerous objects input
        self.danger_input = QLineEdit(self)
        self.danger_input.setPlaceholderText("Enter dangerous objects (comma-separated)")
        self.control_layout.addWidget(self.danger_input)
        
        # Update objects button
        self.update_button = QPushButton("Update Danger Objects")
        self.update_button.clicked.connect(self.update_danger_objects)
        self.control_layout.addWidget(self.update_button)
        
        # Alert box
        self.alert_box = QTextEdit(self)
        self.alert_box.setReadOnly(True)
        self.control_layout.addWidget(self.alert_box)
        
        # Record alerts button
        self.record_button = QPushButton("Start Recording Alerts")
        self.record_button.clicked.connect(self.toggle_alert_recording)
        self.control_layout.addWidget(self.record_button)
        
        # Add recording controls
        self.add_recording_controls()
        
        # Add statistics panel
        self.add_statistics_panel()
        
        video_layout.addLayout(self.control_layout)
        
        layout.addLayout(video_layout)
        self.detection_tab.setLayout(layout)

    def setup_alerts_tab(self):
        """Create alerts history tab"""
        layout = QVBoxLayout()
        
        # Alerts table
        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(4)
        self.alerts_table.setHorizontalHeaderLabels(["Object", "Timestamp", "Confidence", "Location"])
        # Make table non-editable and select full rows
        self.alerts_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.alerts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.alerts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.alerts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.alerts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self.alerts_table)
        
        # Export button
        export_button = QPushButton("Export Alerts")
        export_button.clicked.connect(self.export_alerts)
        layout.addWidget(export_button)
        
        self.alerts_tab.setLayout(layout)
        # Load initial alerts
        self.load_alerts_from_db()

    def load_alerts_from_db(self):
        """Load alerts from the database into the table"""
        try:
            self.cursor.execute('SELECT object, timestamp, confidence, location FROM alerts ORDER BY timestamp DESC')
            alerts = self.cursor.fetchall()
            
            self.alerts_table.setRowCount(len(alerts))
            
            for row, alert in enumerate(alerts):
                obj, timestamp, confidence, location = alert
                self.alerts_table.setItem(row, 0, QTableWidgetItem(obj))
                self.alerts_table.setItem(row, 1, QTableWidgetItem(timestamp))
                confidence_item = QTableWidgetItem(f"{confidence:.2f}" if confidence else "N/A")
                self.alerts_table.setItem(row, 2, confidence_item)
                self.alerts_table.setItem(row, 3, QTableWidgetItem(location if location else "N/A")) 
                
        except Exception as e:
            self.logger.error(f"Error loading alerts from DB: {str(e)}")

    def export_alerts(self):
        """Export alerts from the database to a CSV file"""
        filename, _ = QFileDialog.getSaveFileName(self, "Export Alerts", "", "CSV Files (*.csv)")
        if filename:
            try:
                self.cursor.execute('SELECT object, timestamp, confidence, location FROM alerts ORDER BY timestamp DESC')
                alerts = self.cursor.fetchall()
                
                with open(filename, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(["Object", "Timestamp", "Confidence", "Location"]) # Add headers
                    writer.writerows(alerts)
                    
                self.statusBar().showMessage(f"Alerts exported to {filename}", 5000)
                self.logger.info(f"Alerts exported to {filename}")
            except Exception as e:
                self.logger.error(f"Export Error: {str(e)}")
                QMessageBox.warning(self, "Export Error", f"Failed to export alerts: {str(e)}")

    def show_settings(self):
        """Show the settings dialog"""
        dialog = SettingsDialog(self)
        
        # Initialize settings dictionary if it doesn't exist
        if not hasattr(self, 'settings'):
            self.settings = {
                'telegram_bot_token': self.config.get('notification', {}).get('telegram_bot_token', TELEGRAM_BOT_TOKEN),
                'telegram_chat_id': self.config.get('notification', {}).get('telegram_chat_id', TELEGRAM_CHAT_ID),
                'confidence_threshold': self.confidence_threshold
            }
            
        # Load current settings into the dialog
        dialog.bot_token.setText(self.settings.get('telegram_bot_token', ''))
        dialog.chat_id.setText(self.settings.get('telegram_chat_id', ''))
        dialog.confidence_threshold.setValue(int(self.settings.get('confidence_threshold', 0.5) * 100))
        
        if dialog.exec_():
            # Save settings if dialog accepted
            self.settings['telegram_bot_token'] = dialog.bot_token.text()
            self.settings['telegram_chat_id'] = dialog.chat_id.text()
            new_threshold = dialog.confidence_threshold.value() / 100.0
            
            # Update confidence threshold if changed
            if self.confidence_threshold != new_threshold:
                self.confidence_threshold = new_threshold
                self.confidence_slider.setValue(int(new_threshold * 100)) # Update slider
                self.logger.info(f"Confidence threshold updated via settings: {self.confidence_threshold:.2f}")
                
            self.settings['confidence_threshold'] = self.confidence_threshold
            
            # Save these settings back to config.json
            self.save_settings_to_config()
            self.logger.info("Settings updated")
            self.statusBar().showMessage("Settings updated", 3000)

    def save_settings_to_config(self):
        """Save current settings back to the config file"""
        try:
            if 'notification' not in self.config:
                self.config['notification'] = {}
            self.config['notification']['telegram_bot_token'] = self.settings.get('telegram_bot_token')
            self.config['notification']['telegram_chat_id'] = self.settings.get('telegram_chat_id')
            if 'detection' not in self.config:
                self.config['detection'] = {}
            self.config['detection']['confidence_threshold'] = self.settings.get('confidence_threshold')

            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.logger.info(f"Settings saved to {self.config_path}")
        except Exception as e:
            self.logger.error(f"Failed to save settings to config file: {str(e)}")
            QMessageBox.warning(self, "Save Error", f"Could not save settings: {str(e)}")

    def add_recording_controls(self):
        """Add recording controls to the control panel"""
        record_group = QGroupBox("Enregistrement")
        record_layout = QVBoxLayout()
        
        self.record_video_btn = QPushButton("Démarrer l'enregistrement")
        self.record_video_btn.clicked.connect(self.toggle_recording)
        
        record_layout.addWidget(self.record_video_btn)
        record_group.setLayout(record_layout)
        
        self.control_layout.addWidget(record_group)

    def add_statistics_panel(self):
        """Add statistics panel to the control panel"""
        stats_group = QGroupBox("Statistiques")
        stats_layout = QVBoxLayout()
        
        self.total_alerts_label = QLabel("Alertes totales: 0")
        self.today_alerts_label = QLabel("Alertes aujourd'hui: 0")
        
        stats_layout.addWidget(self.total_alerts_label)
        stats_layout.addWidget(self.today_alerts_label)
        stats_group.setLayout(stats_layout)
        
        self.control_layout.addWidget(stats_group)

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
        
        # Camera menu
        camera_menu = menubar.addMenu('Caméra')
        
        config_camera_action = QAction('Configurer Caméra', self)
        config_camera_action.triggered.connect(self.show_camera_config)
        camera_menu.addAction(config_camera_action)

    def show_camera_config(self):
        """Show the camera configuration dialog"""
        if not self.has_cameras:
            QMessageBox.warning(self, "No Camera", "No camera detected on this system.")
            return
        if hasattr(self, 'camera_manager') and self.camera_manager:
            dialog = CameraDialog(self.camera_manager, self)
            dialog.exec_()
        else:
             QMessageBox.warning(self, "Error", "Camera manager not initialized.")

    def create_status_bar(self):
        """Create and configure the status bar"""
        self.status_label = QLabel("System Ready")
        self.statusBar().addWidget(self.status_label)
        self.detection_status_label = QLabel("Detection: OFF")
        self.statusBar().addPermanentWidget(self.detection_status_label)

    def toggle_detection(self):
        """Toggle object detection on/off"""
        if not self.detection_active:
            if self.net is None:
                if not self.load_yolo():
                    self.logger.error("Failed to load YOLO model. Cannot start detection.")
                    QMessageBox.critical(self, "Model Error", "Failed to load YOLO model. Check logs.")
                    return

            self.detection_active = True
            self.logger.info("Object detection activated.")
            self.detection_status_label.setText("Detection: ON")
            self.statusBar().showMessage("Detection Activated", 3000)
        else:
            self.detection_active = False
            self.logger.info("Object detection deactivated.")
            self.detection_status_label.setText("Detection: OFF")
            self.statusBar().showMessage("Detection Deactivated", 3000)

    def load_yolo(self):
        """Lazy loading of YOLO model with correct paths"""
        if self.net is None:
            try:
                self.logger.info("Loading YOLO model...")
                weights_path = self.model_dir / 'yolov3.weights'
                cfg_path = self.model_dir / 'yolov3.cfg'
                names_path = self.model_dir / 'coco.names'

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

                self.net = cv2.dnn.readNet(str(weights_path), str(cfg_path))
                layer_names = self.net.getLayerNames()
                self.logger.info(f"YOLO model read successfully from {weights_path} and {cfg_path}")

                try:
                    unconnected_layers = self.net.getUnconnectedOutLayers()
                    if isinstance(unconnected_layers[0], (list, tuple)):
                        self.output_layers = [layer_names[i[0] - 1] for i in unconnected_layers]
                    else:
                         self.output_layers = [layer_names[i - 1] for i in unconnected_layers]
                except Exception as e:
                    self.logger.error(f"Error getting output layer names: {str(e)}")
                    return False

                with open(names_path, "r") as f:
                    self.classes = [line.strip() for line in f.readlines()]

                self.logger.info("YOLO model loaded successfully")
                self.alert_box.append("✅ YOLO model loaded successfully")
                return True

            except Exception as e:
                self.alert_box.append(f"Error loading YOLO model: {str(e)}")
                self.logger.error(f"Failed to load YOLO model: {str(e)}", exc_info=True)
                return False
        return True

    def send_telegram_alert(self, label, confidence, image=None):
        """Send alert via Telegram (Placeholder)"""
        token = self.settings.get('telegram_bot_token')
        chat_id = self.settings.get('telegram_chat_id')

        if not token or not chat_id or token == "Your_Bot_Token":
            self.logger.warning("Telegram Bot Token or Chat ID not configured. Skipping alert.")
            return

        message = f"🚨 Danger Detected! 🚨\nObject: {label}\nConfidence: {confidence:.2f}"
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {'chat_id': chat_id, 'text': message}

        try:
            response = requests.post(url, data=payload, timeout=10)
            response.raise_for_status()
            self.logger.info(f"Telegram alert sent successfully for {label}.")

            if image is not None:
                try:
                    image_url = f"https://api.telegram.org/bot{token}/sendPhoto"
                    is_success, buffer = cv2.imencode(".jpg", image)
                    if is_success:
                        files = {'photo': ('alert.jpg', buffer.tobytes(), 'image/jpeg')}
                        photo_payload = {'chat_id': chat_id, 'caption': f"{label} detected"}
                        photo_response = requests.post(image_url, data=photo_payload, files=files, timeout=20)
                        photo_response.raise_for_status()
                        self.logger.info("Telegram alert image sent successfully.")
                    else:
                         self.logger.error("Failed to encode image for Telegram.")
                except requests.exceptions.RequestException as img_e:
                    self.logger.error(f"Failed to send Telegram image: {str(img_e)}")
                except Exception as img_e_gen:
                    self.logger.error(f"Unexpected error sending Telegram image: {str(img_e_gen)}")

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to send Telegram message: {str(e)}")
        except Exception as e_gen:
             self.logger.error(f"Unexpected error sending Telegram message: {str(e_gen)}")

    def update_frame(self):
        if not hasattr(self, 'camera_manager') or self.camera_manager is None:
            return
            
        frame = self.camera_manager.get_frame()
        if frame is None:
            return

        if self.detection_active:
            frame = self.process_frame(frame)

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, _ = frame.shape
        qt_img = QImage(frame.data, width, height, width * 3, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_img))

    def update_confidence_threshold(self, value):
        """Update detection confidence threshold"""
        self.confidence_threshold = value / 100.0
        self.statusBar().showMessage(f"Confidence Threshold: {value}%")
        self.logger.info(f"Updated confidence threshold to {self.confidence_threshold:.2f}")

    def update_danger_objects(self):
        """Update the list of dangerous objects from user input"""
        user_input = self.danger_input.text().strip().lower()
        if user_input:
            new_objects = {obj.strip() for obj in user_input.split(",")}
            self.dangerous_objects.update(new_objects)
            self.alert_box.append(f"✅ Dangerous objects updated: {', '.join(self.dangerous_objects)}\n")
            self.logger.info(f"Updated dangerous objects list: {self.dangerous_objects}")
        else:
            self.alert_box.append("Please enter one or more objects separated by commas.")

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

    def toggle_recording(self):
        """Toggle video recording"""
        if not hasattr(self, 'video_recorder') or self.video_recorder is None:
            self.video_recorder = VideoRecorder()
            self.video_recorder.finished.connect(self.recording_finished)
            
        if not self.recording:
            filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.avi"
            recordings_dir = Path.cwd() / "recordings"
            recordings_dir.mkdir(exist_ok=True)
            path = str(recordings_dir / filename)
            
            camera_index = 0
            if hasattr(self, 'camera_manager') and self.camera_manager:
                camera_index = self.camera_manager.camera_index
                
            self.video_recorder.start_recording(path, camera_index)
            self.record_video_btn.setText("Arrêter l'enregistrement")
            self.recording = True
            self.logger.info(f"Started video recording to {path}")
            self.statusBar().showMessage(f"Recording to {filename}...")
        else:
            self.video_recorder.stop_recording()
            self.record_video_btn.setText("Démarrer l'enregistrement")
            self.recording = False

    def recording_finished(self, output_path):
        """Handle the signal when recording finishes"""
        self.logger.info(f"Finished video recording: {output_path}")
        self.statusBar().showMessage(f"Recording saved: {os.path.basename(output_path)}", 5000)

    def init_db(self):
        """ Initialize the SQLite database """
        db_path = Path.cwd() / 'data' / 'danger_detection.db'
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(db_path))
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY,
                object TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                confidence REAL,
                location TEXT
            )
        ''')
        self.conn.commit()
        self.logger.info(f"Database initialized at {db_path}")

    def save_alert_to_db(self, label, confidence, location):
        """Save detected alert to the database"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            self.cursor.execute(
                'INSERT INTO alerts (object, timestamp, confidence, location) VALUES (?, ?, ?, ?)', 
                (label, timestamp, confidence, location)
            )
            self.conn.commit()
            self.logger.info(f"Saved alert to DB: {label} at {timestamp}")
            self.load_alerts_from_db() 
            self.update_statistics() 
        except Exception as e:
            self.logger.error(f"Failed to save alert to DB: {str(e)}")

    def update_statistics(self):
        """Update statistics labels"""
        try:
            self.cursor.execute('SELECT COUNT(*) FROM alerts')
            total = self.cursor.fetchone()[0]
            self.total_alerts_label.setText(f"Alertes totales: {total}")
            
            today = datetime.now().strftime('%Y-%m-%d')
            self.cursor.execute('SELECT COUNT(*) FROM alerts WHERE date(timestamp) = ?', (today,))
            today_count = self.cursor.fetchone()[0]
            self.today_alerts_label.setText(f"Alertes aujourd'hui: {today_count}")
        except Exception as e:
            self.logger.error(f"Failed to update statistics: {str(e)}")

    def process_frame(self, frame):
        """Process a frame with object detection"""
        if frame is None:
            return None

        try:
            height, width = frame.shape[:2]
            
            cv2.putText(frame, f"Detection: {'ON' if self.detection_active else 'OFF'}", 
                      (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            if self.net is None:
                cv2.putText(frame, "YOLO not loaded - Press Ctrl+D to start", 
                          (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                return frame
                
            blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
            self.net.setInput(blob)
            
            outs = self.net.forward(self.output_layers)
            
            class_ids = []
            confidences = []
            boxes = []
            
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
                        x = int(center_x - w/2)
                        y = int(center_y - h/2)
                        
                        class_ids.append(class_id)
                        confidences.append(float(confidence))
                        boxes.append([x, y, w, h])
            
            indexes = cv2.dnn.NMSBoxes(boxes, confidences, self.confidence_threshold, 0.4)
            
            detected_danger = False
            
            if indexes is not None and len(indexes) > 0:
                if isinstance(indexes, tuple):
                    indexes = indexes[0]
                if not isinstance(indexes, (list, np.ndarray)):
                    indexes = [indexes] 
                
                for i in indexes:
                    if i < len(boxes):
                        x, y, w, h = boxes[i]
                        label = str(self.classes[class_ids[i]]).lower()
                        confidence = confidences[i]
                        
                        is_dangerous = any(obj in label for obj in self.dangerous_objects)
                        
                        if is_dangerous:
                            detected_danger = True
                            color = (0, 0, 255)
                            
                            now = datetime.now()
                            last_alert_time = getattr(self, f'_last_alert_{label}', None)
                            if last_alert_time is None or (now - last_alert_time).total_seconds() > self.alert_timeout:
                                setattr(self, f'_last_alert_{label}', now)
                                
                                self.alert_box.append(f"⚠️ ALERT: {label} detected! (Confidence: {confidence:.2f})")
                                location_str = f"x:{x},y:{y},w:{w},h:{h}"
                                self.save_alert_to_db(label, confidence, location_str)
                                alert_frame = frame.copy()
                                cv2.rectangle(alert_frame, (x, y), (x + w, y + h), color, 2)
                                cv2.putText(alert_frame, f"{label} ({confidence:.2f})",
                                          (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                                self.send_telegram_alert(label, confidence, alert_frame)
                        else:
                            color = (0, 255, 0)
                        
                        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                        cv2.putText(frame, f"{label} ({confidence:.2f})", 
                                  (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    else:
                        self.logger.warning(f"Invalid index {i} encountered during NMS processing.")
            
            cv2.putText(frame, f"Objects: {len(indexes) if indexes is not None else 0}", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
            if detected_danger:
                cv2.putText(frame, "DANGER DETECTED!", 
                          (width // 2 - 100, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                
            return frame
            
        except Exception as e:
            self.logger.error(f"Error processing frame: {str(e)}", exc_info=True)
            cv2.putText(frame, f"Detection Error", 
                      (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            return frame

    def closeEvent(self, event):
        """Handle application close event"""
        self.logger.info("Closing application...")
        if hasattr(self, 'timer') and self.timer is not None:
            self.timer.stop()
            self.logger.info("Stopped frame update timer.")

        if hasattr(self, 'camera_manager') and self.camera_manager is not None:
            self.camera_manager.stop()
            self.logger.info("Stopped camera manager.")

        if hasattr(self, 'video_recorder') and self.video_recorder is not None and self.video_recorder.isRunning():
            self.logger.info("Stopping video recorder...")
            self.video_recorder.stop_recording()
            self.video_recorder.wait()
            self.logger.info("Video recorder stopped.")

        if hasattr(self, 'conn'):
            self.conn.close()
            self.logger.info("Closed database connection.")

        cv2.destroyAllWindows()
        self.logger.info("Application closed.")
        event.accept()
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

class CameraDialog(QDialog):
    def __init__(self, camera_manager, parent=None):
        super().__init__(parent)
        self.camera_manager = camera_manager
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Configuration Caméra")
        layout = QVBoxLayout()

        # Section Caméra USB
        usb_group = QGroupBox("Caméra USB")
        usb_layout = QVBoxLayout()
        
        self.camera_combo = QComboBox()
        self.refresh_camera_list()
        
        self.connect_usb_btn = QPushButton("Connecter USB")
        self.connect_usb_btn.clicked.connect(self.connect_usb_camera)

        usb_layout.addWidget(QLabel("Sélectionner une caméra :"))
        usb_layout.addWidget(self.camera_combo)
        usb_layout.addWidget(self.connect_usb_btn)
        usb_group.setLayout(usb_layout)

        # Section Caméra IP
        ip_group = QGroupBox("Caméra IP (Téléphone)")
        ip_layout = QFormLayout()
        
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.100")
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("8080")
        
        self.connect_ip_btn = QPushButton("Connecter IP")
        self.connect_ip_btn.clicked.connect(self.connect_ip_camera)

        ip_layout.addRow("Adresse IP:", self.ip_input)
        ip_layout.addRow("Port:", self.port_input)
        ip_layout.addRow(self.connect_ip_btn)
        ip_group.setLayout(ip_layout)

        # Ajouter les sections au layout principal
        layout.addWidget(usb_group)
        layout.addWidget(ip_group)
        
        # Bouton de fermeture
        self.close_btn = QPushButton("Fermer")
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)

        self.setLayout(layout)

    def refresh_camera_list(self):
        self.camera_combo.clear()
        cameras = self.camera_manager.get_camera_list()
        for cam_id in cameras:
            self.camera_combo.addItem(f"Caméra {cam_id}", cam_id)

    def connect_usb_camera(self):
        if self.camera_combo.currentData() is not None:
            device_id = self.camera_combo.currentData()
            QApplication.setOverrideCursor(Qt.WaitCursor)
            success = self.camera_manager.connect_usb_camera(device_id)
            QApplication.restoreOverrideCursor()
            
            if success:
                QMessageBox.information(self, "Succès", f"Caméra USB {device_id} connectée!")
            else:
                QMessageBox.warning(self, "Erreur", 
                    "Impossible de connecter la caméra USB.\n"
                    "Vérifiez que la caméra n'est pas utilisée par une autre application.")

    def connect_ip_camera(self):
        ip = self.ip_input.text().strip()
        port = self.port_input.text().strip()
        
        if not ip:
            QMessageBox.warning(self, "Erreur", "Veuillez entrer une adresse IP")
            return
            
        try:
            port = int(port) if port else 8080
        except ValueError:
            QMessageBox.warning(self, "Erreur", "Le port doit être un nombre")
            return
            
        QApplication.setOverrideCursor(Qt.WaitCursor)
        success = self.camera_manager.connect_ip_camera(ip, port)
        QApplication.restoreOverrideCursor()
        
        if success:
            QMessageBox.information(self, "Succès", f"Caméra IP connectée à {ip}:{port}!")
        else:
            QMessageBox.warning(self, "Erreur", 
                "Impossible de connecter la caméra IP.\n"
                "Vérifiez l'adresse IP, le port et que l'application est en cours d'exécution.")

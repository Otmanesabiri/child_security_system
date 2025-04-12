import cv2
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                           QLabel, QComboBox, QGroupBox, QFormLayout, 
                           QSpinBox, QCheckBox, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
import logging

from src.core.camera_utils import list_available_cameras, get_camera_details

class CameraDialog(QDialog):
    """
    Dialog for camera configuration
    """
    def __init__(self, camera_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Camera Configuration")
        self.setMinimumSize(640, 500)
        
        self.logger = logging.getLogger(__name__)
        self.camera_manager = camera_manager
        
        # Initialize UI
        self.init_ui()
        
        # Start preview timer
        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self.update_preview)
        self.preview_timer.start(50)  # 20 fps
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Camera selector
        camera_group = QGroupBox("Select Camera")
        camera_layout = QFormLayout()
        
        # Camera dropdown
        self.camera_combo = QComboBox()
        self.populate_cameras()
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.populate_cameras)
        
        camera_selector_layout = QHBoxLayout()
        camera_selector_layout.addWidget(self.camera_combo, 1)
        camera_selector_layout.addWidget(refresh_btn, 0)
        
        camera_layout.addRow("Camera:", camera_selector_layout)
        
        # Apply button
        apply_camera_btn = QPushButton("Apply")
        apply_camera_btn.clicked.connect(self.apply_camera_selection)
        camera_layout.addRow("", apply_camera_btn)
        
        camera_group.setLayout(camera_layout)
        layout.addWidget(camera_group)
        
        # Camera settings
        settings_group = QGroupBox("Camera Settings")
        settings_layout = QFormLayout()
        
        # Resolution
        resolution_layout = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(320, 3840)
        self.width_spin.setValue(640)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(240, 2160)
        self.height_spin.setValue(480)
        
        resolution_layout.addWidget(self.width_spin)
        resolution_layout.addWidget(QLabel("x"))
        resolution_layout.addWidget(self.height_spin)
        
        settings_layout.addRow("Resolution:", resolution_layout)
        
        # Apply settings button
        apply_settings_btn = QPushButton("Apply Settings")
        apply_settings_btn.clicked.connect(self.apply_camera_settings)
        settings_layout.addRow("", apply_settings_btn)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Camera preview
        preview_group = QGroupBox("Camera Preview")
        preview_layout = QVBoxLayout()
        
        self.preview_label = QLabel("No preview available")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(320, 240)
        self.preview_label.setStyleSheet("background-color: #222; color: white;")
        
        preview_layout.addWidget(self.preview_label)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        
        screenshot_btn = QPushButton("Take Screenshot")
        screenshot_btn.clicked.connect(self.take_screenshot)
        
        button_layout.addWidget(screenshot_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def populate_cameras(self):
        """Populate the camera dropdown with available cameras"""
        current_index = self.camera_combo.currentData()
        self.camera_combo.clear()
        
        cameras = list_available_cameras()
        if not cameras:
            self.camera_combo.addItem("No cameras found", -1)
            return
            
        for idx in cameras:
            details = get_camera_details(idx)
            if details:
                label = f"Camera {idx} ({details['width']}x{details['height']})"
                self.camera_combo.addItem(label, idx)
            else:
                self.camera_combo.addItem(f"Camera {idx}", idx)
                
        # Restore previous selection if possible
        if current_index is not None:
            index = self.camera_combo.findData(current_index)
            if index >= 0:
                self.camera_combo.setCurrentIndex(index)
                
    def apply_camera_selection(self):
        """Apply the selected camera"""
        camera_idx = self.camera_combo.currentData()
        if camera_idx == -1:
            QMessageBox.warning(self, "No Camera", "No camera selected")
            return
            
        success = self.camera_manager.open_camera(camera_idx)
        if success:
            # Update resolution spinners with actual values
            resolution = self.camera_manager.get_camera_resolution()
            if resolution:
                self.width_spin.setValue(resolution[0])
                self.height_spin.setValue(resolution[1])
            QMessageBox.information(self, "Camera Changed", f"Successfully switched to camera {camera_idx}")
        else:
            QMessageBox.warning(self, "Camera Error", f"Failed to open camera {camera_idx}")
            
    def apply_camera_settings(self):
        """Apply camera settings"""
        width = self.width_spin.value()
        height = self.height_spin.value()
        
        success = self.camera_manager.set_camera_resolution(width, height)
        if success:
            QMessageBox.information(self, "Settings Applied", f"Resolution set to {width}x{height}")
        else:
            QMessageBox.warning(self, "Settings Failed", 
                             "Failed to apply camera settings.\n"
                             f"The camera may not support {width}x{height} resolution.")
            
            # Update spinners with actual values
            resolution = self.camera_manager.get_camera_resolution()
            if resolution:
                self.width_spin.setValue(resolution[0])
                self.height_spin.setValue(resolution[1])
                
    def update_preview(self):
        """Update the camera preview"""
        frame = self.camera_manager.get_frame()
        if frame is None:
            return
            
        # Convert frame to QImage for display
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        
        # Create QImage and scale to fit the preview label
        image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        
        # Scale while maintaining aspect ratio
        label_size = self.preview_label.size()
        scaled_pixmap = pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        self.preview_label.setPixmap(scaled_pixmap)
        
    def take_screenshot(self):
        """Take a screenshot from the camera"""
        filepath = self.camera_manager.save_screenshot()
        if filepath:
            QMessageBox.information(self, "Screenshot Saved", f"Screenshot saved to {filepath}")
        else:
            QMessageBox.warning(self, "Screenshot Failed", "Failed to save screenshot")
            
    def closeEvent(self, event):
        """Handle dialog close event"""
        self.preview_timer.stop()
        event.accept()

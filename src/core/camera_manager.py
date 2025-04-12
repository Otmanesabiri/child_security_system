import cv2
import logging
import time
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class CameraManager:
    """
    Class to manage camera devices
    """
    def __init__(self, camera_index=0):
        """
        Initialize the camera manager
        
        Args:
            camera_index (int): Index of the camera to use
        """
        self.logger = logging.getLogger(__name__)
        self.camera_index = camera_index
        self.camera = None
        self.is_running = False
        self.last_frame = None
        self.open_camera()
    
    def open_camera(self, camera_index=None):
        """
        Open a camera device
        
        Args:
            camera_index (int, optional): Index of the camera to open.
                                         If None, uses the current index.
        
        Returns:
            bool: True if camera opened successfully, False otherwise
        """
        if camera_index is not None:
            self.camera_index = camera_index
            
        # Close any existing camera
        if self.camera is not None:
            self.camera.release()
            
        try:
            self.logger.info(f"Opening camera with index: {self.camera_index}")
            self.camera = cv2.VideoCapture(self.camera_index)
            
            if not self.camera.isOpened():
                self.logger.error(f"Failed to open camera {self.camera_index}")
                return False
                
            # Get camera information
            width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.camera.get(cv2.CAP_PROP_FPS)
            
            self.logger.info(f"Camera opened: {width}x{height} at {fps} FPS")
            self.is_running = True
            return True
            
        except Exception as e:
            self.logger.error(f"Error opening camera: {str(e)}")
            return False
    
    def get_frame(self):
        """
        Get a frame from the camera
        
        Returns:
            numpy.ndarray: Frame image or None if camera is not available
        """
        if self.camera is None or not self.camera.isOpened():
            if not self.open_camera():
                return None
                
        try:
            ret, frame = self.camera.read()
            if ret:
                self.last_frame = frame
                return frame
            else:
                self.logger.warning("Failed to read frame from camera")
                return self.last_frame  # Return last good frame or None
        except Exception as e:
            self.logger.error(f"Error getting frame: {str(e)}")
            return self.last_frame
    
    def set_camera_property(self, prop_id, value):
        """
        Set a camera property
        
        Args:
            prop_id: OpenCV camera property ID
            value: Value to set
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.camera is None or not self.camera.isOpened():
            return False
            
        return self.camera.set(prop_id, value)
    
    def get_camera_property(self, prop_id):
        """
        Get a camera property value
        
        Args:
            prop_id: OpenCV camera property ID
            
        Returns:
            Value of the property or None if camera is not available
        """
        if self.camera is None or not self.camera.isOpened():
            return None
            
        return self.camera.get(prop_id)
    
    def get_camera_resolution(self):
        """
        Get the current camera resolution
        
        Returns:
            tuple: (width, height) or None if camera is not available
        """
        if self.camera is None or not self.camera.isOpened():
            return None
            
        width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return (width, height)
    
    def set_camera_resolution(self, width, height):
        """
        Set the camera resolution
        
        Args:
            width (int): Desired width
            height (int): Desired height
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.camera is None or not self.camera.isOpened():
            return False
            
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        # Verify if resolution was actually set
        actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        return (actual_width == width and actual_height == height)
    
    def save_screenshot(self, output_dir="screenshots"):
        """
        Save a screenshot from the camera
        
        Args:
            output_dir (str): Directory to save the screenshot
            
        Returns:
            str: Path to the saved file or None if failed
        """
        frame = self.get_frame()
        if frame is None:
            return None
            
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.jpg"
        filepath = os.path.join(output_dir, filename)
        
        # Save the image
        try:
            cv2.imwrite(filepath, frame)
            self.logger.info(f"Screenshot saved: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Error saving screenshot: {str(e)}")
            return None
    
    def stop(self):
        """
        Stop and release the camera
        """
        self.is_running = False
        if self.camera is not None:
            self.camera.release()
            self.camera = None
            self.logger.info("Camera released")

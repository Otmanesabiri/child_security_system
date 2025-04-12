import logging
import cv2
from datetime import datetime
import os

class NotificationManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("NotificationManager initialized")
        
        # Create alerts directory if it doesn't exist
        self.alerts_dir = "alerts"
        os.makedirs(self.alerts_dir, exist_ok=True)
        
    def send_alert(self, object_type, confidence, image):
        """
        Send an alert about a detected dangerous object
        
        Args:
            object_type (str): Type of dangerous object detected
            confidence (float): Detection confidence score
            image (numpy.ndarray): Image frame containing the detected object
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"alert_{object_type}_{timestamp}.jpg"
        filepath = os.path.join(self.alerts_dir, filename)
        
        # Save the image with detection
        try:
            cv2.imwrite(filepath, image)
            self.logger.info(f"Alert image saved as {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to save alert image: {str(e)}")
        
        # Here you would implement actual notification sending (email, SMS, etc.)
        self.logger.info(f"Alert sent: {object_type} detected with {confidence:.2f} confidence")
        
        # Return True if notification was sent successfully
        return True
    
    def send_email_alert(self, recipient, subject, message, image_path=None):
        """
        Send an email alert (placeholder for future implementation)
        
        Args:
            recipient (str): Email address of recipient
            subject (str): Email subject
            message (str): Email body text
            image_path (str, optional): Path to image attachment
            
        Returns:
            bool: True if email was sent successfully
        """
        # This is a placeholder for actual email sending implementation
        self.logger.info(f"Would send email to {recipient} with subject '{subject}'")
        return True

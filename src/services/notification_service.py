import requests
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime
import cv2
from pathlib import Path
import logging

class NotificationManager:
    def __init__(self, config_path='config.json'):
        self.config = self._load_config(config_path)
        self.setup_logging()
        
    def _load_config(self, config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def setup_logging(self):
        logging.basicConfig(
            filename='notifications.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def send_telegram_alert(self, message, image_path=None):
        if not self.config['notifications']['telegram']['enabled']:
            return False
            
        try:
            bot_token = self.config['notifications']['telegram']['bot_token']
            chat_id = self.config['notifications']['telegram']['chat_id']
            
            # Envoyer le message
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            response = requests.post(url, data={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            })
            
            # Envoyer l'image si disponible
            if image_path and Path(image_path).exists():
                url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
                with open(image_path, 'rb') as photo:
                    requests.post(url, files={'photo': photo}, data={
                        "chat_id": chat_id,
                        "caption": "Capture de la détection"
                    })
            
            logging.info(f"Alert sent to Telegram: {message}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to send Telegram alert: {str(e)}")
            return False
    
    def send_email_alert(self, subject, message, image_path=None):
        if not self.config['notifications']['email']['enabled']:
            return False
            
        try:
            email_config = self.config['notifications']['email']
            msg = MIMEMultipart()
            msg['From'] = email_config['sender_email']
            msg['To'] = email_config['recipient_email']
            msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'plain'))
            
            # Ajouter l'image si disponible
            if image_path and Path(image_path).exists():
                with open(image_path, 'rb') as f:
                    img = MIMEImage(f.read())
                    img.add_header('Content-Disposition', 'attachment', filename=Path(image_path).name)
                    msg.attach(img)
            
            # Connexion au serveur SMTP
            with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
                server.starttls()
                server.login(email_config['sender_email'], email_config['sender_password'])
                server.send_message(msg)
            
            logging.info(f"Email alert sent: {subject}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to send email alert: {str(e)}")
            return False
    
    def save_detection_image(self, frame, object_name):
        """Sauvegarde une image de la détection"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"detection_{object_name}_{timestamp}.jpg"
            path = Path("detections") / filename
            path.parent.mkdir(exist_ok=True)
            
            cv2.imwrite(str(path), frame)
            logging.info(f"Detection image saved: {filename}")
            return str(path)
            
        except Exception as e:
            logging.error(f"Failed to save detection image: {str(e)}")
            return None
    
    def send_alert(self, object_name, confidence, frame=None):
        """Envoie une alerte sur tous les canaux configurés"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = (
            f"⚠️ ALERTE DE SÉCURITÉ ⚠️\n\n"
            f"Objet dangereux détecté: {object_name}\n"
            f"Niveau de confiance: {confidence:.2%}\n"
            f"Horodatage: {timestamp}"
        )
        
        # Sauvegarder l'image si un frame est fourni
        image_path = None
        if frame is not None:
            image_path = self.save_detection_image(frame, object_name)
        
        # Envoyer les notifications
        telegram_sent = self.send_telegram_alert(message, image_path)
        email_sent = self.send_email_alert(
            f"Alerte de sécurité - {object_name} détecté",
            message,
            image_path
        )
        
        return telegram_sent or email_sent  # Retourne True si au moins une notification a été envoyée
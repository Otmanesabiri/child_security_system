import cv2
import urllib.request
import numpy as np
import threading
from queue import Queue
import logging

class CameraManager:
    def __init__(self):
        self.camera = None
        self.ip_stream_url = None
        self.frame_queue = Queue(maxsize=2)
        self.is_running = False
        self.logger = logging.getLogger('CameraManager')

    def connect_usb_camera(self, device_id=0):
        """Connecter une caméra USB"""
        try:
            if self.camera is not None:
                self.stop()  # Stop any existing camera

            self.camera = cv2.VideoCapture(device_id, cv2.CAP_DSHOW)  # Use DirectShow
            if not self.camera.isOpened():
                raise Exception(f"Impossible de connecter la caméra USB {device_id}")
                
            # Test the camera
            ret, _ = self.camera.read()
            if not ret:
                raise Exception("Camera test frame failed")

            self.is_running = True
            threading.Thread(target=self._capture_loop, daemon=True).start()
            self.logger.info(f"Connected to USB camera {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur de connexion USB: {str(e)}")
            if self.camera is not None:
                self.camera.release()
                self.camera = None
            return False

    def connect_ip_camera(self, ip_address, port=8080):
        """Connecter une caméra IP (téléphone)"""
        try:
            if self.camera is not None:
                self.stop()  # Stop any existing camera

            print(f"Attempting to connect to IP camera at {ip_address}:{port}")
            
            # Modifier les URLs pour supporter plus de formats
            urls = [
                f"http://{ip_address}:{port}/video",
                f"http://{ip_address}:{port}/videofeed",
                f"http://{ip_address}:{port}/shot.jpg",
                f"rtsp://{ip_address}:{port}/h264_ulaw.sdp",  # Format RTSP
                f"http://{ip_address}:{port}/stream.mjpeg",   # Format MJPEG
                f"http://{ip_address}:{port}/camera/live"
            ]

            for url in urls:
                print(f"Trying URL: {url}")
                try:
                    self.logger.info(f"Trying to connect to {url}")
                    # Ajouter des options pour améliorer la capture
                    stream = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                    stream.set(cv2.CAP_PROP_BUFFERSIZE, 3)
                    
                    if stream.isOpened():
                        ret, frame = stream.read()
                        if ret and frame is not None:
                            print(f"Successfully connected to {url}")
                            print(f"Frame size: {frame.shape}")
                            self.camera = stream
                            self.ip_stream_url = url
                            self.is_running = True
                            self.frame_queue = Queue(maxsize=3)  # Reset queue
                            threading.Thread(target=self._capture_loop, daemon=True).start()
                            self.logger.info(f"Successfully connected to IP camera at {url}")
                            return True
                except Exception as e:
                    print(f"Failed to connect to {url}: {str(e)}")
                    self.logger.warning(f"Failed to connect to {url}: {str(e)}")
                    continue

            raise Exception("No working connection found for IP camera")
            
        except Exception as e:
            print(f"Camera connection error: {str(e)}")
            self.logger.error(f"Erreur de connexion IP: {str(e)}")
            return False

    def _capture_loop(self):
        """Boucle de capture des images améliorée"""
        frame_count = 0
        while self.is_running and self.camera is not None:
            try:
                ret, frame = self.camera.read()
                if ret and frame is not None:
                    frame_count += 1
                    # Ne traiter qu'une image sur 2 pour réduire la charge
                    if frame_count % 2 == 0:
                        # Redimensionner l'image pour une meilleure performance
                        frame = cv2.resize(frame, (640, 480))
                        if not self.frame_queue.full():
                            self.frame_queue.put(frame)
                else:
                    self.logger.warning("Failed to read frame")
                    # Tentative de reconnexion
                    if self.ip_stream_url:
                        self.camera = cv2.VideoCapture(self.ip_stream_url, cv2.CAP_FFMPEG)
                    break
            except Exception as e:
                self.logger.error(f"Error in capture loop: {str(e)}")
                break

    def get_frame(self):
        """Récupérer la dernière image"""
        try:
            return self.frame_queue.get_nowait()
        except:
            return None

    def get_camera_list(self):
        """Liste toutes les caméras USB disponibles"""
        available_cameras = []
        tested_ports = 0
        max_ports = 10  # Maximum number of ports to test
        
        while tested_ports < max_ports:
            try:
                cap = cv2.VideoCapture(tested_ports, cv2.CAP_DSHOW)  # Use DirectShow
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        available_cameras.append(tested_ports)
                    cap.release()
            except:
                pass
            tested_ports += 1
            
        return available_cameras

    def stop(self):
        """Arrêter la capture"""
        self.is_running = False
        if self.camera is not None:
            self.camera.release()
            self.camera = None

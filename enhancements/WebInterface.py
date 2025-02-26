from flask import Flask, render_template, Response, jsonify
import cv2
import threading
import json
from datetime import datetime

app = Flask(__name__)

class WebInterface:
    def __init__(self, detection_app):
        self.app = app
        self.detection_app = detection_app
        
    def gen_frames(self):
        while True:
            frame = self.detection_app.get_current_frame()
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                           
    def start(self, host='0.0.0.0', port=5000):
        self.setup_routes()
        threading.Thread(target=self.app.run, 
                       kwargs={'host': host, 'port': port}, 
                       daemon=True).start()
        
    def setup_routes(self):
        @app.route('/')
        def index():
            return render_template('index.html')
            
        @app.route('/video_feed')
        def video_feed():
            return Response(self.gen_frames(),
                          mimetype='multipart/x-mixed-replace; boundary=frame')
                          
        @app.route('/alerts')
        def get_alerts():
            alerts = self.detection_app.get_recent_alerts()
            return jsonify(alerts)

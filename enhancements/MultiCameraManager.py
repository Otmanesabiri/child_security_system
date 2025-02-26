import cv2
import threading
from queue import Queue

class CameraStream:
    def __init__(self, src=0, name="Camera"):
        self.stream = cv2.VideoCapture(src)
        self.name = name
        self.frame_queue = Queue(maxsize=2)
        self.stopped = False
        
    def start(self):
        threading.Thread(target=self.update, daemon=True).start()
        return self
        
    def update(self):
        while not self.stopped:
            if not self.frame_queue.full():
                ret, frame = self.stream.read()
                if ret:
                    if not self.frame_queue.empty():
                        self.frame_queue.get()
                    self.frame_queue.put(frame)
                    
    def read(self):
        return self.frame_queue.get() if not self.frame_queue.empty() else None
        
    def stop(self):
        self.stopped = True
        self.stream.release()

class MultiCameraManager:
    def __init__(self):
        self.cameras = {}
        
    def add_camera(self, src, name):
        camera = CameraStream(src, name)
        self.cameras[name] = camera
        camera.start()
        
    def remove_camera(self, name):
        if name in self.cameras:
            self.cameras[name].stop()
            del self.cameras[name]
            
    def get_frame(self, name):
        if name in self.cameras:
            return self.cameras[name].read()
        return None
        
    def get_all_frames(self):
        frames = {}
        for name, camera in self.cameras.items():
            frame = camera.read()
            if frame is not None:
                frames[name] = frame
        return frames
        
    def close_all(self):
        for camera in self.cameras.values():
            camera.stop()
        self.cameras.clear()

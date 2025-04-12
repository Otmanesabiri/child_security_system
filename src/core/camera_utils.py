import cv2
import logging
import platform
import os
import subprocess
import sys

logger = logging.getLogger(__name__)

def list_available_cameras(max_cameras=10):
    """
    Attempt to detect available cameras on the system.
    
    Args:
        max_cameras (int): Maximum number of camera indices to check
        
    Returns:
        list: List of available camera indices
    """
    available_cameras = []
    
    for i in range(max_cameras):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                available_cameras.append(i)
                logger.info(f"Found camera at index {i}")
            cap.release()
    
    return available_cameras

def get_camera_details(camera_index):
    """
    Get detailed information about a camera
    
    Args:
        camera_index (int): Index of the camera to get details for
        
    Returns:
        dict: Dictionary containing camera details or None if camera not available
    """
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        return None
        
    details = {
        "index": camera_index,
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "backend": cap.getBackendName() if hasattr(cap, 'getBackendName') else "Unknown"
    }
    
    cap.release()
    return details

def diagnose_camera_issues():
    """
    Diagnose common camera issues and return potential solutions
    
    Returns:
        dict: Diagnostic information and potential solutions
    """
    diagnosis = {
        "system": platform.system(),
        "opencv_version": cv2.__version__,
        "available_cameras": [],
        "suggestions": []
    }
    
    # Check for available cameras
    available_cameras = list_available_cameras()
    diagnosis["available_cameras"] = available_cameras
    
    if not available_cameras:
        # Generate recommendations based on OS
        if platform.system() == "Linux":
            diagnosis["suggestions"].append("Run 'ls -l /dev/video*' to check for video devices")
            diagnosis["suggestions"].append("Ensure you have permissions to access camera devices: sudo usermod -a -G video $USER")
            diagnosis["suggestions"].append("Check if camera is recognized: lsusb")
        elif platform.system() == "Windows":
            diagnosis["suggestions"].append("Check Device Manager for camera devices")
            diagnosis["suggestions"].append("Make sure camera is not being used by another application")
        elif platform.system() == "Darwin":  # macOS
            diagnosis["suggestions"].append("Check System Information for camera details")
            diagnosis["suggestions"].append("Make sure you've granted camera permissions to the application")
    
    diagnosis["suggestions"].append("Try restarting your computer")
    diagnosis["suggestions"].append("Check if the camera works in other applications")
    diagnosis["suggestions"].append("Make sure the camera is properly connected")
    
    return diagnosis

def test_camera(camera_index=0, display_time=5):
    """
    Test a camera by opening a window and showing the feed for a few seconds
    
    Args:
        camera_index (int): Index of the camera to test
        display_time (int): Time in seconds to display the feed
        
    Returns:
        bool: True if camera test was successful, False otherwise
    """
    import time
    
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"Could not open camera {camera_index}")
        return False
        
    print(f"Testing camera {camera_index}...")
    print("Press 'q' to quit test")
    
    start_time = time.time()
    success = False
    
    while time.time() - start_time < display_time:
        ret, frame = cap.read()
        
        if not ret:
            print(f"Could not read frame from camera {camera_index}")
            break
            
        success = True
        cv2.imshow(f"Camera {camera_index} Test", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    return success

if __name__ == "__main__":
    # When run directly, provide camera diagnostics
    print("Camera Diagnostic Tool")
    print("-" * 30)
    
    available = list_available_cameras()
    print(f"Available cameras: {available}")
    
    if available:
        for cam_idx in available:
            details = get_camera_details(cam_idx)
            print(f"Camera {cam_idx}: {details['width']}x{details['height']} @ {details['fps']} FPS")
            
        # Test the first available camera
        test_camera(available[0])
    else:
        print("No cameras detected.")
        diagnosis = diagnose_camera_issues()
        print("\nTroubleshooting suggestions:")
        for i, suggestion in enumerate(diagnosis["suggestions"], 1):
            print(f"{i}. {suggestion}")

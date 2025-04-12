#!/usr/bin/env python3
import sys
import cv2
import argparse
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.camera_utils import list_available_cameras, test_camera, diagnose_camera_issues

def main():
    parser = argparse.ArgumentParser(description="Test camera access for the Child Security System")
    parser.add_argument("--list", action="store_true", help="List all available cameras")
    parser.add_argument("--test", type=int, default=-1, help="Test specific camera index (default: first available)")
    parser.add_argument("--diagnose", action="store_true", help="Run diagnostic checks")
    
    args = parser.parse_args()
    
    if args.list:
        print("Searching for available cameras...")
        cameras = list_available_cameras(20)  # Check up to 20 camera indices
        
        if cameras:
            print(f"Found {len(cameras)} camera(s): {cameras}")
        else:
            print("No cameras detected!")
            
    if args.diagnose:
        print("\nRunning camera diagnostics...")
        diagnosis = diagnose_camera_issues()
        
        print(f"System: {diagnosis['system']}")
        print(f"OpenCV version: {diagnosis['opencv_version']}")
        print(f"Available cameras: {diagnosis['available_cameras']}")
        
        print("\nSuggestions:")
        for i, suggestion in enumerate(diagnosis['suggestions'], 1):
            print(f"{i}. {suggestion}")
    
    if args.test >= 0:
        # Test specific camera index
        test_camera(args.test, display_time=10)
    elif args.test == -1 and not args.list and not args.diagnose:
        # If no arguments provided, try to test the first available camera
        cameras = list_available_cameras()
        
        if cameras:
            print(f"Testing first available camera (index {cameras[0]})...")
            test_camera(cameras[0], display_time=10)
        else:
            print("No cameras available to test!")
            print("\nPossible solutions:")
            diagnosis = diagnose_camera_issues()
            for i, suggestion in enumerate(diagnosis['suggestions'], 1):
                print(f"{i}. {suggestion}")

if __name__ == "__main__":
    main()

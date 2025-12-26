#!/usr/bin/env python3
"""
Test script để kiểm tra YOLO có hoạt động không
"""
import sys
import os
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

print("Testing YOLO import...")

try:
    print("1. Importing torch...")
    import torch
    print(f"   ✓ PyTorch version: {torch.__version__}")
except Exception as e:
    print(f"   ✗ Error importing torch: {e}")
    sys.exit(1)

try:
    print("2. Importing ultralytics...")
    from ultralytics import YOLO
    print("   ✓ Ultralytics imported")
except Exception as e:
    print(f"   ✗ Error importing ultralytics: {e}")
    sys.exit(1)

try:
    print("3. Loading YOLO model...")
    model = YOLO('yolov8n.pt')
    print("   ✓ YOLO model loaded")
except Exception as e:
    print(f"   ✗ Error loading YOLO model: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("4. Testing VehicleDetector...")
    from vehicle_detection import VehicleDetector
    detector = VehicleDetector(model_path='yolov8n.pt', conf_threshold=0.25)
    print("   ✓ VehicleDetector initialized")
except Exception as e:
    print(f"   ✗ Error initializing VehicleDetector: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✓ All tests passed! YOLO is working correctly.")


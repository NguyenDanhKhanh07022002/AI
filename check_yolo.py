#!/usr/bin/env python3
"""
Script để test YOLO import an toàn với timeout
"""
import sys
import signal
import time
from pathlib import Path

def timeout_handler(signum, frame):
    raise TimeoutError("YOLO import timeout")

# Set timeout 10 giây
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(10)

try:
    print("Testing YOLO import with 10s timeout...")
    print("1. Importing torch...")
    
    import torch
    print(f"   ✓ PyTorch version: {torch.__version__}")
    
    print("2. Importing ultralytics...")
    from ultralytics import YOLO
    print("   ✓ Ultralytics imported")
    
    print("3. Loading YOLO model...")
    model = YOLO('yolov8n.pt')
    print("   ✓ YOLO model loaded")
    
    signal.alarm(0)  # Cancel timeout
    print("\n✓ SUCCESS: YOLO is working!")
    sys.exit(0)
    
except TimeoutError:
    signal.alarm(0)
    print("\n✗ TIMEOUT: YOLO import took too long (>10s)")
    print("  This usually means Bus error or system crash")
    sys.exit(1)
    
except (SystemError, OSError, RuntimeError) as e:
    signal.alarm(0)
    print(f"\n✗ SYSTEM ERROR: {type(e).__name__} - {str(e)}")
    print("  This is likely a Bus error or compatibility issue")
    sys.exit(1)
    
except Exception as e:
    signal.alarm(0)
    print(f"\n✗ ERROR: {type(e).__name__} - {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


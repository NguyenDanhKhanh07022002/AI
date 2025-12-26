#!/usr/bin/env python3
"""
Quick test script - Test nhanh các chức năng cơ bản
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))

def quick_test():
    """Quick test các imports và initialization"""
    print("Running quick tests...")
    
    # Test 1: Imports
    print("\n1. Testing imports...")
    try:
        from utils import setup_logging, load_config
        from video_segmentation import segment_video
        from image_extraction import extract_frames
        from roi_processing import apply_roi_mask
        from duplicate_detection import check_duplicate
        from camera_shift_detection import detect_camera_shift
        from vehicle_detection import VehicleDetector
        from vehicle_tracking import VehicleTracker
        from counting import VehicleCounter
        from storage import initialize_database
        print("   ✓ All imports successful")
    except Exception as e:
        print(f"   ✗ Import failed: {e}")
        return False
    
    # Test 2: Config
    print("\n2. Testing config...")
    try:
        config_path = project_root / 'config' / 'roi_config.json'
        if config_path.exists():
            config = load_config(str(config_path))
            print("   ✓ Config loaded")
        else:
            print("   ⚠ Config file not found")
    except Exception as e:
        print(f"   ✗ Config test failed: {e}")
        return False
    
    # Test 3: Database
    print("\n3. Testing database...")
    try:
        db_path = project_root / 'data' / 'database' / 'test_quick.db'
        db_path.parent.mkdir(parents=True, exist_ok=True)
        initialize_database(str(db_path))
        print("   ✓ Database initialized")
        # Cleanup
        if db_path.exists():
            db_path.unlink()
    except Exception as e:
        print(f"   ✗ Database test failed: {e}")
        return False
    
    # Test 4: Vehicle Detector (không download model)
    print("\n4. Testing vehicle detector...")
    try:
        detector = VehicleDetector(model_path='yolov8n.pt')
        print("   ✓ Vehicle detector initialized")
        print("   ⚠ Note: YOLO model will be downloaded on first use")
    except Exception as e:
        print(f"   ⚠ Vehicle detector: {e}")
        print("   (This is OK if model not downloaded yet)")
    
    print("\n" + "=" * 50)
    print("Quick test completed!")
    print("=" * 50)
    return True

if __name__ == '__main__':
    success = quick_test()
    sys.exit(0 if success else 1)


#!/usr/bin/env python3
"""
Test script tự động cho System K Vehicle Counting Tool
"""
import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))

import cv2
import logging
from utils import setup_logging, load_config, create_directories

# Setup logging
logger = setup_logging(logging.INFO)

def test_imports():
    """Test tất cả imports"""
    logger.info("Testing imports...")
    try:
        from video_segmentation import segment_video
        from image_extraction import extract_frames
        from roi_processing import apply_roi_mask
        from duplicate_detection import check_duplicate, save_image_hash
        from camera_shift_detection import detect_camera_shift
        from vehicle_detection import VehicleDetector
        from vehicle_tracking import VehicleTracker
        from counting import VehicleCounter
        from storage import initialize_database, save_counting_result
        logger.info("✓ All imports successful")
        return True
    except Exception as e:
        logger.error(f"✗ Import failed: {e}")
        return False

def test_config():
    """Test load config"""
    logger.info("Testing config loading...")
    try:
        config_path = project_root / 'config' / 'roi_config.json'
        if not config_path.exists():
            logger.warning("Config file not found, skipping test")
            return True
        
        config = load_config(str(config_path))
        assert 'roi' in config
        assert 'counting_line' in config
        logger.info("✓ Config loaded successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Config test failed: {e}")
        return False

def test_database():
    """Test database initialization"""
    logger.info("Testing database...")
    try:
        db_path = project_root / 'data' / 'database' / 'test.db'
        create_directories(str(db_path.parent))
        
        from storage import initialize_database
        initialize_database(str(db_path))
        
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        assert 'counting_results' in tables
        assert 'camera_shifts' in tables
        logger.info("✓ Database initialized successfully")
        
        # Cleanup
        if db_path.exists():
            os.remove(str(db_path))
        
        return True
    except Exception as e:
        logger.error(f"✗ Database test failed: {e}")
        return False

def test_vehicle_detector():
    """Test vehicle detector initialization"""
    logger.info("Testing vehicle detector...")
    try:
        from vehicle_detection import VehicleDetector
        detector = VehicleDetector(model_path='yolov8n.pt')
        logger.info("✓ Vehicle detector initialized")
        return True
    except Exception as e:
        logger.error(f"✗ Vehicle detector test failed: {e}")
        logger.warning("This might fail if YOLO model is not downloaded yet")
        return False

def test_roi_processing():
    """Test ROI processing với image mẫu"""
    logger.info("Testing ROI processing...")
    try:
        from roi_processing import apply_roi_mask
        from utils import load_config
        
        # Tạo image test
        test_image = cv2.zeros((480, 640, 3), dtype=cv2.uint8)
        test_image[:] = (255, 255, 255)  # White image
        
        # Load config
        config_path = project_root / 'config' / 'roi_config.json'
        if config_path.exists():
            config = load_config(str(config_path))
            masked = apply_roi_mask(test_image, config['roi'])
            logger.info("✓ ROI processing successful")
            return True
        else:
            logger.warning("Config not found, skipping ROI test")
            return True
    except Exception as e:
        logger.error(f"✗ ROI processing test failed: {e}")
        return False

def test_tracking():
    """Test vehicle tracking"""
    logger.info("Testing vehicle tracking...")
    try:
        from vehicle_tracking import VehicleTracker
        
        tracker = VehicleTracker()
        
        # Mock detections
        detections = [
            {'bbox': [100, 100, 200, 200], 'confidence': 0.9, 'class': 'car'},
            {'bbox': [300, 300, 400, 400], 'confidence': 0.8, 'class': 'truck'}
        ]
        
        tracked = tracker.update(detections)
        assert len(tracked) == 2
        logger.info("✓ Vehicle tracking successful")
        return True
    except Exception as e:
        logger.error(f"✗ Vehicle tracking test failed: {e}")
        return False

def test_counting():
    """Test counting logic"""
    logger.info("Testing counting logic...")
    try:
        from counting import VehicleCounter
        from utils import load_config
        
        config_path = project_root / 'config' / 'roi_config.json'
        if config_path.exists():
            config = load_config(str(config_path))
            counter = VehicleCounter(config['counting_line'])
            logger.info("✓ Counting logic initialized")
            return True
        else:
            logger.warning("Config not found, skipping counting test")
            return True
    except Exception as e:
        logger.error(f"✗ Counting test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("=" * 50)
    logger.info("System K Vehicle Counting Tool - Test Suite")
    logger.info("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Config", test_config),
        ("Database", test_database),
        ("Vehicle Detector", test_vehicle_detector),
        ("ROI Processing", test_roi_processing),
        ("Tracking", test_tracking),
        ("Counting", test_counting),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info("")
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    logger.info("")
    logger.info("=" * 50)
    logger.info("Test Summary")
    logger.info("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info("")
    logger.info(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("All tests passed! ✓")
        return 0
    else:
        logger.warning(f"{total - passed} test(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())


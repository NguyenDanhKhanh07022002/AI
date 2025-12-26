"""
YOLO Loader với timeout và error handling
"""
import sys
import signal
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_yolo_with_timeout(timeout_seconds=30):
    """
    Load YOLO modules với timeout
    
    Returns:
        tuple: (detector, tracker, counter_class) hoặc (None, None, None) nếu fail
    """
    def timeout_handler(signum, frame):
        raise TimeoutError("YOLO import timeout")
    
    # Set timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    
    try:
        logger.info("Starting YOLO import...")
        
        # Import từng module một
        logger.info("Importing vehicle_detection...")
        from vehicle_detection import VehicleDetector
        logger.info("✓ vehicle_detection imported")
        
        logger.info("Importing vehicle_tracking...")
        from vehicle_tracking import VehicleTracker
        logger.info("✓ vehicle_tracking imported")
        
        logger.info("Importing counting...")
        from counting import VehicleCounter
        logger.info("✓ counting imported")
        
        # Cancel timeout
        signal.alarm(0)
        
        return VehicleDetector, VehicleTracker, VehicleCounter
        
    except TimeoutError:
        signal.alarm(0)
        logger.error("YOLO import timeout - có thể do Bus error")
        return None, None, None
    except (SystemError, OSError, RuntimeError, MemoryError) as e:
        signal.alarm(0)
        logger.error(f"System error importing YOLO: {type(e).__name__} - {str(e)}")
        return None, None, None
    except Exception as e:
        signal.alarm(0)
        logger.error(f"Error importing YOLO: {type(e).__name__} - {str(e)}", exc_info=True)
        return None, None, None
    finally:
        signal.alarm(0)  # Đảm bảo cancel timeout


def create_detector_safe(model_path='yolov8n.pt', conf_threshold=0.25, timeout=30):
    """
    Tạo VehicleDetector an toàn với timeout
    
    Returns:
        VehicleDetector hoặc None
    """
    def timeout_handler(signum, frame):
        raise TimeoutError("YOLO initialization timeout")
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    
    try:
        logger.info("Creating VehicleDetector...")
        from vehicle_detection import VehicleDetector
        detector = VehicleDetector(model_path=model_path, conf_threshold=conf_threshold)
        logger.info("✓ VehicleDetector created")
        signal.alarm(0)
        return detector
    except TimeoutError:
        signal.alarm(0)
        logger.error("VehicleDetector creation timeout")
        return None
    except (SystemError, OSError, RuntimeError, MemoryError) as e:
        signal.alarm(0)
        logger.error(f"System error creating detector: {type(e).__name__} - {str(e)}")
        return None
    except Exception as e:
        signal.alarm(0)
        logger.error(f"Error creating detector: {type(e).__name__} - {str(e)}", exc_info=True)
        return None
    finally:
        signal.alarm(0)


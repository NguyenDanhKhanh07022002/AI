"""
Module 6: Vehicle Detection
Phát hiện xe sử dụng YOLOv8
"""
import cv2
import numpy as np
import logging
from ultralytics import YOLO
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# COCO class IDs cho vehicles
VEHICLE_CLASSES = {
    2: 'car',
    3: 'motorcycle',
    5: 'bus',
    7: 'truck'
}


class VehicleDetector:
    """Vehicle detector sử dụng YOLOv8"""
    
    def __init__(self, model_path: str = 'yolov8n.pt', conf_threshold: float = 0.25):
        """
        Khởi tạo vehicle detector
        
        Args:
            model_path: Đường dẫn đến YOLO model (hoặc tên model từ ultralytics)
            conf_threshold: Confidence threshold
        """
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        logger.info(f"Vehicle detector initialized with model: {model_path}")
    
    def detect_vehicles(self, image: np.ndarray, vehicle_classes: Optional[List[str]] = None) -> List[Dict]:
        """
        Phát hiện xe trong ảnh
        
        Args:
            image: Image array (numpy)
            vehicle_classes: List các class cần detect (None = tất cả vehicle classes)
        
        Returns:
            List[Dict]: List detections với format:
                {
                    'bbox': [x1, y1, x2, y2],
                    'confidence': float,
                    'class': str,
                    'class_id': int
                }
        """
        if image is None or image.size == 0:
            logger.warning("Invalid image input")
            return []
        
        # Run YOLO inference
        results = self.model(image, conf=self.conf_threshold, verbose=False)
        
        detections = []
        
        if len(results) > 0:
            result = results[0]
            
            # Lấy boxes, scores, class_ids
            boxes = result.boxes
            
            for i in range(len(boxes)):
                box = boxes[i]
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                
                # Chỉ lấy vehicle classes
                if class_id in VEHICLE_CLASSES:
                    class_name = VEHICLE_CLASSES[class_id]
                    
                    # Filter theo vehicle_classes nếu được chỉ định
                    if vehicle_classes is not None and class_name not in vehicle_classes:
                        continue
                    
                    # Lấy bounding box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    
                    detection = {
                        'bbox': [float(x1), float(y1), float(x2), float(y2)],
                        'confidence': confidence,
                        'class': class_name,
                        'class_id': class_id
                    }
                    detections.append(detection)
        
        logger.debug(f"Detected {len(detections)} vehicles")
        return detections
    
    def detect_vehicles_batch(self, images: List[np.ndarray], vehicle_classes: Optional[List[str]] = None) -> List[List[Dict]]:
        """
        Phát hiện xe trong batch images
        
        Args:
            images: List các image arrays
            vehicle_classes: List các class cần detect
        
        Returns:
            List[List[Dict]]: List detections cho mỗi image
        """
        all_detections = []
        for image in images:
            detections = self.detect_vehicles(image, vehicle_classes)
            all_detections.append(detections)
        return all_detections


def detect_vehicles(image: np.ndarray, model_path: str = 'yolov8n.pt', vehicle_classes: Optional[List[str]] = None) -> List[Dict]:
    """
    Convenience function để detect vehicles
    
    Args:
        image: Image array
        model_path: Đường dẫn đến YOLO model
        vehicle_classes: List các class cần detect
    
    Returns:
        List[Dict]: List detections
    """
    detector = VehicleDetector(model_path)
    return detector.detect_vehicles(image, vehicle_classes)


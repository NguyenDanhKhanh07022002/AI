"""
Module 7: Vehicle Tracking
Theo dõi xe qua các frames sử dụng ByteTrack
"""
import cv2
import numpy as np
import logging
from typing import List, Dict, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class VehicleTracker:
    """Vehicle tracker sử dụng simple tracking algorithm (có thể tích hợp ByteTrack sau)"""
    
    def __init__(self, max_disappeared: int = 5, max_distance: float = 50.0):
        """
        Khởi tạo tracker
        
        Args:
            max_disappeared: Số frame tối đa một object có thể mất trước khi remove
            max_distance: Khoảng cách tối đa để match object giữa các frames
        """
        self.next_id = 0
        self.objects = {}  # {track_id: {'bbox': [...], 'centroid': (x, y), 'disappeared': 0}}
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance
        logger.info("Vehicle tracker initialized")
    
    def _calculate_centroid(self, bbox: List[float]) -> tuple:
        """Tính centroid từ bounding box"""
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        return (cx, cy)
    
    def _calculate_distance(self, centroid1: tuple, centroid2: tuple) -> float:
        """Tính khoảng cách Euclidean giữa 2 centroids"""
        return np.sqrt((centroid1[0] - centroid2[0])**2 + (centroid1[1] - centroid2[1])**2)
    
    def update(self, detections: List[Dict]) -> List[Dict]:
        """
        Update tracker với detections mới
        
        Args:
            detections: List detections từ vehicle_detection module
        
        Returns:
            List[Dict]: Tracked objects với track_id
        """
        if len(detections) == 0:
            # Tăng disappeared count cho tất cả objects
            for track_id in list(self.objects.keys()):
                self.objects[track_id]['disappeared'] += 1
                if self.objects[track_id]['disappeared'] > self.max_disappeared:
                    del self.objects[track_id]
                    logger.debug(f"Removed track {track_id}")
            return []
        
        # Nếu chưa có objects, tạo mới cho tất cả detections
        if len(self.objects) == 0:
            for detection in detections:
                track_id = self.next_id
                self.next_id += 1
                centroid = self._calculate_centroid(detection['bbox'])
                self.objects[track_id] = {
                    'bbox': detection['bbox'],
                    'centroid': centroid,
                    'disappeared': 0,
                    'class': detection.get('class', 'unknown'),
                    'confidence': detection.get('confidence', 0.0)
                }
        else:
            # Match detections với existing objects
            input_centroids = [self._calculate_centroid(d['bbox']) for d in detections]
            object_centroids = {tid: obj['centroid'] for tid, obj in self.objects.items()}
            
            # Tính distance matrix
            distance_matrix = {}
            for i, input_centroid in enumerate(input_centroids):
                for tid, obj_centroid in object_centroids.items():
                    distance = self._calculate_distance(input_centroid, obj_centroid)
                    distance_matrix[(i, tid)] = distance
            
            # Greedy matching: match closest pairs
            used_detections = set()
            used_tracks = set()
            
            # Sort by distance
            sorted_pairs = sorted(distance_matrix.items(), key=lambda x: x[1])
            
            for (det_idx, track_id), distance in sorted_pairs:
                if det_idx in used_detections or track_id in used_tracks:
                    continue
                
                if distance <= self.max_distance:
                    # Match found
                    detection = detections[det_idx]
                    centroid = input_centroids[det_idx]
                    
                    self.objects[track_id]['bbox'] = detection['bbox']
                    self.objects[track_id]['centroid'] = centroid
                    self.objects[track_id]['disappeared'] = 0
                    self.objects[track_id]['class'] = detection.get('class', 'unknown')
                    self.objects[track_id]['confidence'] = detection.get('confidence', 0.0)
                    
                    used_detections.add(det_idx)
                    used_tracks.add(track_id)
            
            # Tạo mới cho detections không match
            for i, detection in enumerate(detections):
                if i not in used_detections:
                    track_id = self.next_id
                    self.next_id += 1
                    centroid = self._calculate_centroid(detection['bbox'])
                    self.objects[track_id] = {
                        'bbox': detection['bbox'],
                        'centroid': centroid,
                        'disappeared': 0,
                        'class': detection.get('class', 'unknown'),
                        'confidence': detection.get('confidence', 0.0)
                    }
            
            # Tăng disappeared count cho objects không match
            for track_id in list(self.objects.keys()):
                if track_id not in used_tracks:
                    self.objects[track_id]['disappeared'] += 1
                    if self.objects[track_id]['disappeared'] > self.max_disappeared:
                        del self.objects[track_id]
                        logger.debug(f"Removed track {track_id}")
        
        # Trả về tracked objects
        tracked_objects = []
        for track_id, obj in self.objects.items():
            if obj['disappeared'] == 0:  # Chỉ trả về objects đang active
                tracked_obj = {
                    'track_id': track_id,
                    'bbox': obj['bbox'],
                    'centroid': obj['centroid'],
                    'class': obj['class'],
                    'confidence': obj['confidence']
                }
                tracked_objects.append(tracked_obj)
        
        return tracked_objects


def track_vehicles(detections: List[Dict], previous_tracks: Optional[Dict] = None) -> List[Dict]:
    """
    Convenience function để track vehicles
    
    Args:
        detections: List detections từ vehicle_detection
        previous_tracks: Tracker state từ frame trước (optional)
    
    Returns:
        List[Dict]: Tracked objects với track_id
    """
    if previous_tracks is None:
        tracker = VehicleTracker()
    else:
        tracker = previous_tracks
    
    tracked_objects = tracker.update(detections)
    return tracked_objects, tracker


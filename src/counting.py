"""
Module 8: Vehicle Counting
Logic đếm xe qua counting line/zone
"""
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class VehicleCounter:
    """Vehicle counter với counting line"""
    
    def __init__(self, counting_line: Dict):
        """
        Khởi tạo counter
        
        Args:
            counting_line: Config dictionary chứa counting line settings
                {
                    'type': 'line',
                    'start': [x1, y1],
                    'end': [x2, y2],
                    'direction': 'horizontal' or 'vertical'
                }
        """
        self.counting_line = counting_line
        self.start_point = tuple(counting_line['start'])
        self.end_point = tuple(counting_line['end'])
        self.direction = counting_line.get('direction', 'horizontal')
        
        # Tracking vehicles đã đếm để tránh đếm trùng
        self.counted_vehicles = set()  # Set of track_ids đã đếm
        
        # Counters
        self.count_up = 0  # Chiều lên (hoặc trái/phải tùy direction)
        self.count_down = 0  # Chiều xuống (hoặc phải/trái tùy direction)
        
        logger.info(f"Vehicle counter initialized with line: {self.start_point} -> {self.end_point}")
    
    def _point_to_line_distance(self, point: Tuple[float, float], line_start: Tuple[float, float], line_end: Tuple[float, float]) -> float:
        """Tính khoảng cách từ điểm đến đường thẳng"""
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end
        
        # Vector từ line_start đến line_end
        dx = x2 - x1
        dy = y2 - y1
        
        # Vector từ line_start đến point
        dx0 = x0 - x1
        dy0 = y0 - y1
        
        # Tính distance
        if dx == 0 and dy == 0:
            # Line là một điểm
            return np.sqrt((x0 - x1)**2 + (y0 - y1)**2)
        
        # Projection
        t = (dx0 * dx + dy0 * dy) / (dx * dx + dy * dy)
        t = max(0, min(1, t))  # Clamp to [0, 1]
        
        # Closest point on line
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        
        # Distance
        distance = np.sqrt((x0 - proj_x)**2 + (y0 - proj_y)**2)
        return distance
    
    def _is_crossing_line(self, prev_centroid: Tuple[float, float], curr_centroid: Tuple[float, float]) -> Optional[str]:
        """
        Kiểm tra xe có vượt qua counting line không
        
        Args:
            prev_centroid: Centroid ở frame trước
            curr_centroid: Centroid ở frame hiện tại
        
        Returns:
            'up' hoặc 'down' nếu vượt qua, None nếu không
        """
        # Kiểm tra cả 2 điểm có ở 2 phía của line không
        prev_dist = self._point_to_line_distance(prev_centroid, self.start_point, self.end_point)
        curr_dist = self._point_to_line_distance(curr_centroid, self.start_point, self.end_point)
        
        # Nếu một điểm gần line (trong threshold) và điểm kia xa hơn, có thể đã vượt qua
        threshold = 10.0  # pixels
        
        if prev_dist < threshold and curr_dist < threshold:
            # Cả 2 đều gần line, kiểm tra xem có vượt qua không
            # Tính side của mỗi điểm so với line
            prev_side = self._get_side_of_line(prev_centroid)
            curr_side = self._get_side_of_line(curr_centroid)
            
            if prev_side != curr_side:
                # Đã vượt qua line
                if self.direction == 'horizontal':
                    # Up = từ dưới lên (y giảm), Down = từ trên xuống (y tăng)
                    if prev_centroid[1] > curr_centroid[1]:
                        return 'up'
                    else:
                        return 'down'
                else:  # vertical
                    # Up = từ phải sang trái (x giảm), Down = từ trái sang phải (x tăng)
                    if prev_centroid[0] > curr_centroid[0]:
                        return 'up'
                    else:
                        return 'down'
        
        return None
    
    def _get_side_of_line(self, point: Tuple[float, float]) -> int:
        """Xác định điểm ở phía nào của line (1 hoặc -1)"""
        x, y = point
        x1, y1 = self.start_point
        x2, y2 = self.end_point
        
        # Vector từ start đến end
        dx = x2 - x1
        dy = y2 - y1
        
        # Vector từ start đến point
        dx0 = x - x1
        dy0 = y - y1
        
        # Cross product để xác định side
        cross = dx * dy0 - dy * dx0
        return 1 if cross > 0 else -1
    
    def count_vehicles(
        self,
        tracked_objects: List[Dict],
        previous_centroids: Dict[int, Tuple[float, float]]
    ) -> Dict:
        """
        Đếm xe từ tracked objects
        
        Args:
            tracked_objects: List tracked objects với track_id và centroid
            previous_centroids: Dict {track_id: centroid} từ frame trước
        
        Returns:
            Dict: {
                'count_up': int,
                'count_down': int,
                'total': int,
                'new_counts': List[Dict]  # List vehicles mới đếm được
            }
        """
        new_counts = []
        
        for obj in tracked_objects:
            track_id = obj['track_id']
            curr_centroid = obj['centroid']
            
            # Nếu đã đếm rồi thì skip
            if track_id in self.counted_vehicles:
                continue
            
            # Kiểm tra có centroid ở frame trước không
            if track_id in previous_centroids:
                prev_centroid = previous_centroids[track_id]
                direction = self._is_crossing_line(prev_centroid, curr_centroid)
                
                if direction:
                    # Đã vượt qua line
                    self.counted_vehicles.add(track_id)
                    
                    if direction == 'up':
                        self.count_up += 1
                    else:
                        self.count_down += 1
                    
                    new_counts.append({
                        'track_id': track_id,
                        'direction': direction,
                        'class': obj.get('class', 'unknown')
                    })
                    
                    logger.info(f"Vehicle {track_id} ({obj.get('class', 'unknown')}) crossed line: {direction}")
        
        return {
            'count_up': self.count_up,
            'count_down': self.count_down,
            'total': self.count_up + self.count_down,
            'new_counts': new_counts
        }
    
    def reset(self):
        """Reset counters"""
        self.count_up = 0
        self.count_down = 0
        self.counted_vehicles.clear()
        logger.info("Vehicle counter reset")


def count_vehicles(
    tracked_objects: List[Dict],
    counting_line: Dict,
    previous_centroids: Optional[Dict[int, Tuple[float, float]]] = None,
    counter: Optional[VehicleCounter] = None
) -> Tuple[Dict, VehicleCounter]:
    """
    Convenience function để đếm xe
    
    Args:
        tracked_objects: List tracked objects
        counting_line: Counting line config
        previous_centroids: Centroids từ frame trước
        counter: VehicleCounter instance (nếu None sẽ tạo mới)
    
    Returns:
        Tuple[Dict, VehicleCounter]: (counting result, counter instance)
    """
    if counter is None:
        counter = VehicleCounter(counting_line)
    
    if previous_centroids is None:
        previous_centroids = {}
    
    result = counter.count_vehicles(tracked_objects, previous_centroids)
    return result, counter


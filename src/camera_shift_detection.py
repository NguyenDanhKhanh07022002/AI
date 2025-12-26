"""
Module 5: Camera Shift Detection
Kiểm tra camera có bị lệch không
"""
import cv2
import numpy as np
import logging
import os
from pathlib import Path
from typing import Optional, Tuple, Dict

logger = logging.getLogger(__name__)


def detect_camera_shift(
    current_frame: np.ndarray,
    reference_frame: np.ndarray,
    threshold: float = 0.1
) -> Dict:
    """
    Phát hiện camera bị lệch bằng feature matching
    
    Args:
        current_frame: Frame hiện tại
        reference_frame: Frame tham chiếu
        threshold: Ngưỡng để coi là lệch (0.0 - 1.0)
    
    Returns:
        Dict: {
            'shift_x': float,
            'shift_y': float,
            'rotation': float,
            'is_shifted': bool,
            'match_count': int
        }
    """
    if current_frame is None or reference_frame is None:
        return {
            'shift_x': 0.0,
            'shift_y': 0.0,
            'rotation': 0.0,
            'is_shifted': False,
            'match_count': 0
        }
    
    # Convert to grayscale nếu cần
    if len(current_frame.shape) == 3:
        current_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
    else:
        current_gray = current_frame
    
    if len(reference_frame.shape) == 3:
        ref_gray = cv2.cvtColor(reference_frame, cv2.COLOR_BGR2GRAY)
    else:
        ref_gray = reference_frame
    
    # Sử dụng ORB detector (nhanh hơn SIFT)
    orb = cv2.ORB_create(nfeatures=1000)
    
    # Detect keypoints và descriptors
    kp1, des1 = orb.detectAndCompute(current_gray, None)
    kp2, des2 = orb.detectAndCompute(ref_gray, None)
    
    if des1 is None or des2 is None or len(des1) < 4 or len(des2) < 4:
        logger.warning("Not enough features detected")
        return {
            'shift_x': 0.0,
            'shift_y': 0.0,
            'rotation': 0.0,
            'is_shifted': False,
            'match_count': 0
        }
    
    # Match features
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(des1, des2, k=2)
    
    # Apply ratio test
    good_matches = []
    for match_pair in matches:
        if len(match_pair) == 2:
            m, n = match_pair
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)
    
    if len(good_matches) < 4:
        logger.warning("Not enough good matches")
        return {
            'shift_x': 0.0,
            'shift_y': 0.0,
            'rotation': 0.0,
            'is_shifted': False,
            'match_count': len(good_matches)
        }
    
    # Lấy điểm tương ứng
    src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    
    # Tính homography matrix
    homography, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    
    if homography is None:
        logger.warning("Could not compute homography")
        return {
            'shift_x': 0.0,
            'shift_y': 0.0,
            'rotation': 0.0,
            'is_shifted': False,
            'match_count': len(good_matches)
        }
    
    # Tính shift và rotation từ homography
    # Homography matrix: [[a, b, tx], [c, d, ty], [e, f, 1]]
    shift_x = homography[0, 2]
    shift_y = homography[1, 2]
    
    # Tính rotation từ scale và rotation components
    a, b = homography[0, 0], homography[0, 1]
    rotation = np.arctan2(b, a) * 180 / np.pi
    
    # Normalize shift theo kích thước frame
    h, w = current_gray.shape[:2]
    normalized_shift_x = abs(shift_x) / w
    normalized_shift_y = abs(shift_y) / h
    
    # Kiểm tra có lệch không
    max_shift = max(normalized_shift_x, normalized_shift_y)
    is_shifted = max_shift > threshold or abs(rotation) > 5.0  # 5 độ
    
    result = {
        'shift_x': shift_x,
        'shift_y': shift_y,
        'rotation': rotation,
        'is_shifted': is_shifted,
        'match_count': len(good_matches),
        'normalized_shift_x': normalized_shift_x,
        'normalized_shift_y': normalized_shift_y
    }
    
    if is_shifted:
        logger.warning(
            f"Camera shift detected: shift_x={shift_x:.2f}, shift_y={shift_y:.2f}, "
            f"rotation={rotation:.2f}°"
        )
    
    return result


def save_reference_frame(frame: np.ndarray, output_path: str):
    """
    Lưu frame làm reference frame
    
    Args:
        frame: Frame để lưu
        output_path: Đường dẫn lưu file
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(output_path, frame)
    logger.info(f"Saved reference frame: {output_path}")


def load_reference_frame(reference_path: str) -> Optional[np.ndarray]:
    """
    Load reference frame từ file
    
    Args:
        reference_path: Đường dẫn đến reference frame
    
    Returns:
        np.ndarray: Reference frame hoặc None nếu không tìm thấy
    """
    if not os.path.exists(reference_path):
        logger.warning(f"Reference frame not found: {reference_path}")
        return None
    
    frame = cv2.imread(reference_path)
    if frame is None:
        logger.error(f"Could not load reference frame: {reference_path}")
    
    return frame


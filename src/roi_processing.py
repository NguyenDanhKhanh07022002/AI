"""
Module 3: ROI Processing
Bôi đen phần thừa (ROI masking)
"""
import cv2
import numpy as np
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


def apply_roi_mask(image: np.ndarray, roi_config: Dict) -> np.ndarray:
    """
    Áp dụng ROI mask để bôi đen phần thừa
    
    Args:
        image: Image array (numpy)
        roi_config: Config dictionary chứa ROI settings
    
    Returns:
        np.ndarray: Image đã được mask
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid image input")
    
    masked_image = image.copy()
    roi_type = roi_config.get('type', 'polygon')
    mask_color = roi_config.get('mask_color', [0, 0, 0])
    
    # Tạo mask để giữ lại vùng ROI (phần không bị bôi đen)
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    
    if roi_type == 'polygon':
        points = roi_config.get('points', [])
        if len(points) < 3:
            logger.warning("Polygon ROI needs at least 3 points")
            return masked_image
        
        # Convert points to numpy array và đảm bảo là integer
        # Loại bỏ điểm trùng lặp
        unique_points = []
        seen = set()
        for p in points:
            point_tuple = (int(round(p[0])), int(round(p[1])))
            if point_tuple not in seen:
                unique_points.append(point_tuple)
                seen.add(point_tuple)
        
        if len(unique_points) < 3:
            logger.warning(f"After removing duplicates, only {len(unique_points)} unique points, need at least 3")
            return masked_image
        
        pts = np.array(unique_points, dtype=np.int32)
        
        # Đảm bảo points nằm trong bounds của ảnh
        h, w = image.shape[:2]
        pts[:, 0] = np.clip(pts[:, 0], 0, w - 1)  # x coordinates
        pts[:, 1] = np.clip(pts[:, 1], 0, h - 1)  # y coordinates
        
        # Fill polygon trong mask (vùng này sẽ được giữ lại)
        cv2.fillPoly(mask, [pts], 255)
        logger.debug(f"ROI polygon: {len(unique_points)} points, image size: {w}x{h}")
        
    elif roi_type == 'rectangle':
        if 'x' in roi_config and 'y' in roi_config and 'width' in roi_config and 'height' in roi_config:
            x = roi_config['x']
            y = roi_config['y']
            w = roi_config['width']
            h = roi_config['height']
            cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)
        else:
            logger.warning("Rectangle ROI needs x, y, width, height")
            return masked_image
    else:
        logger.warning(f"Unknown ROI type: {roi_type}")
        return masked_image
    
    # Invert mask: vùng ngoài ROI sẽ được bôi đen
    mask_inv = cv2.bitwise_not(mask)
    
    # Áp dụng mask: bôi đen phần ngoài ROI
    for c in range(image.shape[2]):
        masked_image[:, :, c] = np.where(
            mask_inv > 0,
            mask_color[c] if len(mask_color) > c else 0,
            masked_image[:, :, c]
        )
    
    logger.debug(f"Applied ROI mask (type: {roi_type})")
    return masked_image


def create_roi_mask(image_shape: Tuple[int, int], roi_config: Dict) -> np.ndarray:
    """
    Tạo mask cho ROI (helper function)
    
    Args:
        image_shape: Shape của image (height, width)
        roi_config: Config dictionary chứa ROI settings
    
    Returns:
        np.ndarray: Binary mask (255 = keep, 0 = mask out)
    """
    mask = np.zeros(image_shape, dtype=np.uint8)
    roi_type = roi_config.get('type', 'polygon')
    
    if roi_type == 'polygon':
        points = roi_config.get('points', [])
        if len(points) >= 3:
            pts = np.array(points, dtype=np.int32)
            cv2.fillPoly(mask, [pts], 255)
    elif roi_type == 'rectangle':
        if 'x' in roi_config and 'y' in roi_config and 'width' in roi_config and 'height' in roi_config:
            x = roi_config['x']
            y = roi_config['y']
            w = roi_config['width']
            h = roi_config['height']
            cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)
    
    return mask


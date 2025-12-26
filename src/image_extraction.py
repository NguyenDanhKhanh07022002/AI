"""
Module 2: Image Extraction
Chuyển video ngắn thành frames (ảnh)
"""
import cv2
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def extract_frames(video_path: str, output_dir: str, fps: Optional[float] = None) -> list:
    """
    Extract frames từ video
    
    Args:
        video_path: Đường dẫn đến video
        output_dir: Thư mục lưu frames
        fps: FPS để extract (None = extract tất cả frames)
    
    Returns:
        list: Danh sách đường dẫn các frames đã extract
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    # Tạo output directory nếu chưa tồn tại
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    video_name = Path(video_path).stem
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    logger.info(f"Extracting frames from: {video_path}")
    logger.info(f"Video FPS: {video_fps}, Total frames: {total_frames}")
    
    # Tính frame interval nếu chỉ định fps
    frame_interval = 1
    if fps is not None and fps > 0:
        frame_interval = max(1, int(video_fps / fps))
        logger.info(f"Extracting at {fps} FPS (every {frame_interval} frames)")
    
    frame_paths = []
    frame_count = 0
    saved_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Chỉ lưu frame nếu đúng interval
            if frame_count % frame_interval == 0:
                frame_filename = f"{video_name}_frame_{saved_count:06d}.jpg"
                frame_path = os.path.join(output_dir, frame_filename)
                
                cv2.imwrite(frame_path, frame)
                frame_paths.append(frame_path)
                saved_count += 1
            
            frame_count += 1
        
        logger.info(f"Extracted {saved_count} frames to {output_dir}")
        
    finally:
        cap.release()
    
    return frame_paths


def extract_frames_by_time_interval(video_path: str, output_dir: str, time_interval_seconds: float = 300.0) -> list:
    """
    Extract frames từ video theo khoảng thời gian (ví dụ: mỗi 5 phút = 300 giây)
    
    Args:
        video_path: Đường dẫn đến video
        output_dir: Thư mục lưu frames
        time_interval_seconds: Khoảng thời gian giữa các frame (giây), mặc định 300s (5 phút)
    
    Returns:
        list: Danh sách đường dẫn các frames đã extract
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    # Tạo output directory nếu chưa tồn tại
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Kiểm tra file có tồn tại không
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    # Kiểm tra file size (file rỗng hoặc bị lỗi)
    file_size = os.path.getsize(video_path)
    if file_size == 0:
        raise RuntimeError(f"Video file is empty: {video_path}")
    
    video_name = Path(video_path).stem
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}. File may be corrupted or format not supported.")
    
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_seconds = total_frames / video_fps if video_fps > 0 else 0
    
    logger.info(f"Extracting frames by time interval from: {video_path}")
    logger.info(f"Video FPS: {video_fps}, Total frames: {total_frames}, Duration: {duration_seconds:.2f}s")
    logger.info(f"Time interval: {time_interval_seconds} seconds")
    
    # Tính frame interval dựa trên time interval
    frame_interval = max(1, int(video_fps * time_interval_seconds))
    
    frame_paths = []
    frame_count = 0
    saved_count = 0
    last_saved_time = 0.0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            current_time = frame_count / video_fps if video_fps > 0 else 0
            
            # Lưu frame nếu đã đủ thời gian
            if current_time - last_saved_time >= time_interval_seconds:
                frame_filename = f"{video_name}_time_{int(current_time):06d}s_frame_{saved_count:06d}.jpg"
                frame_path = os.path.join(output_dir, frame_filename)
                
                cv2.imwrite(frame_path, frame)
                frame_paths.append(frame_path)
                saved_count += 1
                last_saved_time = current_time
                
                logger.debug(f"Saved frame at {current_time:.2f}s: {frame_filename}")
            
            frame_count += 1
        
        logger.info(f"Extracted {saved_count} frames (every {time_interval_seconds}s) to {output_dir}")
        
    finally:
        cap.release()
    
    return frame_paths


def extract_all_frames(video_path: str, output_dir: str) -> list:
    """
    Extract tất cả frames từ video (wrapper function)
    
    Args:
        video_path: Đường dẫn đến video
        output_dir: Thư mục lưu frames
    
    Returns:
        list: Danh sách đường dẫn các frames
    """
    return extract_frames(video_path, output_dir, fps=None)


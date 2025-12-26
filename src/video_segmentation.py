"""
Module 1: Video Segmentation
Cắt video dài thành video ngắn sử dụng FFmpeg
"""
import os
import subprocess
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def segment_video(
    input_path: str, 
    output_dir: str, 
    segment_duration: int = 300,
    start_time: float = 300.0
) -> List[str]:
    """
    Cắt video dài thành các video ngắn theo thời gian
    
    Args:
        input_path: Đường dẫn đến video input
        output_dir: Thư mục lưu video đã cắt
        segment_duration: Độ dài mỗi segment (giây), mặc định 300s (5 phút)
    
    Returns:
        List[str]: Danh sách đường dẫn các video đã cắt
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Video file not found: {input_path}")
    
    # Tạo output directory nếu chưa tồn tại
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    video_name = Path(input_path).stem
    output_pattern = os.path.join(output_dir, f"{video_name}_segment_%03d.mp4")
    
    logger.info(f"Segmenting video: {input_path}")
    logger.info(f"Segment duration: {segment_duration} seconds")
    if start_time > 0:
        logger.info(f"Start time: {start_time} seconds (from {start_time/60:.1f} minutes)")
    
    # FFmpeg command để cắt video
    cmd = ['ffmpeg', '-i', input_path]
    
    # Nếu có start_time, thêm -ss (luôn cắt từ 5 phút trở đi theo yêu cầu)
    if start_time > 0:
        hours = int(start_time // 3600)
        minutes = int((start_time % 3600) // 60)
        seconds = int(start_time % 60)
        cmd.extend(['-ss', f"{hours:02d}:{minutes:02d}:{seconds:02d}"])
    
    cmd.extend([
        '-c', 'copy',  # Copy codec để nhanh hơn
        '-f', 'segment',
        '-segment_time', str(segment_duration),
        '-reset_timestamps', '1',
        '-segment_format', 'mp4',
        output_pattern
    ])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("Video segmentation completed successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr}")
        raise RuntimeError(f"Failed to segment video: {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError("FFmpeg not found. Please install FFmpeg first.")
    
    # Tìm tất cả các file segment đã tạo
    segment_files = []
    segment_pattern = os.path.join(output_dir, f"{video_name}_segment_*.mp4")
    
    import glob
    import time
    segment_files = sorted(glob.glob(segment_pattern))
    
    # Kiểm tra các file có tồn tại và có kích thước > 0
    valid_segments = []
    for seg_file in segment_files:
        if os.path.exists(seg_file) and os.path.getsize(seg_file) > 0:
            valid_segments.append(seg_file)
        else:
            logger.warning(f"Invalid segment file (missing or empty): {seg_file}")
    
    if not valid_segments:
        logger.warning("No valid video segments created. This may happen if:")
        logger.warning("  - Video is shorter than start_time (5 minutes)")
        logger.warning("  - FFmpeg segmentation failed silently")
        logger.warning("  - Output directory permissions issue")
    
    logger.info(f"Created {len(valid_segments)} valid video segments (out of {len(segment_files)} found)")
    return valid_segments


def get_video_duration(video_path: str) -> float:
    """
    Lấy độ dài video (giây) sử dụng FFprobe
    
    Args:
        video_path: Đường dẫn đến video
    
    Returns:
        float: Độ dài video (giây)
    """
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return duration
    except (subprocess.CalledProcessError, ValueError) as e:
        logger.warning(f"Could not get video duration: {e}")
        return 0.0


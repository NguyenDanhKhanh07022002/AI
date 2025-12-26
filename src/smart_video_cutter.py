"""
Smart Video Cutter
Cắt video thông minh dựa trên memo (duplicate segments và camera shifts)
"""
import os
import subprocess
import logging
from pathlib import Path
from typing import List, Tuple
from video_segmentation import get_video_duration
from memo_system import generate_cut_plan, get_duplicate_segments, get_camera_shift_points

logger = logging.getLogger(__name__)


def cut_video_segment(
    input_path: str,
    output_path: str,
    start_time: float,
    duration: float = None,
    end_time: float = None
) -> bool:
    """
    Cắt một đoạn video cụ thể
    
    Args:
        input_path: Đường dẫn video input
        output_path: Đường dẫn video output
        start_time: Thời gian bắt đầu (giây)
        duration: Độ dài đoạn (giây, nếu có)
        end_time: Thời gian kết thúc (giây, nếu có)
    
    Returns:
        bool: True nếu thành công
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Video file not found: {input_path}")
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Tính duration nếu có end_time
    if end_time is not None and duration is None:
        duration = end_time - start_time
    
    if duration is None or duration <= 0:
        logger.warning(f"Invalid duration for segment: start={start_time}, duration={duration}")
        return False
    
    # FFmpeg command: ffmpeg -i input.mkv -ss 00:00:00 -t 00:15:00 -c copy output.mkv
    cmd = [
        'ffmpeg',
        '-i', input_path,
        '-ss', f"{int(start_time // 60):02d}:{int(start_time % 60):02d}:{int((start_time % 1) * 100):02d}",
        '-t', f"{int(duration // 60):02d}:{int(duration % 60):02d}:{int((duration % 1) * 100):02d}",
        '-c', 'copy',  # Copy codec, không re-encode
        '-y',  # Overwrite output file
        output_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Cut video segment: {start_time:.2f}s - {start_time + duration:.2f}s -> {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error cutting segment: {e.stderr}")
        return False
    except FileNotFoundError:
        raise RuntimeError("FFmpeg not found. Please install FFmpeg first.")


def smart_cut_video(
    input_path: str,
    output_dir: str,
    db_path: str,
    min_start_time: float = 300.0,
    default_segment_duration: int = 900
) -> List[str]:
    """
    Cắt video thông minh dựa trên memo (duplicate và camera shifts)
    
    Args:
        input_path: Đường dẫn video input
        output_dir: Thư mục lưu video đã cắt
        db_path: Đường dẫn database chứa memo
        min_start_time: Thời gian bắt đầu tối thiểu (mặc định 300s = 5 phút)
        default_segment_duration: Độ dài mặc định mỗi segment nếu không có memo (giây)
    
    Returns:
        List[str]: Danh sách đường dẫn các video đã cắt
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Video file not found: {input_path}")
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Lấy độ dài video
    video_duration = get_video_duration(input_path)
    if video_duration <= 0:
        raise RuntimeError("Could not get video duration")
    
    logger.info(f"Smart cutting video: {input_path}")
    logger.info(f"Video duration: {video_duration:.2f} seconds")
    
    # Tạo kế hoạch cắt dựa trên memo
    cut_segments = generate_cut_plan(db_path, input_path, video_duration, min_start_time)
    
    if not cut_segments:
        # Nếu không có memo, cắt từ min_start_time với default duration
        logger.info("No memo found, using default cutting plan")
        segments = []
        current_time = min_start_time
        segment_idx = 0
        
        while current_time < video_duration:
            duration = min(default_segment_duration, video_duration - current_time)
            segments.append((current_time, duration))
            current_time += duration
            segment_idx += 1
        
        cut_segments = segments
    
    logger.info(f"Cutting plan: {len(cut_segments)} segments")
    for i, (start, duration) in enumerate(cut_segments):
        logger.info(f"  Segment {i+1}: {start:.2f}s - {start + duration:.2f}s ({duration:.2f}s)")
    
    # Cắt video theo kế hoạch
    video_name = Path(input_path).stem
    output_files = []
    
    for segment_idx, (start_time, duration) in enumerate(cut_segments):
        output_filename = f"{video_name}_part{segment_idx + 1:02d}.mkv"
        output_path = os.path.join(output_dir, output_filename)
        
        if cut_video_segment(input_path, output_path, start_time, duration=duration):
            output_files.append(output_path)
        else:
            logger.warning(f"Failed to cut segment {segment_idx + 1}")
    
    logger.info(f"Created {len(output_files)} video segments")
    return output_files


def cut_video_from_5min(input_path: str, output_path: str) -> bool:
    """
    Cắt video từ 5 phút trở đi (theo yêu cầu: luôn cắt từ 5 phút để tránh Python script error)
    
    Args:
        input_path: Đường dẫn video input
        output_path: Đường dẫn video output
    
    Returns:
        bool: True nếu thành công
    """
    return cut_video_segment(input_path, output_path, start_time=300.0)


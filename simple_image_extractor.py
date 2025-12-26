#!/usr/bin/env python3
"""
Simple Image Extractor
Tool đơn giản: Video → Extract frames → Apply ROI mask → Save images
Không có vehicle detection/counting
"""
import os
import sys
import cv2
import argparse
import logging
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from utils import setup_logging, load_config, create_directories, get_timestamp
from video_segmentation import segment_video, get_video_duration
from image_extraction import extract_frames_by_time_interval, extract_frames
from roi_processing import apply_roi_mask
from duplicate_detection import check_duplicate, save_image_hash, initialize_database as init_hash_db
from camera_shift_detection import detect_camera_shift, save_reference_frame, load_reference_frame
from memo_system import (
    initialize_memo_database, save_duplicate_memo, save_camera_shift_memo
)

logger = setup_logging(logging.INFO)


def process_video_simple(
    video_path: str,
    output_dir: str = 'extracted_images',
    time_interval: float = 300.0,
    config_path: str = 'config/roi_config.json',
    check_duplicate: bool = True,
    check_camera_shift: bool = True
):
    """
    Xử lý video đơn giản: Extract frames → Apply ROI mask → Save
    
    Args:
        video_path: Đường dẫn video
        output_dir: Thư mục lưu ảnh đã xử lý
        time_interval: Khoảng thời gian giữa các frame (giây)
        config_path: Đường dẫn config ROI
        check_duplicate: Có check duplicate không
        check_camera_shift: Có check camera shift không
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    # Tạo output directory
    create_directories(output_dir)
    
    # Load config
    config = load_config(config_path)
    roi_config = config.get('roi', {})
    
    # Initialize databases
    db_path = 'data/database/vehicle_counting.db'
    init_hash_db(db_path)
    
    memo_db_path = 'data/database/memo.db'
    initialize_memo_database(memo_db_path)
    
    logger.info(f"Processing video: {video_path}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Time interval: {time_interval} seconds")
    
    # Step 1: Cắt video từ 5 phút trở đi (theo yêu cầu)
    logger.info("Step 1: Cutting video from 5 minutes...")
    temp_segments_dir = 'data/temp_segments'
    create_directories(temp_segments_dir)
    
    # Cắt video từ 5 phút trở đi
    segment_files = segment_video(video_path, temp_segments_dir, segment_duration=3600, start_time=300.0)
    
    if not segment_files:
        logger.warning("No segments created, trying to extract directly from video")
        segment_files = [video_path]
    
    # Step 2: Extract frames và apply ROI mask
    total_saved = 0
    
    for seg_idx, segment_path in enumerate(segment_files):
        logger.info(f"Processing segment {seg_idx + 1}/{len(segment_files)}: {segment_path}")
        
        # Extract frames theo time interval
        temp_frames_dir = 'data/temp_frames'
        create_directories(temp_frames_dir)
        
        frame_paths = extract_frames_by_time_interval(
            segment_path,
            temp_frames_dir,
            time_interval_seconds=time_interval
        )
        
        logger.info(f"Extracted {len(frame_paths)} frames from segment")
        
        # Load/create reference frame
        reference_frame = None
        if len(frame_paths) > 0 and check_camera_shift:
            ref_frame_path = "data/reference_frame.jpg"
            if os.path.exists(ref_frame_path):
                reference_frame = load_reference_frame(ref_frame_path)
            else:
                ref_frame = cv2.imread(frame_paths[0])
                if ref_frame is not None:
                    save_reference_frame(ref_frame, ref_frame_path)
                    reference_frame = ref_frame
        
        # Process each frame
        video_name = Path(video_path).stem
        segment_time_offset = 300.0 + (seg_idx * 3600)  # 5 phút base + segment offset
        
        for frame_idx, frame_path in enumerate(frame_paths):
            # Load frame
            frame = cv2.imread(frame_path)
            if frame is None:
                continue
            
            # Tính thời gian frame
            frame_time = segment_time_offset + (frame_idx * time_interval)
            
            # Check duplicate (nếu bật)
            if check_duplicate:
                is_dup, _ = check_duplicate(frame_path, db_path)
                if is_dup:
                    logger.info(f"Skipping duplicate frame at {frame_time:.2f}s")
                    # Lưu memo
                    save_duplicate_memo(
                        memo_db_path, video_path,
                        start_time=max(0, frame_time - 60),
                        end_time=frame_time + 60,
                        description=f"Duplicate at {frame_time:.2f}s"
                    )
                    continue
            
            # Check camera shift (nếu bật)
            if check_camera_shift and reference_frame is not None:
                shift_result = detect_camera_shift(frame, reference_frame, threshold=0.1)
                if shift_result['is_shifted']:
                    logger.warning(f"Camera shift detected at {frame_time:.2f}s")
                    # Lưu memo
                    save_camera_shift_memo(
                        memo_db_path, video_path,
                        shift_time=frame_time,
                        shift_x=shift_result['shift_x'],
                        shift_y=shift_result['shift_y'],
                        rotation=shift_result['rotation'],
                        description=f"Camera shift at {frame_time:.2f}s"
                    )
            
            # Apply ROI mask (bôi đen phần thừa)
            masked_frame = apply_roi_mask(frame, roi_config)
            
            # Save processed image
            output_filename = f"{video_name}_time_{int(frame_time):06d}s_{total_saved:04d}.jpg"
            output_path = os.path.join(output_dir, output_filename)
            cv2.imwrite(output_path, masked_frame)
            
            total_saved += 1
            
            # Save image hash
            save_image_hash(output_path, db_path)
            
            if total_saved % 10 == 0:
                logger.info(f"Saved {total_saved} processed images...")
    
    logger.info(f"✓ Completed! Saved {total_saved} processed images to {output_dir}")
    
    # Cleanup temp files
    import shutil
    if os.path.exists(temp_segments_dir):
        shutil.rmtree(temp_segments_dir)
    if os.path.exists(temp_frames_dir):
        shutil.rmtree(temp_frames_dir)
    
    return total_saved


def main():
    parser = argparse.ArgumentParser(description='Simple Image Extractor - Extract và bôi đen ảnh từ video')
    parser.add_argument('--video', type=str, required=True, help='Đường dẫn video')
    parser.add_argument('--output', type=str, default='extracted_images', help='Thư mục lưu ảnh (default: extracted_images)')
    parser.add_argument('--interval', type=float, default=300.0, help='Khoảng thời gian giữa các frame (giây, default: 300 = 5 phút)')
    parser.add_argument('--config', type=str, default='config/roi_config.json', help='Đường dẫn config ROI')
    parser.add_argument('--no-duplicate-check', action='store_true', help='Tắt check duplicate')
    parser.add_argument('--no-camera-shift-check', action='store_true', help='Tắt check camera shift')
    
    args = parser.parse_args()
    
    try:
        total = process_video_simple(
            video_path=args.video,
            output_dir=args.output,
            time_interval=args.interval,
            config_path=args.config,
            check_duplicate=not args.no_duplicate_check,
            check_camera_shift=not args.no_camera_shift_check
        )
        print(f"\n✓ Success! Saved {total} processed images to {args.output}")
        return 0
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    exit(main())


#!/usr/bin/env python3
"""
System K Vehicle Counting Tool - Web Interface
Web interface để upload video và xem kết quả
"""
import os
import sys
import json
import cv2
import numpy as np
import logging
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
import threading

# Add src to path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from utils import setup_logging, load_config, create_directories, get_timestamp
from video_segmentation import segment_video, get_video_duration
from image_extraction import extract_frames, extract_frames_by_time_interval
from duplicate_detection import check_duplicate, save_image_hash, initialize_database as init_hash_db
from camera_shift_detection import detect_camera_shift, save_reference_frame, load_reference_frame
from memo_system import (
    initialize_memo_database, save_duplicate_memo, save_camera_shift_memo,
    get_duplicate_segments, get_camera_shift_points
)
# Lazy import để tránh Bus error khi khởi động
# from vehicle_detection import VehicleDetector
# from vehicle_tracking import VehicleTracker
# from counting import VehicleCounter
from storage import (
    initialize_database, save_camera_shift
)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'data/input'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB max
app.config['SECRET_KEY'] = 'system-k-secret-key'

# Setup logging
logger = setup_logging(logging.INFO)

# Global variables
processing_status = {
    'is_processing': False,
    'progress': 0,
    'message': '',
    'current_step': ''
}

# Initialize directories
create_directories(
    'data/input',
    'data/output',
    'data/frames',
    'data/processed',
    'data/database',
    'static/uploads',
    'static/frames'
)

ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'flv'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Trang chủ"""
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_video():
    """Upload video"""
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        try:
            filename = secure_filename(file.filename)
            timestamp = get_timestamp()
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Đảm bảo thư mục tồn tại
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            file.save(filepath)
            
            # Kiểm tra file đã được lưu thành công
            if not os.path.exists(filepath):
                logger.error(f"File was not saved: {filepath}")
                return jsonify({'error': 'Failed to save file'}), 500
            
            logger.info(f"Video uploaded successfully: {filename}")
            return jsonify({
                'success': True,
                'filename': filename,
                'message': 'Video uploaded successfully'
            })
        except PermissionError as e:
            logger.error(f"Permission error saving file: {e}")
            return jsonify({'error': f'Permission denied: {str(e)}'}), 500
        except OSError as e:
            logger.error(f"OS error saving file: {e}")
            return jsonify({'error': f'File system error: {str(e)}'}), 500
        except Exception as e:
            logger.error(f"Error saving file: {e}", exc_info=True)
            return jsonify({'error': f'Error saving file: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Unexpected error in upload_video: {e}", exc_info=True)
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


@app.route('/api/process', methods=['POST'])
def process_video():
    """Bắt đầu xử lý video"""
    if processing_status['is_processing']:
        return jsonify({'error': 'Already processing'}), 400
    
    data = request.json
    video_filename = data.get('filename')
    segment_duration = data.get('segment_duration', 300)
    save_frames_interval = data.get('save_frames_interval', None)  # Khoảng thời gian lưu frames (giây)
    
    if not video_filename:
        return jsonify({'error': 'No video filename'}), 400
    
    video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
    if not os.path.exists(video_path):
        return jsonify({'error': 'Video file not found'}), 404
    
    # Start processing in background thread
    thread = threading.Thread(
        target=process_video_thread,
        args=(video_path, segment_duration, save_frames_interval)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': 'Processing started'
    })


def process_video_thread(video_path, segment_duration, save_frames_interval=None):
    """
    Xử lý video trong background thread
    
    Args:
        video_path: Đường dẫn video
        segment_duration: Độ dài mỗi segment (giây)
        save_frames_interval: Khoảng thời gian lưu frames (giây, None = không lưu riêng)
    """
    global processing_status
    
    try:
        processing_status['is_processing'] = True
        processing_status['progress'] = 0
        processing_status['message'] = 'Initializing...'
        
        # Load config (không cần ROI nữa, chỉ cần vehicle_classes)
        config_path = 'config/roi_config.json'
        try:
            config = load_config(config_path)
        except FileNotFoundError:
            # Tạo default config nếu file không tồn tại
            logger.warning(f"Config file not found: {config_path}, using default config")
            config = {
                "vehicle_classes": ["car", "truck", "bus", "motorcycle"]
            }
        
        db_path = 'data/database/vehicle_counting.db'
        initialize_database(db_path)
        init_hash_db(db_path)
        
        # Lazy import để tránh Bus error khi khởi động
        detector = None
        
        try:
            processing_status['message'] = 'Loading YOLO model (this may take a moment)...'
            processing_status['current_step'] = 'Loading YOLO (timeout 30s)...'
            logger.info("Importing vehicle detection modules with timeout protection...")
            
            # Sử dụng yolo_loader với timeout
            from yolo_loader import create_detector_safe
            
            processing_status['current_step'] = 'Creating YOLO detector...'
            
            detector = create_detector_safe(model_path='yolov8n.pt', conf_threshold=0.25, timeout=30)
            
            if detector is None:
                raise RuntimeError("VehicleDetector không thể tạo (timeout hoặc system error)")
            
            logger.info("✓ YOLO detector initialized successfully")
            processing_status['message'] = 'YOLO loaded successfully'
            
        except (SystemError, OSError, RuntimeError, MemoryError, TimeoutError) as e:
            # Bus error hoặc các lỗi hệ thống
            error_msg = f"YOLO không thể load: {type(e).__name__}"
            if isinstance(e, TimeoutError):
                error_msg += " - Timeout (có thể do Bus error)"
            else:
                error_msg += f" - {str(e)}"
            
            logger.error(error_msg, exc_info=True)
            processing_status['message'] = f"WARNING: {error_msg}. Tiếp tục không có YOLO..."
            processing_status['current_step'] = 'YOLO không hoạt động - tiếp tục không có detection'
            # KHÔNG set is_processing = False, tiếp tục với detector=None
            logger.warning("Continuing without YOLO - chỉ có thể segment video và extract frames")
        except Exception as e:
            error_msg = f"Error loading YOLO: {type(e).__name__} - {str(e)}"
            logger.error(error_msg, exc_info=True)
            processing_status['message'] = f"WARNING: {error_msg}. Tiếp tục không có YOLO..."
            processing_status['current_step'] = 'YOLO không hoạt động - tiếp tục không có detection'
            # KHÔNG set is_processing = False, tiếp tục với detector=None
            logger.warning("Continuing without YOLO")
        
        # Kiểm tra nếu YOLO không load được, vẫn tiếp tục với các chức năng khác
        if detector is None:
            logger.warning("YOLO not available, continuing without vehicle detection")
            processing_status['message'] = 'YOLO không khả dụng, tiếp tục không có vehicle detection...'
        
        # Initialize memo database
        memo_db_path = 'data/database/memo.db'
        initialize_memo_database(memo_db_path)
        
        # Step 1: Kiểm tra độ dài video và segment (nếu video dài hơn 5 phút)
        video_duration = get_video_duration(video_path)
        logger.info(f"Video duration: {video_duration:.2f} seconds ({video_duration/60:.2f} minutes)")
        
        segment_files = []
        segment_time_offset = 0.0
        
        if video_duration > 300.0:  # Video dài hơn 5 phút
            # Segment video từ 5 phút trở đi
            processing_status['progress'] = 10
            processing_status['current_step'] = 'Segmenting video (from 5 minutes)...'
            logger.info("Video is longer than 5 minutes, segmenting from 5 minutes...")
            output_dir = "data/output"
            
            try:
                segment_files = segment_video(video_path, output_dir, segment_duration, start_time=300.0)
            except Exception as e:
                logger.error(f"Error segmenting video: {e}", exc_info=True)
                raise RuntimeError(f"Failed to segment video: {str(e)}")
            
            if not segment_files:
                logger.warning("No segments created, processing original video from start")
                segment_files = [video_path]
                segment_time_offset = 0.0
            else:
                segment_time_offset = 300.0  # Bắt đầu từ 5 phút
                logger.info(f"Created {len(segment_files)} video segments")
        else:
            # Video ngắn hơn 5 phút, xử lý trực tiếp từ đầu
            processing_status['progress'] = 10
            processing_status['current_step'] = 'Video is shorter than 5 minutes, processing directly...'
            logger.info("Video is shorter than 5 minutes, processing directly from start")
            segment_files = [video_path]
            segment_time_offset = 0.0
        
        # Process each segment
        total_segments = len(segment_files)
        for seg_idx, segment_path in enumerate(segment_files):
            # Kiểm tra file segment có tồn tại không
            if not os.path.exists(segment_path):
                logger.error(f"Segment file not found: {segment_path}")
                processing_status['message'] = f"Error: Segment file not found: {segment_path}"
                continue
            processing_status['progress'] = 10 + int((seg_idx / total_segments) * 80)
            processing_status['current_step'] = f'Processing segment {seg_idx + 1}/{total_segments}...'
            
            # Extract frames
            frames_dir = "data/frames"
            
            # Nếu có yêu cầu lưu frames theo time interval
            try:
                if save_frames_interval is not None and save_frames_interval > 0:
                    processing_status['current_step'] = f'Extracting frames (every {save_frames_interval}s)...'
                    logger.info(f"Extracting frames with time interval: {save_frames_interval}s from {segment_path}")
                    frame_paths = extract_frames_by_time_interval(
                        segment_path, 
                        frames_dir, 
                        time_interval_seconds=save_frames_interval
                    )
                else:
                    # Extract tất cả frames (cho xử lý)
                    logger.info(f"Extracting all frames from {segment_path}")
                    frame_paths = extract_frames(segment_path, frames_dir, fps=None)
            except (FileNotFoundError, RuntimeError) as e:
                logger.error(f"Error extracting frames from segment {seg_idx + 1}: {e}")
                processing_status['message'] = f"Error extracting frames from segment {seg_idx + 1}: {str(e)}"
                continue  # Skip segment này, tiếp tục với segment tiếp theo
            
            if not frame_paths or len(frame_paths) == 0:
                logger.warning(f"No frames extracted from segment {seg_idx + 1}, skipping")
                continue
            
            # Load/create reference frame
            reference_frame = None
            if len(frame_paths) > 0:
                ref_frame_path = "data/reference_frame.jpg"
                if os.path.exists(ref_frame_path):
                    reference_frame = load_reference_frame(ref_frame_path)
                else:
                    ref_frame = cv2.imread(frame_paths[0])
                    if ref_frame is not None:
                        save_reference_frame(ref_frame, ref_frame_path)
                        reference_frame = ref_frame
            
            # Process each frame
            total_frames = len(frame_paths)
            # Tính offset thời gian cho segment này
            if video_duration > 300.0:
                # Video dài: offset = 300s (5 phút) + segment offset
                current_segment_offset = segment_time_offset + (seg_idx * segment_duration)
            else:
                # Video ngắn: offset = 0 + segment offset
                current_segment_offset = seg_idx * segment_duration
            
            for frame_idx, frame_path in enumerate(frame_paths):
                # Update progress
                frame_progress = (frame_idx / total_frames) * (80 / total_segments) if total_frames > 0 else 0
                processing_status['progress'] = 10 + int((seg_idx / total_segments) * 80) + int(frame_progress)
                processing_status['current_step'] = f'Processing frame {frame_idx + 1}/{total_frames}...'
                
                # Load frame
                frame = cv2.imread(frame_path)
                if frame is None:
                    logger.warning(f"Could not load frame: {frame_path}, skipping")
                    continue
                
                logger.debug(f"Processing frame {frame_idx + 1}/{total_frames}: {os.path.basename(frame_path)}, size: {frame.shape}")
                
                # Tính thời gian của frame trong video gốc
                if save_frames_interval and save_frames_interval > 0:
                    # Nếu extract theo interval, tính thời gian chính xác hơn
                    frame_time = current_segment_offset + (frame_idx * save_frames_interval)
                else:
                    # Nếu extract tất cả frames, ước tính dựa trên FPS
                    cap = cv2.VideoCapture(segment_path)
                    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
                    cap.release()
                    frame_time = current_segment_offset + (frame_idx / fps)
                
                # Check duplicate và lưu memo
                is_duplicate, matched_hash = check_duplicate(frame_path, db_path)
                if is_duplicate:
                    # Lưu memo về duplicate
                    save_duplicate_memo(
                        memo_db_path,
                        video_path,
                        start_time=max(0, frame_time - 60),  # 1 phút trước frame
                        end_time=frame_time + 60,   # 1 phút sau frame
                        description=f"Duplicate frame detected at {frame_time:.2f}s"
                    )
                    logger.info(f"Duplicate detected at {frame_time:.2f}s, but will still save processed image")
                    # KHÔNG continue - vẫn tiếp tục để lưu ảnh (mục đích chính)
                
                # Check camera shift và lưu memo
                if reference_frame is not None:
                    shift_result = detect_camera_shift(frame, reference_frame, threshold=0.1)
                    if shift_result['is_shifted']:
                        warning = f"Camera shift: shift_x={shift_result['shift_x']:.2f}, shift_y={shift_result['shift_y']:.2f}"
                        save_camera_shift(
                            db_path, frame_path,
                            shift_result['shift_x'], shift_result['shift_y'],
                            shift_result['rotation'], True, warning
                        )
                        # Lưu memo về camera shift
                        save_camera_shift_memo(
                            memo_db_path,
                            video_path,
                            shift_time=frame_time,
                            shift_x=shift_result['shift_x'],
                            shift_y=shift_result['shift_y'],
                            rotation=shift_result['rotation'],
                            description=warning
                        )
                        logger.warning(f"Camera shift detected at {frame_time:.2f}s, saved to memo")
                
                # LƯU ẢNH ĐÃ XỬ LÝ (mục đích chính của tool)
                processed_dir = "data/processed_images"
                create_directories(processed_dir)
                
                # Lưu ảnh đã xử lý
                processed_filename = f"{Path(video_path).stem}_processed_time_{int(frame_time):06d}s_{frame_idx:04d}.jpg"
                processed_path = os.path.join(processed_dir, processed_filename)
                
                # Kiểm tra frame có hợp lệ không
                if frame is None or frame.size == 0:
                    logger.error(f"Frame is invalid for frame {frame_idx}")
                    continue
                
                # Lưu ảnh
                logger.debug(f"Attempting to save processed image: {processed_path}")
                success = cv2.imwrite(processed_path, frame)
                
                if success:
                    # Verify file was actually created
                    if os.path.exists(processed_path):
                        file_size = os.path.getsize(processed_path)
                        logger.info(f"✓ Saved processed image: {processed_filename} ({file_size} bytes)")
                    else:
                        logger.error(f"✗ File was not created after cv2.imwrite: {processed_path}")
                        processing_status['message'] = f"Error: File not created: {processed_path}"
                else:
                    logger.error(f"✗ cv2.imwrite returned False for: {processed_path}")
                    processing_status['message'] = f"Warning: Failed to save image. Check permissions for {processed_dir}"
                
                # Save image hash (cho duplicate detection)
                save_image_hash(frame_path, db_path)
        
        # Finalizing
        processing_status['progress'] = 90
        processing_status['current_step'] = 'Finalizing...'
        
        processing_status['progress'] = 100
        processing_status['current_step'] = 'Completed'
        processed_count = len([f for f in os.listdir("data/processed_images") if f.endswith('.jpg')]) if os.path.exists("data/processed_images") else 0
        processing_status['message'] = f"Processing completed! Saved {processed_count} processed images to data/processed_images/"
        
    except Exception as e:
        logger.error(f"Error processing video: {e}", exc_info=True)
        processing_status['message'] = f"Error: {str(e)}"
        processing_status['current_step'] = 'Error'
    finally:
        processing_status['is_processing'] = False


@app.route('/api/status', methods=['GET'])
def get_status():
    """Lấy trạng thái xử lý"""
    return jsonify(processing_status)


@app.route('/api/frames/<path:filename>')
def get_frame(filename):
    """Lấy frame để hiển thị"""
    return send_from_directory('data/frames', filename)


@app.route('/api/processed_images/<path:filename>')
def get_processed_image(filename):
    """Serve processed images (đã được bôi đen)"""
    return send_from_directory('data/processed_images', filename)


@app.route('/api/list_processed_images')
def list_processed_images():
    """List all processed images"""
    try:
        processed_dir = 'data/processed_images'
        if not os.path.exists(processed_dir):
            return jsonify({'success': True, 'images': []})
        
        images = []
        for filename in sorted(os.listdir(processed_dir)):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                filepath = os.path.join(processed_dir, filename)
                file_size = os.path.getsize(filepath)
                images.append({
                    'filename': filename,
                    'url': f'/api/processed_images/{filename}',
                    'size': file_size
                })
        
        return jsonify({
            'success': True,
            'count': len(images),
            'images': images
        })
    except Exception as e:
        logger.error(f"Error listing processed images: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/static/<path:path>')
def send_static(path):
    """Serve static files"""
    return send_from_directory('static', path)


if __name__ == '__main__':
    # Initialize database
    db_path = 'data/database/vehicle_counting.db'
    initialize_database(db_path)
    init_hash_db(db_path)
    
    print("=" * 50)
    print("System K Vehicle Counting Tool - Web Interface")
    print("=" * 50)
    print("Starting server on http://localhost:5000")
    print("Open your browser and navigate to http://localhost:5000")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)


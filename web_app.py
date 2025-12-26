#!/usr/bin/env python3
"""
System K Vehicle Counting Tool - Web Interface
Web interface để upload video, vẽ ROI, và xem kết quả
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
from roi_processing import apply_roi_mask
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
    initialize_database, save_counting_result, save_camera_shift,
    export_to_json, export_to_csv, get_counting_summary
)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'data/input'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max
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
    'results',
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
    if 'video' not in request.files:
        return jsonify({'error': 'No video file'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = get_timestamp()
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Extract first frame for ROI configuration
        cap = cv2.VideoCapture(filepath)
        ret, frame = cap.read()
        if ret:
            frame_path = f"static/frames/{timestamp}_preview.jpg"
            cv2.imwrite(frame_path, frame)
            cap.release()
            
            return jsonify({
                'success': True,
                'filename': filename,
                'preview_frame': frame_path,
                'message': 'Video uploaded successfully'
            })
        cap.release()
        return jsonify({'error': 'Could not extract preview frame'}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400


@app.route('/api/save-config', methods=['POST'])
def save_config():
    """Lưu ROI config"""
    try:
        data = request.json
        config_path = 'config/roi_config.json'
        
        # Validate config (chỉ cần ROI, counting_line là optional)
        required_keys = ['roi', 'vehicle_classes']
        for key in required_keys:
            if key not in data:
                return jsonify({'error': f'Missing key: {key}'}), 400
        
        # Save config
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return jsonify({'success': True, 'message': 'Config saved successfully'})
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/load-config', methods=['GET'])
def load_config_api():
    """Load ROI config"""
    try:
        config_path = 'config/roi_config.json'
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return jsonify({'success': True, 'config': config})
        else:
            # Return default config (không có counting_line)
            default_config = {
                "roi": {
                    "type": "polygon",
                    "points": [[0, 0], [100, 0], [100, 100], [0, 100]],
                    "mask_color": [0, 0, 0]
                },
                "vehicle_classes": ["car", "truck", "bus", "motorcycle"]
            }
            return jsonify({'success': True, 'config': default_config})
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return jsonify({'error': str(e)}), 500


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
        
        # Load config
        config_path = 'config/roi_config.json'
        config = load_config(config_path)
        
        db_path = 'data/database/vehicle_counting.db'
        initialize_database(db_path)
        init_hash_db(db_path)
        
        # Lazy import để tránh Bus error khi khởi động
        detector = None
        tracker = None
        counter = None
        previous_centroids = {}
        
        try:
            processing_status['message'] = 'Loading YOLO model (this may take a moment)...'
            processing_status['current_step'] = 'Loading YOLO (timeout 30s)...'
            logger.info("Importing vehicle detection modules with timeout protection...")
            
            # Sử dụng yolo_loader với timeout
            from yolo_loader import load_yolo_with_timeout, create_detector_safe
            
            VehicleDetectorClass, VehicleTrackerClass, VehicleCounterClass = load_yolo_with_timeout(timeout_seconds=30)
            
            if VehicleDetectorClass is None:
                raise RuntimeError("YOLO modules không thể import (timeout hoặc system error)")
            
            logger.info("YOLO modules imported, creating instances...")
            processing_status['current_step'] = 'Creating YOLO detector...'
            
            detector = create_detector_safe(model_path='yolov8n.pt', conf_threshold=0.25, timeout=30)
            
            if detector is None:
                raise RuntimeError("VehicleDetector không thể tạo (timeout hoặc system error)")
            
                logger.info("Creating tracker and counter...")
                tracker = VehicleTrackerClass()
                # Chỉ tạo counter nếu có counting_line trong config
                if 'counting_line' in config and config.get('counting_line'):
                    counter = VehicleCounterClass(config['counting_line'])
                else:
                    logger.info("No counting_line in config, skipping vehicle counting")
                    counter = None
            
            logger.info("✓ All YOLO components initialized successfully")
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
                
                # Check duplicate và lưu memo (NHƯNG VẪN LƯU ẢNH ĐÃ BÔI ĐEN)
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
                    # KHÔNG continue - vẫn tiếp tục để lưu ảnh đã bôi đen (mục đích chính)
                
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
                
                # Apply ROI mask (bôi đen phần thừa)
                try:
                    roi_config = config['roi'].copy()
                    if 'points' in roi_config:
                        # Lấy kích thước frame thực tế
                        frame_h, frame_w = frame.shape[:2]
                        
                        # Lấy preview frame size từ config hoặc từ reference frame
                        # Preview frame có thể có kích thước khác với frame thực tế
                        # Cần scale ROI points từ preview size sang frame size
                        preview_frame_path = "data/reference_frame.jpg"
                        if os.path.exists(preview_frame_path):
                            preview_frame = cv2.imread(preview_frame_path)
                            if preview_frame is not None:
                                preview_h, preview_w = preview_frame.shape[:2]
                                
                                # Tính scale factor
                                scale_x = frame_w / preview_w if preview_w > 0 else 1.0
                                scale_y = frame_h / preview_h if preview_h > 0 else 1.0
                                
                                # Scale ROI points từ preview size sang frame size
                                scaled_points = []
                                for p in roi_config['points']:
                                    scaled_x = p[0] * scale_x
                                    scaled_y = p[1] * scale_y
                                    scaled_points.append([scaled_x, scaled_y])
                                
                                roi_config['points'] = scaled_points
                                logger.info(f"Scaled ROI points: preview {preview_w}x{preview_h} -> frame {frame_w}x{frame_h} (scale: {scale_x:.3f}x{scale_y:.3f})")
                            else:
                                logger.warning("Could not load preview frame for scaling, using ROI points as is")
                        else:
                            # Nếu không có preview frame, giả sử ROI points đã đúng với frame size
                            max_x = max([p[0] for p in roi_config['points']] if roi_config['points'] else [0])
                            max_y = max([p[1] for p in roi_config['points']] if roi_config['points'] else [0])
                            logger.debug(f"Frame size: {frame_w}x{frame_h}, ROI points: {len(roi_config['points'])} points, max: ({max_x}, {max_y})")
                            # Nếu points quá nhỏ so với frame, có thể cần scale
                            if max_x < frame_w * 0.5 or max_y < frame_h * 0.5:
                                logger.warning(f"ROI points may need scaling: max ({max_x}, {max_y}) vs frame ({frame_w}, {frame_h})")
                    
                    masked_frame = apply_roi_mask(frame, roi_config)
                    logger.debug(f"Applied ROI mask to frame {frame_idx}, original shape: {frame.shape}, masked shape: {masked_frame.shape}")
                except Exception as e:
                    logger.error(f"Error applying ROI mask to frame {frame_idx}: {e}", exc_info=True)
                    # Nếu lỗi, vẫn lưu frame gốc nhưng log warning
                    masked_frame = frame
                    processing_status['message'] = f"Warning: ROI mask failed, saving original frame"
                
                # LƯU ẢNH ĐÃ ĐƯỢC BÔI ĐEN (mục đích chính của tool)
                processed_dir = "data/processed_images"
                create_directories(processed_dir)
                
                # Lưu ảnh đã được bôi đen
                processed_filename = f"{Path(video_path).stem}_processed_time_{int(frame_time):06d}s_{frame_idx:04d}.jpg"
                processed_path = os.path.join(processed_dir, processed_filename)
                
                # Kiểm tra masked_frame có hợp lệ không
                if masked_frame is None or masked_frame.size == 0:
                    logger.error(f"Masked frame is invalid for frame {frame_idx}")
                    continue
                
                # Lưu ảnh - QUAN TRỌNG: Luôn lưu ảnh đã được bôi đen
                logger.debug(f"Attempting to save processed image: {processed_path}")
                success = cv2.imwrite(processed_path, masked_frame)
                
                if success:
                    # Verify file was actually created
                    if os.path.exists(processed_path):
                        file_size = os.path.getsize(processed_path)
                        # Kiểm tra xem ảnh có thực sự được bôi đen không (so sánh với ảnh gốc)
                        diff = cv2.absdiff(frame, masked_frame)
                        black_pixels = np.sum(diff > 10)  # Đếm số pixel khác biệt (đã bôi đen)
                        total_pixels = frame.shape[0] * frame.shape[1]
                        black_ratio = (black_pixels / total_pixels) * 100 if total_pixels > 0 else 0
                        logger.info(f"✓ Saved processed image: {processed_filename} ({file_size} bytes) | Blackout ratio: {black_ratio:.1f}% ({black_pixels}/{total_pixels} pixels changed)")
                    else:
                        logger.error(f"✗ File was not created after cv2.imwrite: {processed_path}")
                        processing_status['message'] = f"Error: File not created: {processed_path}"
                else:
                    logger.error(f"✗ cv2.imwrite returned False for: {processed_path}")
                    processing_status['message'] = f"Warning: Failed to save image. Check permissions for {processed_dir}"
                
                # Detect vehicles (chỉ nếu detector đã được khởi tạo) - TÙY CHỌN
                detections = []
                if detector is not None:
                    try:
                        detections = detector.detect_vehicles(
                            masked_frame,
                            vehicle_classes=config.get('vehicle_classes', None)
                        )
                    except Exception as e:
                        logger.error(f"Error detecting vehicles in frame {frame_idx}: {e}", exc_info=True)
                        detections = []
                else:
                    # YOLO không khả dụng, skip detection
                    detections = []
                
                # Track vehicles (chỉ nếu tracker đã được khởi tạo)
                tracked_objects = []
                if tracker is not None:
                    try:
                        tracked_objects = tracker.update(detections)
                    except Exception as e:
                        logger.error(f"Error tracking vehicles in frame {frame_idx}: {e}", exc_info=True)
                        tracked_objects = []
                
                # Update centroids
                current_centroids = {obj['track_id']: obj['centroid'] for obj in tracked_objects}
                
                # Count vehicles (chỉ nếu counter đã được khởi tạo)
                if counter is not None:
                    counting_result, counter = counter.count_vehicles(
                        tracked_objects,
                        previous_centroids
                    )
                    previous_centroids = current_centroids
                else:
                    # Fallback: không có counting
                    counting_result = {
                        'count_up': 0,
                        'count_down': 0,
                        'total': 0,
                        'new_counts': []
                    }
                
                # Save counting results (chỉ nếu có counter)
                if counter is not None:
                    save_counting_result(
                        db_path,
                        video_path=video_path,
                        frame_path=frame_path,
                        vehicle_count_up=counting_result['count_up'],
                        vehicle_count_down=counting_result['count_down'],
                        total_count=counting_result['total'],
                        frame_number=frame_idx
                    )
                
                # Save image hash (cho duplicate detection)
                save_image_hash(frame_path, db_path)
        
        # Export results (nếu có vehicle counting)
        processing_status['progress'] = 90
        processing_status['current_step'] = 'Finalizing...'
        
        # Get summary (nếu có counting)
        summary = {'count_up': 0, 'count_down': 0, 'total': 0}
        if counter is not None:
            summary = get_counting_summary(db_path, video_path)
            timestamp = get_timestamp()
            video_name = Path(video_path).stem
            export_to_json(db_path, f"results/counting_results_{video_name}_{timestamp}.json", 'counting_results')
            export_to_csv(db_path, f"results/counting_results_{video_name}_{timestamp}.csv", 'counting_results')
        
        processing_status['progress'] = 100
        processing_status['current_step'] = 'Completed'
        processed_count = len([f for f in os.listdir("data/processed_images") if f.endswith('.jpg')]) if os.path.exists("data/processed_images") else 0
        processing_status['message'] = f"Processing completed! Saved {processed_count} processed images to data/processed_images/"
        if summary['total'] > 0:
            processing_status['message'] += f" | Vehicles counted: {summary['total']}"
        processing_status['summary'] = summary
        
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


@app.route('/api/results', methods=['GET'])
def get_results():
    """Lấy kết quả: số lượng ảnh đã xử lý và kết quả đếm xe (nếu có)"""
    try:
        # Đếm số ảnh đã xử lý
        processed_dir = 'data/processed_images'
        processed_count = 0
        if os.path.exists(processed_dir):
            processed_count = len([f for f in os.listdir(processed_dir) if f.endswith('.jpg')])
        
        # Lấy kết quả đếm xe (nếu có)
        db_path = 'data/database/vehicle_counting.db'
        summary = {'count_up': 0, 'count_down': 0, 'total': 0}
        recent_results = []
        
        if os.path.exists(db_path):
            summary = get_counting_summary(db_path)
            
            # Get recent results
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, vehicle_count_up, vehicle_count_down, total_count
                FROM counting_results
                ORDER BY timestamp DESC
                LIMIT 100
            ''')
            rows = cursor.fetchall()
            conn.close()
            
            recent_results = [
                {
                    'timestamp': row[0],
                    'count_up': row[1],
                    'count_down': row[2],
                    'total': row[3]
                }
                for row in rows
            ]
        
        return jsonify({
            'success': True,
            'processed_images_count': processed_count,
            'processed_images_dir': processed_dir,
            'summary': summary,
            'recent_results': recent_results
        })
    except Exception as e:
        logger.error(f"Error getting results: {e}")
        return jsonify({'error': str(e)}), 500


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


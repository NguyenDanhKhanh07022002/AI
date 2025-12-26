"""
System K Vehicle Counting Tool - Main Entry Point
Pipeline workflow: Segment video → Extract frames → Process → Detect → Track → Count
"""
import os
import sys
import cv2
import argparse
import logging
from pathlib import Path
from tqdm import tqdm
from typing import Dict, Optional

# Add src directory to Python path to ensure imports work
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Import modules
from utils import (
    setup_logging, load_config, create_directories,
    get_timestamp, get_video_name, validate_config
)
from video_segmentation import segment_video
from image_extraction import extract_frames
from roi_processing import apply_roi_mask
from duplicate_detection import check_duplicate, save_image_hash, initialize_database as init_hash_db
from camera_shift_detection import (
    detect_camera_shift, save_reference_frame, load_reference_frame
)
from vehicle_detection import VehicleDetector
from vehicle_tracking import VehicleTracker
from counting import VehicleCounter
from storage import (
    initialize_database, save_counting_result, save_camera_shift,
    export_to_json, export_to_csv, get_counting_summary
)

logger = logging.getLogger(__name__)


class SystemKPipeline:
    """Main pipeline cho System K vehicle counting"""
    
    def __init__(self, config_path: str, db_path: str, reference_frame_path: Optional[str] = None):
        """
        Khởi tạo pipeline
        
        Args:
            config_path: Đường dẫn đến config file
            db_path: Đường dẫn đến database
            reference_frame_path: Đường dẫn đến reference frame (None = sẽ tạo từ frame đầu)
        """
        self.config = load_config(config_path)
        validate_config(self.config)
        
        self.db_path = db_path
        self.reference_frame_path = reference_frame_path
        
        # Initialize database
        initialize_database(db_path)
        init_hash_db(db_path)  # Initialize hash database
        
        # Initialize vehicle detector
        self.detector = VehicleDetector(model_path='yolov8n.pt', conf_threshold=0.25)
        
        # Initialize tracker
        self.tracker = VehicleTracker()
        
        # Initialize counter
        self.counter = VehicleCounter(self.config['counting_line'])
        
        # Store previous centroids for tracking
        self.previous_centroids = {}
        
        logger.info("System K Pipeline initialized")
    
    def process_video(self, video_path: str, segment_duration: int = 300):
        """
        Xử lý video hoàn chỉnh
        
        Args:
            video_path: Đường dẫn đến video input
            segment_duration: Độ dài mỗi segment (giây)
        """
        logger.info(f"Processing video: {video_path}")
        
        # Step 1: Segment video
        logger.info("Step 1: Segmenting video...")
        output_dir = "data/output"
        create_directories(output_dir)
        
        segment_files = segment_video(video_path, output_dir, segment_duration)
        logger.info(f"Created {len(segment_files)} video segments")
        
        # Process each segment
        for segment_idx, segment_path in enumerate(segment_files):
            logger.info(f"Processing segment {segment_idx + 1}/{len(segment_files)}: {segment_path}")
            self.process_segment(segment_path, segment_idx)
        
        # Export results
        self.export_results(video_path)
    
    def process_segment(self, segment_path: str, segment_idx: int):
        """
        Xử lý một video segment
        
        Args:
            segment_path: Đường dẫn đến video segment
            segment_idx: Index của segment
        """
        # Step 2: Extract frames
        logger.info("Step 2: Extracting frames...")
        frames_dir = "data/frames"
        create_directories(frames_dir)
        
        frame_paths = extract_frames(segment_path, frames_dir, fps=None)
        logger.info(f"Extracted {len(frame_paths)} frames")
        
        # Load reference frame nếu chưa có
        if self.reference_frame_path is None or not os.path.exists(self.reference_frame_path):
            if len(frame_paths) > 0:
                # Sử dụng frame đầu làm reference
                ref_frame = cv2.imread(frame_paths[0])
                if ref_frame is not None:
                    self.reference_frame_path = "data/reference_frame.jpg"
                    save_reference_frame(ref_frame, self.reference_frame_path)
                    logger.info(f"Created reference frame from first frame")
        
        reference_frame = load_reference_frame(self.reference_frame_path)
        
        # Process each frame
        for frame_idx, frame_path in enumerate(tqdm(frame_paths, desc="Processing frames")):
            self.process_frame(
                frame_path,
                segment_path,
                frame_idx,
                reference_frame
            )
    
    def process_frame(
        self,
        frame_path: str,
        video_path: str,
        frame_number: int,
        reference_frame: Optional[cv2.typing.MatLike]
    ):
        """
        Xử lý một frame
        
        Args:
            frame_path: Đường dẫn đến frame
            video_path: Đường dẫn đến video gốc
            frame_number: Số thứ tự frame
            reference_frame: Reference frame để check camera shift
        """
        # Load frame
        frame = cv2.imread(frame_path)
        if frame is None:
            logger.warning(f"Could not load frame: {frame_path}")
            return
        
        # Step 3: Check duplicate
        is_duplicate, _ = check_duplicate(frame_path, self.db_path)
        if is_duplicate:
            logger.debug(f"Skipping duplicate frame: {frame_path}")
            return
        
        # Step 4: Check camera shift
        if reference_frame is not None:
            shift_result = detect_camera_shift(frame, reference_frame, threshold=0.1)
            
            if shift_result['is_shifted']:
                warning = (
                    f"Camera shift detected: "
                    f"shift_x={shift_result['shift_x']:.2f}, "
                    f"shift_y={shift_result['shift_y']:.2f}, "
                    f"rotation={shift_result['rotation']:.2f}°"
                )
                logger.warning(warning)
                
                save_camera_shift(
                    self.db_path,
                    frame_path,
                    shift_result['shift_x'],
                    shift_result['shift_y'],
                    shift_result['rotation'],
                    True,
                    warning
                )
        
        # Step 5: Apply ROI mask
        masked_frame = apply_roi_mask(frame, self.config['roi'])
        
        # Step 6: Detect vehicles
        detections = self.detector.detect_vehicles(
            masked_frame,
            vehicle_classes=self.config.get('vehicle_classes', None)
        )
        
        # Step 7: Track vehicles
        tracked_objects = self.tracker.update(detections)
        
        # Update previous centroids
        current_centroids = {obj['track_id']: obj['centroid'] for obj in tracked_objects}
        
        # Step 8: Count vehicles
        counting_result, self.counter = self.counter.count_vehicles(
            tracked_objects,
            self.previous_centroids
        )
        
        # Update previous centroids
        self.previous_centroids = current_centroids
        
        # Step 9: Save results
        save_counting_result(
            self.db_path,
            video_path=video_path,
            frame_path=frame_path,
            vehicle_count_up=counting_result['count_up'],
            vehicle_count_down=counting_result['count_down'],
            total_count=counting_result['total'],
            frame_number=frame_number
        )
        
        # Save image hash
        save_image_hash(frame_path, self.db_path)
    
    def export_results(self, video_path: str):
        """Export kết quả ra JSON và CSV"""
        logger.info("Exporting results...")
        
        timestamp = get_timestamp()
        video_name = get_video_name(video_path)
        
        # Export counting results
        json_path = f"results/counting_results_{video_name}_{timestamp}.json"
        csv_path = f"results/counting_results_{video_name}_{timestamp}.csv"
        
        export_to_json(self.db_path, json_path, table='counting_results')
        export_to_csv(self.db_path, csv_path, table='counting_results')
        
        # Export camera shifts
        json_shift_path = f"results/camera_shifts_{video_name}_{timestamp}.json"
        csv_shift_path = f"results/camera_shifts_{video_name}_{timestamp}.csv"
        
        export_to_json(self.db_path, json_shift_path, table='camera_shifts')
        export_to_csv(self.db_path, csv_shift_path, table='camera_shifts')
        
        # Print summary
        summary = get_counting_summary(self.db_path, video_path)
        logger.info("=" * 50)
        logger.info("COUNTING SUMMARY")
        logger.info(f"Count Up: {summary['count_up']}")
        logger.info(f"Count Down: {summary['count_down']}")
        logger.info(f"Total: {summary['total']}")
        logger.info("=" * 50)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='System K Vehicle Counting Tool')
    parser.add_argument(
        '--video',
        type=str,
        required=True,
        help='Path to input video file'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/roi_config.json',
        help='Path to ROI config file (default: config/roi_config.json)'
    )
    parser.add_argument(
        '--db',
        type=str,
        default='data/database/vehicle_counting.db',
        help='Path to database file (default: data/database/vehicle_counting.db)'
    )
    parser.add_argument(
        '--segment-duration',
        type=int,
        default=300,
        help='Segment duration in seconds (default: 300 = 5 minutes)'
    )
    parser.add_argument(
        '--reference-frame',
        type=str,
        default=None,
        help='Path to reference frame (optional, will use first frame if not provided)'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = getattr(logging, args.log_level.upper())
    setup_logging(log_level)
    
    # Create necessary directories
    create_directories(
        'data/input',
        'data/output',
        'data/frames',
        'data/processed',
        'data/database',
        'results'
    )
    
    # Check if video exists
    if not os.path.exists(args.video):
        logger.error(f"Video file not found: {args.video}")
        sys.exit(1)
    
    # Check if config exists
    if not os.path.exists(args.config):
        logger.error(f"Config file not found: {args.config}")
        sys.exit(1)
    
    try:
        # Initialize pipeline
        pipeline = SystemKPipeline(
            config_path=args.config,
            db_path=args.db,
            reference_frame_path=args.reference_frame
        )
        
        # Process video
        pipeline.process_video(args.video, segment_duration=args.segment_duration)
        
        logger.info("Processing completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during processing: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()


# Hướng dẫn Test System K Vehicle Counting Tool

## Bước 1: Kiểm tra Dependencies

### 1.1 Kiểm tra Python version
```bash
python3 --version
# Cần Python 3.8+
```

### 1.2 Kiểm tra FFmpeg
```bash
ffmpeg -version
# Nếu chưa có, cài đặt: sudo apt install ffmpeg
```

### 1.3 Cài đặt Python packages
```bash
pip install -r requirements.txt
```

### 1.4 Kiểm tra YOLO model
YOLO model sẽ được download tự động lần đầu chạy. Hoặc test thủ công:
```python
from ultralytics import YOLO
model = YOLO('yolov8n.pt')
print("YOLO model loaded successfully")
```

## Bước 2: Test Từng Module

### 2.1 Test Video Segmentation
```python
# test_video_segmentation.py
import sys
sys.path.insert(0, 'src')
from video_segmentation import segment_video

# Test với video mẫu
segment_files = segment_video(
    'data/input/test_video.mp4',
    'data/output',
    segment_duration=60  # 1 phút
)
print(f"Created {len(segment_files)} segments")
```

### 2.2 Test Image Extraction
```python
# test_image_extraction.py
import sys
sys.path.insert(0, 'src')
from image_extraction import extract_frames

frame_paths = extract_frames(
    'data/output/test_video_segment_000.mp4',
    'data/frames',
    fps=1  # Extract 1 frame/giây
)
print(f"Extracted {len(frame_paths)} frames")
```

### 2.3 Test ROI Processing
```python
# test_roi_processing.py
import sys
import cv2
sys.path.insert(0, 'src')
from roi_processing import apply_roi_mask
from utils import load_config

config = load_config('config/roi_config.json')
frame = cv2.imread('data/frames/test_frame_000000.jpg')
masked_frame = apply_roi_mask(frame, config['roi'])
cv2.imwrite('data/processed/test_masked.jpg', masked_frame)
print("ROI mask applied successfully")
```

### 2.4 Test Duplicate Detection
```python
# test_duplicate_detection.py
import sys
sys.path.insert(0, 'src')
from duplicate_detection import check_duplicate, save_image_hash, initialize_database

db_path = 'data/database/vehicle_counting.db'
initialize_database(db_path)

# Test với frame đầu
save_image_hash('data/frames/test_frame_000000.jpg', db_path)
is_dup, _ = check_duplicate('data/frames/test_frame_000000.jpg', db_path)
print(f"Is duplicate: {is_dup}")  # Should be True
```

### 2.5 Test Camera Shift Detection
```python
# test_camera_shift.py
import sys
import cv2
sys.path.insert(0, 'src')
from camera_shift_detection import detect_camera_shift, save_reference_frame

ref_frame = cv2.imread('data/frames/test_frame_000000.jpg')
save_reference_frame(ref_frame, 'data/reference_frame.jpg')

# Test với frame khác
curr_frame = cv2.imread('data/frames/test_frame_000100.jpg')
result = detect_camera_shift(curr_frame, ref_frame)
print(f"Camera shift detected: {result['is_shifted']}")
print(f"Shift: ({result['shift_x']:.2f}, {result['shift_y']:.2f})")
```

### 2.6 Test Vehicle Detection
```python
# test_vehicle_detection.py
import sys
import cv2
sys.path.insert(0, 'src')
from vehicle_detection import VehicleDetector

detector = VehicleDetector(model_path='yolov8n.pt')
frame = cv2.imread('data/frames/test_frame_000000.jpg')
detections = detector.detect_vehicles(frame)
print(f"Detected {len(detections)} vehicles")
for det in detections:
    print(f"  - {det['class']}: {det['confidence']:.2f}")
```

### 2.7 Test Vehicle Tracking
```python
# test_vehicle_tracking.py
import sys
sys.path.insert(0, 'src')
from vehicle_tracking import VehicleTracker
from vehicle_detection import VehicleDetector
import cv2

detector = VehicleDetector()
tracker = VehicleTracker()

# Test với 2 frames
frame1 = cv2.imread('data/frames/test_frame_000000.jpg')
frame2 = cv2.imread('data/frames/test_frame_000001.jpg')

detections1 = detector.detect_vehicles(frame1)
tracked1 = tracker.update(detections1)
print(f"Frame 1: {len(tracked1)} tracked vehicles")

detections2 = detector.detect_vehicles(frame2)
tracked2 = tracker.update(detections2)
print(f"Frame 2: {len(tracked2)} tracked vehicles")
```

### 2.8 Test Counting
```python
# test_counting.py
import sys
sys.path.insert(0, 'src')
from counting import VehicleCounter
from utils import load_config

config = load_config('config/roi_config.json')
counter = VehicleCounter(config['counting_line'])

# Mock tracked objects
tracked_objects = [
    {'track_id': 1, 'centroid': (100, 200), 'class': 'car'},
    {'track_id': 2, 'centroid': (300, 400), 'class': 'truck'}
]

previous_centroids = {1: (100, 250), 2: (300, 350)}
result = counter.count_vehicles(tracked_objects, previous_centroids)
print(f"Count result: {result}")
```

### 2.9 Test Storage
```python
# test_storage.py
import sys
sys.path.insert(0, 'src')
from storage import (
    initialize_database, save_counting_result,
    save_camera_shift, export_to_json, export_to_csv
)

db_path = 'data/database/vehicle_counting.db'
initialize_database(db_path)

# Test save counting result
save_counting_result(
    db_path,
    video_path='test_video.mp4',
    frame_path='test_frame.jpg',
    vehicle_count_up=5,
    vehicle_count_down=3,
    total_count=8
)

# Test export
export_to_json(db_path, 'results/test_counting.json')
export_to_csv(db_path, 'results/test_counting.csv')
print("Storage test completed")
```

## Bước 3: Test Pipeline Hoàn Chỉnh

### 3.1 Chuẩn bị dữ liệu test

1. Đặt video test vào `data/input/`
2. Cấu hình ROI trong `config/roi_config.json`

### 3.2 Test với video ngắn (1-2 phút)

```bash
# Test với video ngắn trước
python3 src/main.py \
    --video data/input/test_short.mp4 \
    --config config/roi_config.json \
    --segment-duration 30 \
    --log-level DEBUG
```

### 3.3 Kiểm tra kết quả

```bash
# Kiểm tra database
sqlite3 data/database/vehicle_counting.db "SELECT * FROM counting_results LIMIT 10;"

# Kiểm tra files output
ls -lh data/output/
ls -lh data/frames/
ls -lh results/
```

### 3.4 Test với video dài

```bash
# Test với video dài (sẽ tự động cắt thành segments)
python3 src/main.py \
    --video data/input/test_long.mp4 \
    --segment-duration 300 \
    --log-level INFO
```

## Bước 4: Test Edge Cases

### 4.1 Test với video không tồn tại
```bash
python src/main.py --video data/input/nonexistent.mp4
# Should show error message
```

### 4.2 Test với config không hợp lệ
```bash
# Tạo config sai
python src/main.py --video data/input/test.mp4 --config invalid_config.json
# Should show validation error
```

### 4.3 Test với video không có xe
```bash
# Test với video chỉ có background
python src/main.py --video data/input/no_vehicles.mp4
# Should complete without errors, count = 0
```

### 4.4 Test với duplicate frames
```bash
# Chạy 2 lần với cùng video
python src/main.py --video data/input/test.mp4
python src/main.py --video data/input/test.mp4
# Lần 2 should skip duplicate frames
```

## Bước 5: Test Performance

### 5.1 Đo thời gian xử lý
```bash
time python src/main.py --video data/input/test.mp4
```

### 5.2 Kiểm tra memory usage
```bash
# Sử dụng htop hoặc top trong terminal khác
python src/main.py --video data/input/test.mp4
```

### 5.3 Test với batch processing
```bash
# Xử lý nhiều video
for video in data/input/*.mp4; do
    python src/main.py --video "$video"
done
```

## Bước 6: Kiểm tra Kết quả

### 6.1 Kiểm tra database
```python
import sqlite3
conn = sqlite3.connect('data/database/vehicle_counting.db')
cursor = conn.cursor()

# Tổng số records
cursor.execute("SELECT COUNT(*) FROM counting_results")
print(f"Total records: {cursor.fetchone()[0]}")

# Summary
cursor.execute("""
    SELECT 
        SUM(vehicle_count_up) as up,
        SUM(vehicle_count_down) as down,
        SUM(total_count) as total
    FROM counting_results
""")
result = cursor.fetchone()
print(f"Count Up: {result[0]}, Count Down: {result[1]}, Total: {result[2]}")
conn.close()
```

### 6.2 Kiểm tra JSON/CSV exports
```bash
# Xem JSON
cat results/counting_results_*.json | head -20

# Xem CSV
head -10 results/counting_results_*.csv
```

### 6.3 Kiểm tra camera shifts
```bash
sqlite3 data/database/vehicle_counting.db "SELECT * FROM camera_shifts WHERE is_shifted = 1;"
```

## Bước 7: Test Script Tự Động

Chạy script test tự động:

```bash
python3 tests/test_all.py
```

## Troubleshooting

### Lỗi FFmpeg not found
```bash
which ffmpeg
# Nếu không có, cài đặt: sudo apt install ffmpeg
```

### Lỗi YOLO model download
- Kiểm tra kết nối internet
- Hoặc download thủ công và đặt vào thư mục phù hợp

### Lỗi Memory
- Giảm `--segment-duration`
- Giảm số frames extract (tăng fps parameter)

### Lỗi Import
```bash
# Đảm bảo đang ở thư mục project root
cd /home/khanhnd4/AI
python src/main.py --video ...
```


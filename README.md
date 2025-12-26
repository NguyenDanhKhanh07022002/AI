# System K Vehicle Counting Tool

Tool Python modular để đếm xe từ video với các chức năng:
- Cắt video dài thành video ngắn (FFmpeg)
- Extract frames từ video
- Bôi đen phần thừa (ROI masking)
- Kiểm tra ảnh trùng với hôm trước
- Kiểm tra camera bị lệch
- Phát hiện và đếm xe (YOLOv8 + Tracking)

## Cài đặt

### Yêu cầu

- Python 3.8+
- FFmpeg (cần cài đặt riêng)

### Cài đặt FFmpeg

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download từ https://ffmpeg.org/download.html

### Cài đặt Python dependencies

```bash
pip install -r requirements.txt
```

## Cấu trúc Project

```
/home/khanhnd4/AI/
├── requirements.txt
├── README.md
├── config/
│   └── roi_config.json          # Cấu hình ROI và counting line
├── src/
│   ├── __init__.py
│   ├── main.py                  # Entry point
│   ├── video_segmentation.py   # Module 1: Cắt video bằng FFmpeg
│   ├── image_extraction.py      # Module 2: Video → Frames
│   ├── roi_processing.py        # Module 3: Bôi đen phần thừa
│   ├── duplicate_detection.py   # Module 4: Check ảnh trùng
│   ├── camera_shift_detection.py # Module 5: Check camera lệch
│   ├── vehicle_detection.py     # Module 6: YOLO detection
│   ├── vehicle_tracking.py      # Module 7: Object tracking
│   ├── counting.py              # Module 8: Logic đếm xe
│   ├── storage.py               # Module 9: Lưu kết quả
│   └── utils.py                 # Utilities chung
├── data/
│   ├── input/                   # Video input
│   ├── output/                  # Video output sau khi cắt
│   ├── frames/                  # Frames extracted
│   ├── processed/               # Frames sau khi xử lý
│   └── database/                # SQLite database
└── results/                     # Kết quả đếm xe (JSON/CSV)
```

## Cấu hình

Chỉnh sửa file `config/roi_config.json` để cấu hình:

- **ROI (Region of Interest)**: Vùng cần giữ lại (phần ngoài sẽ bị bôi đen)
- **Counting Line**: Đường đếm xe
- **Vehicle Classes**: Các loại xe cần detect

Ví dụ:

```json
{
  "roi": {
    "type": "polygon",
    "points": [[100, 100], [800, 100], [800, 600], [100, 600]],
    "mask_color": [0, 0, 0]
  },
  "counting_line": {
    "type": "line",
    "start": [400, 100],
    "end": [400, 600],
    "direction": "vertical"
  },
  "vehicle_classes": ["car", "truck", "bus", "motorcycle"]
}
```

## Sử dụng

### Basic usage

```bash
python3 src/main.py --video data/input/video.mp4
```

### Với các tùy chọn

```bash
python3 src/main.py \
    --video data/input/video.mp4 \
    --config config/roi_config.json \
    --db data/database/vehicle_counting.db \
    --segment-duration 300 \
    --reference-frame data/reference_frame.jpg \
    --log-level INFO
```

### Các tham số

- `--video`: Đường dẫn đến video input (bắt buộc)
- `--config`: Đường dẫn đến file config (mặc định: `config/roi_config.json`)
- `--db`: Đường dẫn đến database (mặc định: `data/database/vehicle_counting.db`)
- `--segment-duration`: Độ dài mỗi segment (giây, mặc định: 300 = 5 phút)
- `--reference-frame`: Đường dẫn đến reference frame (tùy chọn, sẽ dùng frame đầu nếu không có)
- `--log-level`: Mức độ logging (DEBUG, INFO, WARNING, ERROR, mặc định: INFO)

## Workflow

1. **Segment video**: Cắt video dài thành các video ngắn (theo thời gian)
2. **Extract frames**: Chuyển video ngắn thành frames
3. **Check duplicate**: Kiểm tra frame có trùng với hôm trước không → Skip nếu trùng
4. **Check camera shift**: Kiểm tra camera có bị lệch không → Cảnh báo nếu lệch
5. **Apply ROI mask**: Bôi đen phần thừa
6. **Detect vehicles**: Phát hiện xe bằng YOLOv8
7. **Track vehicles**: Theo dõi xe qua các frames
8. **Count vehicles**: Đếm xe khi vượt qua counting line
9. **Save results**: Lưu kết quả vào SQLite, JSON, CSV

## Kết quả

Kết quả được lưu trong thư mục `results/`:

- `counting_results_*.json`: Kết quả đếm xe (JSON)
- `counting_results_*.csv`: Kết quả đếm xe (CSV)
- `camera_shifts_*.json`: Thông tin camera shift (JSON)
- `camera_shifts_*.csv`: Thông tin camera shift (CSV)

Database SQLite chứa:
- `counting_results`: Kết quả đếm xe chi tiết
- `camera_shifts`: Thông tin camera shift
- `image_hashes`: Hash của các ảnh đã xử lý

## Modules

### 1. video_segmentation.py
Cắt video dài thành video ngắn sử dụng FFmpeg.

### 2. image_extraction.py
Extract frames từ video sử dụng OpenCV.

### 3. roi_processing.py
Áp dụng ROI mask để bôi đen phần thừa.

### 4. duplicate_detection.py
Kiểm tra ảnh trùng sử dụng perceptual hashing.

### 5. camera_shift_detection.py
Phát hiện camera bị lệch sử dụng feature matching (ORB).

### 6. vehicle_detection.py
Phát hiện xe sử dụng YOLOv8 (Ultralytics).

### 7. vehicle_tracking.py
Theo dõi xe qua các frames sử dụng tracking algorithm.

### 8. counting.py
Logic đếm xe khi vượt qua counting line.

### 9. storage.py
Lưu kết quả vào SQLite, export ra JSON/CSV.

## Lưu ý

- Đảm bảo FFmpeg đã được cài đặt và có trong PATH
- YOLOv8 model sẽ được download tự động lần đầu chạy
- Cần cấu hình ROI và counting line phù hợp với video của bạn
- Reference frame nên là frame ổn định, không có xe di chuyển

## Troubleshooting

### FFmpeg not found
Đảm bảo FFmpeg đã được cài đặt và có trong PATH:
```bash
ffmpeg -version
```

### YOLO model download slow
Model sẽ được download tự động. Nếu chậm, có thể download thủ công và đặt vào thư mục phù hợp.

### Memory issues với video lớn
Giảm `--segment-duration` để cắt video thành các segment nhỏ hơn.

## License

MIT License


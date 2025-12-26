# System K Vehicle Counting Tool - Web Interface

## Giới thiệu

Web interface cho phép bạn:
- Upload video trực tiếp trên trình duyệt
- Vẽ ROI và Counting Line trực tiếp trên màn hình
- Xem tiến trình xử lý real-time
- Xem kết quả đếm xe ngay trên web

## Cài đặt

### 1. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 2. Chạy web server
```bash
python3 web_app.py
```

### 3. Mở trình duyệt
Truy cập: http://localhost:5000

## Hướng dẫn sử dụng

### Bước 1: Upload Video
1. Click vào vùng upload hoặc kéo thả file video
2. Hệ thống sẽ tự động extract frame đầu tiên để preview
3. Chờ upload hoàn tất

### Bước 2: Cấu hình ROI và Counting Line
1. **Vẽ ROI (Region of Interest)**:
   - Chọn "Draw ROI"
   - Click trên canvas để vẽ polygon (ít nhất 3 điểm)
   - Vùng ngoài ROI sẽ bị bôi đen

2. **Vẽ Counting Line**:
   - Chọn "Draw Counting Line"
   - Click 2 điểm để vẽ đường đếm xe
   - Xe vượt qua đường này sẽ được đếm

3. **Lưu cấu hình**:
   - Click "Save Config" để lưu
   - Hoặc "Load Config" để tải cấu hình đã lưu

### Bước 3: Xử lý Video
1. Điều chỉnh "Segment Duration" (thời gian mỗi segment)
2. Click "Start Processing"
3. Theo dõi tiến trình real-time:
   - Progress bar hiển thị %
   - Current step hiển thị bước đang xử lý
   - Status message hiển thị thông báo

### Bước 4: Xem Kết quả
1. Kết quả tự động cập nhật sau khi xử lý xong
2. Hiển thị:
   - Count Up: Số xe đi lên
   - Count Down: Số xe đi xuống
   - Total: Tổng số xe

## API Endpoints

### POST /api/upload
Upload video file
- Form data: `video` (file)

### POST /api/save-config
Lưu ROI config
- JSON body: `{roi: {...}, counting_line: {...}, vehicle_classes: [...]}`

### GET /api/load-config
Load ROI config hiện tại

### POST /api/process
Bắt đầu xử lý video
- JSON body: `{filename: "...", segment_duration: 300}`

### GET /api/status
Lấy trạng thái xử lý
- Returns: `{is_processing: bool, progress: int, message: str, current_step: str}`

### GET /api/results
Lấy kết quả đếm xe
- Returns: `{summary: {...}, recent_results: [...]}`

## Tính năng

- ✅ Upload video drag & drop
- ✅ Preview frame đầu tiên
- ✅ Vẽ ROI trực tiếp trên canvas
- ✅ Vẽ Counting Line trực tiếp
- ✅ Real-time progress tracking
- ✅ Auto-refresh results
- ✅ Responsive design
- ✅ Error handling

## Troubleshooting

### Lỗi "python not found" hoặc "Command 'python' not found"
Hệ thống của bạn sử dụng `python3` thay vì `python`. Có 2 cách:

**Cách 1: Sử dụng python3 trực tiếp**
```bash
python3 web_app.py
```

**Cách 2: Sử dụng script helper**
```bash
./start_web.sh
```

### Port 5000 đã được sử dụng
Thay đổi port trong `web_app.py`:
```python
app.run(host='0.0.0.0', port=8080, debug=True)
```

### Video upload bị lỗi
- Kiểm tra kích thước file (max 500MB)
- Kiểm tra format video (MP4, AVI, MOV, MKV, FLV)

### Canvas không hiển thị
- Kiểm tra console browser (F12) để xem lỗi
- Đảm bảo frame preview đã được extract

### Processing bị lỗi
- Kiểm tra logs trong terminal
- Đảm bảo FFmpeg đã được cài đặt
- Kiểm tra YOLO model đã được download

## Lưu ý

- Web interface chạy trên localhost (chỉ truy cập được từ máy local)
- Để truy cập từ máy khác, thay đổi `host='0.0.0.0'` (đã có sẵn)
- Video lớn sẽ mất thời gian xử lý, vui lòng đợi
- Kết quả được lưu vào database và có thể export ra JSON/CSV


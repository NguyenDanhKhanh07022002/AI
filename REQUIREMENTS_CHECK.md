# Kiểm tra yêu cầu từ Annotation作業説明

## Yêu cầu từ file Excel

### 1. 動画ファイルのチェック (Video file check)
- ✅ Check ảnh có trùng với hôm trước không → **ĐÃ CÓ** (duplicate_detection.py)
- ✅ Check camera có bị lệch không → **ĐÃ CÓ** (camera_shift_detection.py)
- ❌ **THIẾU**: Memo lại kết quả check (ghi chú thời gian, vị trí)

### 2. ffmpegを使った動画ファイル切り取り (Video cutting)
- ✅ Cắt video bằng FFmpeg → **ĐÃ CÓ** (video_segmentation.py)
- ❌ **THIẾU**: Cắt dựa trên memo (cắt phần trùng với hôm trước)
- ❌ **THIẾU**: Cắt khi camera góc thay đổi (dựa trên camera shift detection)
- ❌ **THIẾU**: Luôn cắt từ 5 phút trở đi (mặc định)

### 3. 画像化 (Image conversion)
- ✅ Extract frames từ video → **ĐÃ CÓ** (image_extraction.py)
- ✅ Extract theo time interval → **ĐÃ CÓ** (extract_frames_by_time_interval)
- ✅ Bôi đen phần thừa → **ĐÃ CÓ** (roi_processing.py)
- ✅ Vẽ ROI trên màn hình → **ĐÃ CÓ** (roi_selector.py, web interface)

## Tổng kết

**Đã có:**
- ✅ Video segmentation (FFmpeg)
- ✅ Image extraction với time interval
- ✅ ROI masking
- ✅ Duplicate detection
- ✅ Camera shift detection
- ✅ Web interface

**Còn thiếu:**
- ❌ Memo system (ghi chú kết quả check)
- ❌ Smart video cutting (dựa trên memo và camera shift)
- ❌ Default cut từ 5 phút trở đi
- ❌ Workflow tự động hóa toàn bộ quy trình


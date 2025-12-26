# Simple Mode - Chỉ Extract và Bôi Đen Ảnh

## Mục đích

Tool này có 2 mode:
1. **Simple Mode**: Chỉ extract ảnh và bôi đen (không đếm xe) - **MỤC ĐÍCH CHÍNH**
2. **Full Mode**: Extract + bôi đen + đếm xe (nếu YOLO hoạt động)

## Simple Mode - Command Line

Sử dụng script `simple_image_extractor.py`:

```bash
python3 simple_image_extractor.py --video path/to/video.mkv --output extracted_images --interval 300
```

### Các tham số:
- `--video`: Đường dẫn video (bắt buộc)
- `--output`: Thư mục lưu ảnh (default: `extracted_images`)
- `--interval`: Khoảng thời gian giữa các frame (giây, default: 300 = 5 phút)
- `--config`: Đường dẫn config ROI (default: `config/roi_config.json`)
- `--no-duplicate-check`: Tắt check duplicate
- `--no-camera-shift-check`: Tắt check camera shift

### Ví dụ:

```bash
# Extract ảnh mỗi 5 phút
python3 simple_image_extractor.py --video camera4_part2.mkv --interval 300

# Extract ảnh mỗi 1 phút
python3 simple_image_extractor.py --video camera4_part2.mkv --interval 60

# Extract ảnh mỗi 5 phút, không check duplicate
python3 simple_image_extractor.py --video camera4_part2.mkv --interval 300 --no-duplicate-check
```

## Simple Mode - Web Interface

Web interface đã được cập nhật để:
1. **Luôn lưu ảnh đã được bôi đen** vào `data/processed_images/`
2. Vehicle counting là tùy chọn (chỉ chạy nếu YOLO hoạt động)

### Workflow trên Web:

1. Upload video
2. Vẽ ROI (vùng cần bôi đen)
3. Vẽ Counting Line (tùy chọn, chỉ cần nếu muốn đếm xe)
4. Set "Save Frames Interval" (ví dụ: 300 = mỗi 5 phút)
5. Click "Start Processing"
6. **Ảnh đã được bôi đen sẽ được lưu vào `data/processed_images/`**

## Output

### Thư mục output:
- `data/processed_images/`: **Ảnh đã được bôi đen** (mục đích chính)
- `data/frames/`: Frames gốc (tạm thời, có thể xóa sau)
- `data/output/`: Video segments (tạm thời)

### Format tên file:
```
{video_name}_processed_time_{timestamp}s_{frame_number}.jpg
```

Ví dụ: `camera4_part2_processed_time_000300s_0000.jpg`

## Lưu ý

- **Ảnh được lưu ngay sau khi apply ROI mask**, không phụ thuộc vào vehicle detection
- Nếu YOLO không hoạt động, tool vẫn lưu ảnh bình thường
- Vehicle counting chỉ là tính năng bổ sung, không bắt buộc


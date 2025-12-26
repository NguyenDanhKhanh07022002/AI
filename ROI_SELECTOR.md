# ROI Selector Tool

Tool để vẽ ROI (vùng cần bôi đen) trực tiếp trên video frame và extract frames với mask đã áp dụng.

## Tính năng

- ✅ Hiển thị frame đầu tiên của video
- ✅ Vẽ ROI bằng cách click và kéo chuột
- ✅ Hỗ trợ nhiều vùng ROI
- ✅ Extract frames từ video với interval tùy chỉnh
- ✅ Tự động áp dụng mask (bôi đen) các vùng đã chọn
- ✅ Lưu config ROI ra file JSON

## Cài đặt

Không cần cài đặt thêm, chỉ cần:
- Python 3.8+
- OpenCV (`pip install opencv-python`)

## Sử dụng

### Basic usage

```bash
python3 roi_selector.py --video path/to/video.mp4
```

### Với các tùy chọn

```bash
python3 roi_selector.py \
    --video path/to/video.mp4 \
    --output extracted_images \
    --interval 300 \
    --width 1280 \
    --height 720 \
    --save-config roi_config.json
```

### Các tham số

- `--video`: Đường dẫn đến video file (bắt buộc)
- `--output`: Thư mục lưu frames đã extract (mặc định: `extracted_images`)
- `--interval`: Khoảng thời gian giữa các frame (giây, mặc định: 300 = 5 phút)
- `--width`: Chiều rộng cửa sổ hiển thị (mặc định: 1280)
- `--height`: Chiều cao cửa sổ hiển thị (mặc định: 720)
- `--save-config`: Lưu ROI config vào file JSON (tùy chọn)

## Hướng dẫn sử dụng

1. **Chạy script** với video của bạn
2. **Cửa sổ hiển thị** sẽ mở với frame đầu tiên
3. **Vẽ ROI**:
   - Click và kéo chuột để vẽ hình chữ nhật
   - Vùng này sẽ bị bôi đen trong frames đã extract
   - Có thể vẽ nhiều vùng
4. **Điều khiển**:
   - Nhấn phím bất kỳ để hoàn tất và bắt đầu extract
   - Nhấn `r` để reset (xóa tất cả vùng đã vẽ)
   - Nhấn `q` hoặc `ESC` để thoát
5. **Frames sẽ được extract** với mask đã áp dụng

## Ví dụ

### Extract frames mỗi 5 phút

```bash
python3 roi_selector.py --video camera4_part2.mkv --interval 300
```

### Extract frames mỗi 1 phút và lưu config

```bash
python3 roi_selector.py \
    --video camera4_part2.mkv \
    --interval 60 \
    --save-config my_roi_config.json
```

### Extract tất cả frames (interval = 0)

```bash
python3 roi_selector.py --video camera4_part2.mkv --interval 0
```

## Output

- **Frames**: Được lưu trong thư mục `extracted_images/` (hoặc thư mục bạn chỉ định)
- **Format**: `image_000.jpg`, `image_001.jpg`, ...
- **Config**: Nếu sử dụng `--save-config`, file JSON sẽ chứa ROI config

## Lưu ý

- Frame đầu tiên được dùng để vẽ ROI
- Tọa độ ROI được lưu theo resolution gốc của video
- Frames được extract với mask đã áp dụng (các vùng ROI đã bị bôi đen)
- Nếu không vẽ ROI nào, frames sẽ được extract mà không có mask

## Tích hợp với System K Tool

Config được lưu có thể được sử dụng với System K Vehicle Counting Tool:

```bash
# Sử dụng config đã lưu
python3 src/main.py --video video.mp4 --config my_roi_config.json
```


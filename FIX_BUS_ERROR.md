# Fix Bus Error với PyTorch/YOLO

## Vấn đề

Khi click "Start Processing", chương trình bị dừng do Bus error khi load YOLO model. Đây là vấn đề tương thích giữa PyTorch và hệ thống.

## Giải pháp

### Giải pháp 1: Cài CPU-only PyTorch (Khuyến nghị)

Gỡ PyTorch hiện tại và cài CPU-only version:

```bash
# Gỡ PyTorch hiện tại
pip3 uninstall torch torchvision

# Cài CPU-only version
pip3 install --user torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### Giải pháp 2: Sử dụng Docker

Chạy trong container với môi trường đã cấu hình sẵn.

### Giải pháp 3: Tạm thời bỏ qua YOLO

Code đã được cập nhật để xử lý trường hợp YOLO không hoạt động. Web app vẫn chạy được nhưng không có vehicle detection.

## Kiểm tra

Sau khi cài CPU-only PyTorch, test lại:

```bash
python3 test_yolo_safe.py
```

Nếu không còn Bus error, web app sẽ hoạt động bình thường.

## Lưu ý

- CPU-only PyTorch sẽ chậm hơn nhưng ổn định hơn
- Nếu có GPU, có thể cần cài CUDA-compatible version phù hợp với hệ thống
- Bus error thường xảy ra do conflict giữa CUDA libraries và hệ thống


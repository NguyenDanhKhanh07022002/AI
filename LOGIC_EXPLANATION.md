# Logic Hiện Tại của Tool

## 1. Workflow Xử Lý Video

```
1. Upload video
   ↓
2. Kiểm tra độ dài video
   ├─ Nếu video < 5 phút: Xử lý trực tiếp từ đầu
   └─ Nếu video ≥ 5 phút: Cắt từ 5 phút trở đi (segment)
   ↓
3. Extract frames theo time interval (ví dụ: mỗi 5 phút)
   ↓
4. Với mỗi frame:
   ├─ Check duplicate (bỏ qua nếu trùng)
   ├─ Check camera shift (lưu memo nếu lệch)
   ├─ Apply ROI mask (bôi đen phần thừa) ← QUAN TRỌNG
   ├─ Lưu ảnh đã bôi đen vào data/processed_images/
   └─ [Tùy chọn] Vehicle detection & counting (nếu YOLO hoạt động)
   ↓
5. Export kết quả
```

## 2. Logic Bôi Đen ROI

### Cách hoạt động:

1. **ROI (Region of Interest)**: Vùng bạn VẼ trên ảnh = Vùng được GIỮ LẠI (không bị bôi đen)

2. **Phần ngoài ROI**: Tự động bị BÔI ĐEN (màu đen [0,0,0])

### Ví dụ:

```
Ảnh gốc:
┌─────────────────┐
│  Phần trên      │ ← Sẽ bị bôi đen (ngoài ROI)
│  (cần bôi đen)  │
├─────────────────┤
│  Phần dưới      │ ← Được giữ lại (trong ROI)
│  (cần giữ lại)  │
└─────────────────┘

ROI polygon vẽ ở phần dưới:
┌─────────────────┐
│  ███████████████│ ← Bôi đen (ngoài ROI)
│  ███████████████│
├─────────────────┤
│  ┌───────────┐  │ ← ROI polygon (giữ lại)
│  │ Phần dưới │  │
│  └───────────┘  │
└─────────────────┘
```

### Code Logic:

```python
# 1. Tạo mask: vùng ROI = 255 (giữ lại), ngoài ROI = 0
mask = np.zeros(image.shape[:2], dtype=np.uint8)
cv2.fillPoly(mask, [roi_points], 255)  # Vùng ROI = 255

# 2. Invert mask: vùng ngoài ROI = 255 (sẽ bôi đen)
mask_inv = cv2.bitwise_not(mask)  # 255 → 0, 0 → 255

# 3. Áp dụng: nơi nào mask_inv > 0 thì bôi đen
masked_image[:, :, c] = np.where(
    mask_inv > 0,  # Nếu ngoài ROI
    mask_color[c],  # → Bôi đen
    masked_image[:, :, c]  # Nếu trong ROI → Giữ nguyên
)
```

## 3. Vị Trí Lưu Ảnh

### Thư mục output:
- **Path**: `data/processed_images/`
- **Full path**: `/home/khanhnd4/AI/data/processed_images/`

### Format tên file:
```
{video_name}_processed_time_{timestamp}s_{frame_number}.jpg
```

Ví dụ:
```
camera4_part2_processed_time_000300s_0000.jpg
camera4_part2_processed_time_000600s_0001.jpg
```

## 4. Cách Vẽ ROI Đúng

### Để bôi đen phần trên, giữ lại phần dưới:

1. **Vẽ polygon ở phần DƯỚI** (phần cần giữ lại)
2. **Không vẽ ở phần trên** (phần sẽ tự động bị bôi đen)

### Ví dụ vẽ ROI:

```
Ảnh preview:
┌─────────────────┐
│  Phần trên      │ ← Không vẽ ROI ở đây
│  (sẽ bị bôi đen)│
├─────────────────┤
│  Click điểm 1   │ ← Bắt đầu vẽ ROI ở đây
│  Click điểm 2   │
│  Click điểm 3   │ ← Vẽ polygon bao quanh phần dưới
│  Click điểm 4   │
│  (phần giữ lại) │
└─────────────────┘
```

## 5. Kiểm Tra Kết Quả

### Trong log:
```
✓ Saved processed image: filename.jpg | Blackout ratio: X% (Y/Z pixels)
```

- **Blackout ratio > 0%**: Ảnh đã được bôi đen
- **Blackout ratio = 0%**: Ảnh chưa được bôi đen (có thể ROI chưa đúng)

### Xem ảnh output:
1. **Thư mục**: `data/processed_images/`
2. **Web API**: `http://localhost:5000/api/list_processed_images`
3. **Xem trực tiếp**: `http://localhost:5000/api/processed_images/<filename>`

## 6. Vấn Đề Thường Gặp

### ROI không hoạt động (Blackout ratio = 0%):

**Nguyên nhân có thể:**
1. ROI points quá nhỏ so với ảnh
2. ROI points nằm ngoài bounds của ảnh
3. ROI points có điểm trùng lặp
4. ROI được vẽ trên canvas nhỏ nhưng ảnh thực tế lớn hơn

**Giải pháp:**
- Code đã tự động loại bỏ điểm trùng lặp
- Code đã tự động clip points vào bounds của ảnh
- Đảm bảo vẽ ROI trên preview frame có kích thước đúng

## 7. Cải Tiến Đã Thêm

1. ✅ Loại bỏ điểm trùng lặp trong ROI points
2. ✅ Đảm bảo points nằm trong bounds của ảnh
3. ✅ Logging chi tiết để debug
4. ✅ Kiểm tra blackout ratio sau khi lưu
5. ✅ Error handling khi apply ROI mask
6. ✅ Hỗ trợ video ngắn hơn 5 phút


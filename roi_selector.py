#!/usr/bin/env python3
"""
ROI Selector Tool
Tool để vẽ ROI (vùng cần bôi đen) trực tiếp trên video frame
Sau đó extract frames với mask đã áp dụng
"""
import cv2
import os
import argparse
from pathlib import Path


class ROISelector:
    """Tool để chọn ROI bằng cách vẽ trên frame"""
    
    def __init__(self, video_path, output_dir='extracted_images', window_width=1280, window_height=720):
        """
        Khởi tạo ROI Selector
        
        Args:
            video_path: Đường dẫn đến video
            output_dir: Thư mục lưu frames đã extract
            window_width: Chiều rộng cửa sổ hiển thị
            window_height: Chiều cao cửa sổ hiển thị
        """
        self.video_path = video_path
        self.output_dir = output_dir
        self.window_width = window_width
        self.window_height = window_height
        
        # Mask regions (lưu theo tọa độ gốc)
        self.mask_regions = []
        self.drawing = False
        self.ix, self.iy = -1, -1
        self.temp_frame_display = None
        self.scale_x = 1.0
        self.scale_y = 1.0
        
        # Tạo output directory
        os.makedirs(output_dir, exist_ok=True)
    
    def draw_rectangle(self, event, x, y, flags, param):
        """Callback function cho mouse events"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.ix, self.iy = x, y
        
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                # Vẽ preview rectangle
                temp = self.temp_frame_display.copy()
                cv2.rectangle(temp, (self.ix, self.iy), (x, y), (0, 0, 255), 2)
                cv2.imshow('Select Mask Regions', temp)
        
        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            # Chuyển từ tọa độ hiển thị về tọa độ gốc
            x1_orig = int(self.ix / self.scale_x)
            y1_orig = int(self.iy / self.scale_y)
            x2_orig = int(x / self.scale_x)
            y2_orig = int(y / self.scale_y)
            
            # Đảm bảo x1 < x2 và y1 < y2
            x1_orig, x2_orig = min(x1_orig, x2_orig), max(x1_orig, x2_orig)
            y1_orig, y2_orig = min(y1_orig, y2_orig), max(y1_orig, y2_orig)
            
            self.mask_regions.append((x1_orig, y1_orig, x2_orig, y2_orig))
            cv2.rectangle(self.temp_frame_display, (self.ix, self.iy), (x, y), (0, 0, 0), 2)
            print(f"Added mask region: ({x1_orig}, {y1_orig}) -> ({x2_orig}, {y2_orig})")
    
    def select_roi(self):
        """Hiển thị frame đầu tiên và cho phép người dùng vẽ ROI"""
        # Đọc video và lấy frame đầu tiên
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            raise ValueError(f"Không thể mở video: {self.video_path}")
        
        ret, first_frame = cap.read()
        cap.release()
        
        if first_frame is None:
            raise ValueError("Không thể đọc frame đầu tiên từ video")
        
        # Lưu kích thước gốc
        orig_height, orig_width = first_frame.shape[:2]
        
        # Tính scale factor
        self.scale_x = self.window_width / orig_width
        self.scale_y = self.window_height / orig_height
        
        # Resize để hiển thị
        self.temp_frame_display = cv2.resize(first_frame.copy(), (self.window_width, self.window_height))
        
        # Tạo window và set mouse callback
        cv2.namedWindow('Select Mask Regions', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Select Mask Regions', self.window_width, self.window_height)
        cv2.setMouseCallback('Select Mask Regions', self.draw_rectangle)
        
        print("=" * 60)
        print("HƯỚNG DẪN:")
        print("- Click và kéo chuột để vẽ vùng cần bôi đen")
        print("- Có thể vẽ nhiều vùng")
        print("- Nhấn phím bất kỳ để hoàn tất")
        print("- Nhấn 'r' để reset (xóa tất cả vùng đã vẽ)")
        print("- Nhấn 'q' hoặc ESC để thoát")
        print("=" * 60)
        
        while True:
            cv2.imshow('Select Mask Regions', self.temp_frame_display)
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == 27:  # ESC
                print("Đã hủy")
                cv2.destroyAllWindows()
                return False
            elif key == ord('r'):
                # Reset
                self.mask_regions = []
                self.temp_frame_display = cv2.resize(first_frame.copy(), (self.window_width, self.window_height))
                print("Đã reset tất cả vùng")
            elif key != 255 and key != -1:  # Bất kỳ phím nào khác
                break
        
        cv2.destroyAllWindows()
        
        if len(self.mask_regions) == 0:
            print("Cảnh báo: Chưa vẽ vùng nào. Tiếp tục mà không có mask.")
        
        return True
    
    def extract_frames(self, interval_sec=300):
        """
        Extract frames từ video với mask đã áp dụng
        
        Args:
            interval_sec: Khoảng thời gian giữa các frame (giây), mặc định 300s (5 phút)
        """
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            raise ValueError(f"Không thể mở video: {self.video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = frame_count / fps
        
        print(f"\nVideo info:")
        print(f"  FPS: {fps:.2f}")
        print(f"  Total frames: {frame_count}")
        print(f"  Duration: {duration_sec:.2f} seconds ({duration_sec/60:.2f} minutes)")
        print(f"  Extract interval: {interval_sec} seconds")
        
        frame_interval = int(fps * interval_sec)
        frame_idx = 0
        image_idx = 0
        
        print(f"\nBắt đầu extract frames...")
        
        while True:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # Áp dụng mask (bôi đen các vùng đã chọn)
            for (x1, y1, x2, y2) in self.mask_regions:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), -1)
            
            # Lưu frame
            output_path = os.path.join(self.output_dir, f'image_{image_idx:03d}.jpg')
            cv2.imwrite(output_path, frame)
            
            image_idx += 1
            frame_idx += frame_interval
            
            if image_idx % 10 == 0:
                print(f"  Đã extract {image_idx} frames...")
        
        cap.release()
        
        print(f"\n✓ Hoàn tất! Đã extract {image_idx} frames")
        print(f"  Lưu tại: {os.path.abspath(self.output_dir)}")
        
        return image_idx
    
    def save_config(self, config_path='roi_config.json'):
        """Lưu ROI config ra file JSON"""
        # Chuyển đổi mask_regions thành polygon format
        roi_points = []
        for (x1, y1, x2, y2) in self.mask_regions:
            # Tạo polygon từ rectangle
            roi_points.append([[x1, y1], [x2, y1], [x2, y2], [x1, y2]])
        
        # Nếu có nhiều regions, combine thành một polygon lớn
        if len(roi_points) > 0:
            # Flatten tất cả points
            all_points = []
            for poly in roi_points:
                all_points.extend(poly)
            
            config = {
                "roi": {
                    "type": "polygon",
                    "points": all_points,
                    "mask_color": [0, 0, 0]
                },
                "counting_line": {
                    "type": "line",
                    "start": [0, 0],
                    "end": [100, 100],
                    "direction": "vertical"
                },
                "vehicle_classes": ["car", "truck", "bus", "motorcycle"]
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print(f"\n✓ Đã lưu config vào: {config_path}")
            return True
        
        return False


def main():
    parser = argparse.ArgumentParser(description='ROI Selector Tool - Vẽ ROI và extract frames')
    parser.add_argument('--video', type=str, required=True, help='Đường dẫn đến video file')
    parser.add_argument('--output', type=str, default='extracted_images', help='Thư mục lưu frames (default: extracted_images)')
    parser.add_argument('--interval', type=int, default=300, help='Khoảng thời gian giữa các frame (giây, default: 300 = 5 phút)')
    parser.add_argument('--width', type=int, default=1280, help='Chiều rộng cửa sổ hiển thị (default: 1280)')
    parser.add_argument('--height', type=int, default=720, help='Chiều cao cửa sổ hiển thị (default: 720)')
    parser.add_argument('--save-config', type=str, default=None, help='Lưu ROI config vào file JSON (optional)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.video):
        print(f"Lỗi: Video không tồn tại: {args.video}")
        return 1
    
    try:
        # Tạo ROI selector
        selector = ROISelector(
            video_path=args.video,
            output_dir=args.output,
            window_width=args.width,
            window_height=args.height
        )
        
        # Chọn ROI
        if not selector.select_roi():
            print("Đã hủy bỏ")
            return 0
        
        print(f"\nĐã chọn {len(selector.mask_regions)} vùng mask")
        
        # Extract frames
        selector.extract_frames(interval_sec=args.interval)
        
        # Lưu config nếu được yêu cầu
        if args.save_config:
            selector.save_config(args.save_config)
        
        return 0
        
    except Exception as e:
        print(f"Lỗi: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())


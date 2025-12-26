"""
Memo System
Ghi chú kết quả check video: duplicate và camera shift
"""
import sqlite3
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def initialize_memo_database(db_path: str):
    """Khởi tạo database cho memo system"""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Table video_checks: Lưu kết quả check video
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS video_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_path TEXT NOT NULL,
            check_date TEXT NOT NULL,
            check_type TEXT NOT NULL,
            start_time REAL,
            end_time REAL,
            description TEXT,
            status TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    # Table duplicate_segments: Lưu các đoạn video trùng với hôm trước
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS duplicate_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_path TEXT NOT NULL,
            start_time REAL NOT NULL,
            end_time REAL NOT NULL,
            matched_video_path TEXT,
            description TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    # Table camera_shift_points: Lưu các điểm camera bị lệch
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS camera_shift_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_path TEXT NOT NULL,
            shift_time REAL NOT NULL,
            shift_x REAL,
            shift_y REAL,
            rotation REAL,
            description TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_video_path ON video_checks(video_path)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_check_date ON video_checks(check_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_duplicate_video ON duplicate_segments(video_path)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shift_video ON camera_shift_points(video_path)')
    
    conn.commit()
    conn.close()
    logger.info(f"Memo database initialized: {db_path}")


def save_duplicate_memo(
    db_path: str,
    video_path: str,
    start_time: float,
    end_time: float,
    matched_video_path: Optional[str] = None,
    description: Optional[str] = None
):
    """
    Lưu memo về đoạn video trùng với hôm trước
    
    Args:
        db_path: Đường dẫn database
        video_path: Đường dẫn video hiện tại
        start_time: Thời gian bắt đầu đoạn trùng (giây)
        end_time: Thời gian kết thúc đoạn trùng (giây)
        matched_video_path: Đường dẫn video trùng (nếu có)
        description: Mô tả
    """
    if not os.path.exists(db_path):
        initialize_memo_database(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    created_at = datetime.now().isoformat()
    
    try:
        cursor.execute('''
            INSERT INTO duplicate_segments 
            (video_path, start_time, end_time, matched_video_path, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (video_path, start_time, end_time, matched_video_path, description, created_at))
        
        conn.commit()
        logger.info(f"Saved duplicate memo: {video_path} [{start_time:.2f}s - {end_time:.2f}s]")
    except Exception as e:
        logger.error(f"Error saving duplicate memo: {e}")
    finally:
        conn.close()


def save_camera_shift_memo(
    db_path: str,
    video_path: str,
    shift_time: float,
    shift_x: float,
    shift_y: float,
    rotation: float,
    description: Optional[str] = None
):
    """
    Lưu memo về điểm camera bị lệch
    
    Args:
        db_path: Đường dẫn database
        video_path: Đường dẫn video
        shift_time: Thời gian camera bị lệch (giây)
        shift_x: Độ lệch X
        shift_y: Độ lệch Y
        rotation: Góc xoay
        description: Mô tả
    """
    if not os.path.exists(db_path):
        initialize_memo_database(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    created_at = datetime.now().isoformat()
    
    try:
        cursor.execute('''
            INSERT INTO camera_shift_points 
            (video_path, shift_time, shift_x, shift_y, rotation, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (video_path, shift_time, shift_x, shift_y, rotation, description, created_at))
        
        conn.commit()
        logger.info(f"Saved camera shift memo: {video_path} at {shift_time:.2f}s")
    except Exception as e:
        logger.error(f"Error saving camera shift memo: {e}")
    finally:
        conn.close()


def get_duplicate_segments(db_path: str, video_path: str) -> List[Dict]:
    """
    Lấy danh sách các đoạn video trùng
    
    Args:
        db_path: Đường dẫn database
        video_path: Đường dẫn video
    
    Returns:
        List[Dict]: Danh sách các đoạn trùng
    """
    if not os.path.exists(db_path):
        return []
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT start_time, end_time, matched_video_path, description
            FROM duplicate_segments
            WHERE video_path = ?
            ORDER BY start_time
        ''', (video_path,))
        
        rows = cursor.fetchall()
        return [
            {
                'start_time': row[0],
                'end_time': row[1],
                'matched_video_path': row[2],
                'description': row[3]
            }
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Error getting duplicate segments: {e}")
        return []
    finally:
        conn.close()


def get_camera_shift_points(db_path: str, video_path: str) -> List[Dict]:
    """
    Lấy danh sách các điểm camera bị lệch
    
    Args:
        db_path: Đường dẫn database
        video_path: Đường dẫn video
    
    Returns:
        List[Dict]: Danh sách các điểm lệch
    """
    if not os.path.exists(db_path):
        return []
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT shift_time, shift_x, shift_y, rotation, description
            FROM camera_shift_points
            WHERE video_path = ?
            ORDER BY shift_time
        ''', (video_path,))
        
        rows = cursor.fetchall()
        return [
            {
                'shift_time': row[0],
                'shift_x': row[1],
                'shift_y': row[2],
                'rotation': row[3],
                'description': row[4]
            }
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Error getting camera shift points: {e}")
        return []
    finally:
        conn.close()


def generate_cut_plan(
    db_path: str,
    video_path: str,
    video_duration: float,
    min_start_time: float = 300.0
) -> List[Tuple[float, float]]:
    """
    Tạo kế hoạch cắt video dựa trên memo
    
    Args:
        db_path: Đường dẫn database
        video_path: Đường dẫn video
        video_duration: Độ dài video (giây)
        min_start_time: Thời gian bắt đầu tối thiểu (mặc định 300s = 5 phút)
    
    Returns:
        List[Tuple[float, float]]: List các đoạn cần cắt (start_time, end_time)
    """
    duplicate_segments = get_duplicate_segments(db_path, video_path)
    shift_points = get_camera_shift_points(db_path, video_path)
    
    # Tạo list các điểm cần cắt
    cut_points = [min_start_time]  # Luôn bắt đầu từ 5 phút
    
    # Thêm các điểm camera shift
    for shift in shift_points:
        cut_points.append(shift['shift_time'])
    
    # Thêm các điểm duplicate (bỏ qua các đoạn trùng)
    for dup in duplicate_segments:
        # Cắt trước đoạn trùng
        if dup['start_time'] > min_start_time:
            cut_points.append(dup['start_time'])
        # Cắt sau đoạn trùng
        if dup['end_time'] < video_duration:
            cut_points.append(dup['end_time'])
    
    # Sắp xếp và loại bỏ trùng lặp
    cut_points = sorted(set(cut_points))
    cut_points.append(video_duration)
    
    # Tạo các đoạn cắt
    segments = []
    for i in range(len(cut_points) - 1):
        start = cut_points[i]
        end = cut_points[i + 1]
        if end - start > 10:  # Chỉ cắt nếu đoạn > 10 giây
            segments.append((start, end))
    
    return segments


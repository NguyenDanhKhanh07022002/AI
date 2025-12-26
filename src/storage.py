"""
Module 9: Storage
Lưu kết quả vào SQLite, JSON, CSV
"""
import os
import sqlite3
import json
import csv
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def initialize_database(db_path: str):
    """Khởi tạo database với các tables cần thiết"""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Table counting_results
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS counting_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            video_path TEXT,
            frame_path TEXT,
            vehicle_count_up INTEGER DEFAULT 0,
            vehicle_count_down INTEGER DEFAULT 0,
            total_count INTEGER DEFAULT 0,
            frame_number INTEGER,
            created_at TEXT NOT NULL
        )
    ''')
    
    # Table camera_shifts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS camera_shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            frame_path TEXT NOT NULL,
            shift_x REAL,
            shift_y REAL,
            rotation REAL,
            is_shifted INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL,
            warning TEXT
        )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON counting_results(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_video_path ON counting_results(video_path)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_camera_timestamp ON camera_shifts(timestamp)')
    
    conn.commit()
    conn.close()
    logger.info(f"Database initialized: {db_path}")


def save_counting_result(
    db_path: str,
    video_path: Optional[str] = None,
    frame_path: Optional[str] = None,
    vehicle_count_up: int = 0,
    vehicle_count_down: int = 0,
    total_count: int = 0,
    frame_number: Optional[int] = None
):
    """
    Lưu kết quả đếm xe vào database
    
    Args:
        db_path: Đường dẫn đến database
        video_path: Đường dẫn video
        frame_path: Đường dẫn frame
        vehicle_count_up: Số xe đếm được chiều lên
        vehicle_count_down: Số xe đếm được chiều xuống
        total_count: Tổng số xe
        frame_number: Số thứ tự frame
    """
    if not os.path.exists(db_path):
        initialize_database(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    created_at = datetime.now().isoformat()
    
    try:
        cursor.execute('''
            INSERT INTO counting_results 
            (timestamp, video_path, frame_path, vehicle_count_up, vehicle_count_down, total_count, frame_number, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, video_path, frame_path, vehicle_count_up, vehicle_count_down, total_count, frame_number, created_at))
        
        conn.commit()
        logger.debug(f"Saved counting result: total={total_count}")
    except Exception as e:
        logger.error(f"Error saving counting result: {e}")
    finally:
        conn.close()


def save_camera_shift(
    db_path: str,
    frame_path: str,
    shift_x: float,
    shift_y: float,
    rotation: float,
    is_shifted: bool,
    warning: Optional[str] = None
):
    """
    Lưu thông tin camera shift vào database
    
    Args:
        db_path: Đường dẫn đến database
        frame_path: Đường dẫn frame
        shift_x: Độ lệch theo trục X
        shift_y: Độ lệch theo trục Y
        rotation: Góc xoay
        is_shifted: Có bị lệch không
        warning: Cảnh báo (nếu có)
    """
    if not os.path.exists(db_path):
        initialize_database(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    
    try:
        cursor.execute('''
            INSERT INTO camera_shifts 
            (frame_path, shift_x, shift_y, rotation, is_shifted, timestamp, warning)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (frame_path, shift_x, shift_y, rotation, 1 if is_shifted else 0, timestamp, warning))
        
        conn.commit()
        logger.debug(f"Saved camera shift: is_shifted={is_shifted}")
    except Exception as e:
        logger.error(f"Error saving camera shift: {e}")
    finally:
        conn.close()


def export_to_json(db_path: str, output_path: str, table: str = 'counting_results'):
    """
    Export dữ liệu từ database ra JSON
    
    Args:
        db_path: Đường dẫn đến database
        output_path: Đường dẫn file JSON output
        table: Tên table cần export
    """
    if not os.path.exists(db_path):
        logger.warning(f"Database not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute(f'SELECT * FROM {table}')
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        
        data = [dict(zip(columns, row)) for row in rows]
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported {len(data)} records to {output_path}")
    except Exception as e:
        logger.error(f"Error exporting to JSON: {e}")
    finally:
        conn.close()


def export_to_csv(db_path: str, output_path: str, table: str = 'counting_results'):
    """
    Export dữ liệu từ database ra CSV
    
    Args:
        db_path: Đường dẫn đến database
        output_path: Đường dẫn file CSV output
        table: Tên table cần export
    """
    if not os.path.exists(db_path):
        logger.warning(f"Database not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(f'SELECT * FROM {table}', conn)
        conn.close()
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8')
        
        logger.info(f"Exported {len(df)} records to {output_path}")
    except Exception as e:
        logger.error(f"Error exporting to CSV: {e}")


def get_counting_summary(db_path: str, video_path: Optional[str] = None) -> Dict:
    """
    Lấy tổng kết kết quả đếm xe
    
    Args:
        db_path: Đường dẫn đến database
        video_path: Đường dẫn video (None = tất cả videos)
    
    Returns:
        Dict: Summary với total counts
    """
    if not os.path.exists(db_path):
        return {'count_up': 0, 'count_down': 0, 'total': 0}
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        if video_path:
            cursor.execute('''
                SELECT SUM(vehicle_count_up), SUM(vehicle_count_down), SUM(total_count)
                FROM counting_results
                WHERE video_path = ?
            ''', (video_path,))
        else:
            cursor.execute('''
                SELECT SUM(vehicle_count_up), SUM(vehicle_count_down), SUM(total_count)
                FROM counting_results
            ''')
        
        result = cursor.fetchone()
        count_up = result[0] or 0
        count_down = result[1] or 0
        total = result[2] or 0
        
        return {
            'count_up': int(count_up),
            'count_down': int(count_down),
            'total': int(total)
        }
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        return {'count_up': 0, 'count_down': 0, 'total': 0}
    finally:
        conn.close()


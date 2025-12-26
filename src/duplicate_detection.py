"""
Module 4: Duplicate Detection
Kiểm tra ảnh có trùng với hôm trước không
"""
import os
import sqlite3
import imagehash
import logging
from PIL import Image
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def initialize_database(db_path: str):
    """Khởi tạo database nếu chưa tồn tại"""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Tạo table image_hashes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS image_hashes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            hash TEXT NOT NULL,
            date TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    
    # Tạo index để tăng tốc query
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_hash ON image_hashes(hash)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_date ON image_hashes(date)
    ''')
    
    conn.commit()
    conn.close()
    logger.info(f"Database initialized: {db_path}")


def calculate_image_hash(image_path: str) -> str:
    """
    Tính perceptual hash của ảnh
    
    Args:
        image_path: Đường dẫn đến ảnh
    
    Returns:
        str: Hash string
    """
    try:
        with Image.open(image_path) as img:
            # Sử dụng average hash (có thể thay bằng perceptual hash)
            hash_value = imagehash.average_hash(img)
            return str(hash_value)
    except Exception as e:
        logger.error(f"Error calculating hash for {image_path}: {e}")
        return ""


def check_duplicate(image_path: str, db_path: str, threshold: int = 5) -> Tuple[bool, Optional[str]]:
    """
    Kiểm tra ảnh có trùng với ảnh đã lưu không
    
    Args:
        image_path: Đường dẫn đến ảnh cần check
        db_path: Đường dẫn đến database
        threshold: Ngưỡng để coi là trùng (hamming distance)
    
    Returns:
        Tuple[bool, Optional[str]]: (is_duplicate, matched_hash)
    """
    if not os.path.exists(image_path):
        logger.warning(f"Image not found: {image_path}")
        return False, None
    
    # Khởi tạo database nếu chưa tồn tại
    if not os.path.exists(db_path):
        initialize_database(db_path)
    
    # Tính hash của ảnh hiện tại
    current_hash = calculate_image_hash(image_path)
    if not current_hash:
        return False, None
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Lấy tất cả hash từ database
        cursor.execute('SELECT hash, path FROM image_hashes')
        rows = cursor.fetchall()
        
        # So sánh với các hash đã lưu
        current_hash_obj = imagehash.hex_to_hash(current_hash)
        
        for stored_hash_str, stored_path in rows:
            stored_hash_obj = imagehash.hex_to_hash(stored_hash_str)
            hamming_distance = current_hash_obj - stored_hash_obj
            
            if hamming_distance <= threshold:
                logger.info(f"Duplicate found: {image_path} matches {stored_path} (distance: {hamming_distance})")
                conn.close()
                return True, stored_hash_str
        
        conn.close()
        return False, None
        
    except Exception as e:
        logger.error(f"Error checking duplicate: {e}")
        conn.close()
        return False, None


def save_image_hash(image_path: str, db_path: str):
    """
    Lưu hash của ảnh vào database
    
    Args:
        image_path: Đường dẫn đến ảnh
        db_path: Đường dẫn đến database
    """
    if not os.path.exists(image_path):
        logger.warning(f"Image not found: {image_path}")
        return
    
    # Khởi tạo database nếu chưa tồn tại
    if not os.path.exists(db_path):
        initialize_database(db_path)
    
    hash_value = calculate_image_hash(image_path)
    if not hash_value:
        return
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_timestamp = datetime.now().isoformat()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO image_hashes (path, hash, date, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (image_path, hash_value, current_date, current_timestamp))
        
        conn.commit()
        logger.debug(f"Saved hash for {image_path}")
        
    except Exception as e:
        logger.error(f"Error saving hash: {e}")
    finally:
        conn.close()


def get_images_by_date(db_path: str, date: str) -> list:
    """
    Lấy danh sách ảnh theo ngày
    
    Args:
        db_path: Đường dẫn đến database
        date: Ngày cần lấy (format: YYYY-MM-DD)
    
    Returns:
        list: Danh sách đường dẫn ảnh
    """
    if not os.path.exists(db_path):
        return []
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT path FROM image_hashes WHERE date = ?', (date,))
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    except Exception as e:
        logger.error(f"Error getting images by date: {e}")
        return []
    finally:
        conn.close()


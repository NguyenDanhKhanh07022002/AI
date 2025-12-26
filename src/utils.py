"""
Utility functions for System K Vehicle Counting Tool
"""
import os
import json
import logging
from datetime import datetime
from pathlib import Path


def setup_logging(log_level=logging.INFO):
    """Setup logging configuration"""
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('system_k.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def load_config(config_path):
    """Load JSON configuration file"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")


def create_directories(*dir_paths):
    """Create directories if they don't exist"""
    for dir_path in dir_paths:
        Path(dir_path).mkdir(parents=True, exist_ok=True)


def get_timestamp():
    """Get current timestamp as string"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def get_video_name(video_path):
    """Extract video name without extension from path"""
    return Path(video_path).stem


def validate_config(config):
    """Validate ROI configuration"""
    required_keys = ['roi', 'counting_line', 'vehicle_classes']
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required config key: {key}")
    
    # Validate ROI
    roi = config['roi']
    if 'type' not in roi or 'points' not in roi:
        raise ValueError("ROI config must have 'type' and 'points'")
    
    # Validate counting line
    counting_line = config['counting_line']
    if 'type' not in counting_line or 'start' not in counting_line or 'end' not in counting_line:
        raise ValueError("Counting line config must have 'type', 'start', and 'end'")
    
    return True


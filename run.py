#!/usr/bin/env python3
"""
Helper script to run System K Vehicle Counting Tool
This script ensures proper Python path setup
"""
import sys
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))

# Now import and run main
if __name__ == '__main__':
    from main import main
    main()


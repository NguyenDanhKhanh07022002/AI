#!/bin/bash
# Script helper để chạy web interface
# Tự động sử dụng python3

echo "Starting System K Vehicle Counting Tool - Web Interface"
echo "======================================================"

# Kiểm tra python3
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3.8+"
    exit 1
fi

# Chạy web app
python3 web_app.py


#!/bin/bash
# Quick Test Script for Mac/Linux
# Double-click this file or run: bash run_demo.sh

echo "==========================================="
echo "WeSi Chatbot - Quick Demo Launcher"
echo "==========================================="
echo ""
echo "Starting demo chatbot..."
echo ""

# Check if Python is available
if command -v python3 &> /dev/null; then
    python3 quick_test.py
elif command -v python &> /dev/null; then
    python quick_test.py
else
    echo "Error: Python is not installed or not in PATH"
    echo "Please install Python 3 from https://www.python.org/"
    exit 1
fi

@echo off
REM Quick Test Script for Windows
REM Double-click this file to run the demo

echo ===========================================
echo WeSi Chatbot - Quick Demo Launcher
echo ===========================================
echo.
echo Starting demo chatbot...
echo.

REM Try python3 first, then python
python3 quick_test.py 2>nul
if %errorlevel% neq 0 (
    python quick_test.py 2>nul
    if %errorlevel% neq 0 (
        echo Error: Python is not installed or not in PATH
        echo Please install Python 3 from https://www.python.org/
        pause
        exit /b 1
    )
)

pause

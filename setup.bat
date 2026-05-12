@echo off
title SOC Deadman Switch - Setup
color 0A

echo =============================================
echo  Visual SOC Deadman Switch - Environment Setup
echo =============================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found.
    echo Download Python 3.10 from https://python.org
    echo Make sure to check "Add Python to PATH" during install
    pause
    exit /b 1
)

echo [1/3] Creating virtual environment...
python -m venv venv

echo [2/3] Activating environment...
call venv\Scripts\activate.bat

echo [3/3] Installing all packages (no compiler required)...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo =============================================
echo  Setup complete - no errors expected.
echo  Now run: python test_camera.py
echo =============================================
pause
@echo off
chcp 65001 >nul
echo =================================================
echo       AI Grader - Assignment Grading System
echo =================================================
echo.
echo Starting GUI...
echo.

REM 查看是否存在虛擬環境
if not exist ".venv\Scripts\python.exe" (
    echo [WARNING] Virtual environment not found!
    echo Creating virtual environment automatically...
    echo.
    
    REM 建立虛擬環境
    python -m venv .venv
    
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment!
        echo Please ensure Python 3.x is installed
        echo.
        pause
        exit /b 1
    )
    
    echo Virtual environment created successfully!
    echo.
    echo Installing dependencies...
    echo.
    
    REM Install 依賴
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install dependencies!
        echo.
        pause
        exit /b 1
    )
    
    echo.
    echo =================================================
    echo                  Setup complete!
    echo =================================================
    echo.
)

REM cd 腳本目錄
cd /d "%~dp0"

REM 啟動 GUI
.venv\Scripts\python.exe ai_grader\gui_app.py

REM 查看 return 值
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] An error occurred while running the program!
    echo Exit code: %ERRORLEVEL%
    echo.
    pause
    exit /b %ERRORLEVEL%
)

REM 結束

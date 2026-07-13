@echo off
chcp 65001 >nul
title SBZ AI Video Studio
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [setup] Pehli dafa setup ho raha hai ^(thori der^)...
    python -m venv .venv
    call ".venv\Scripts\activate.bat"
    python -m pip install --upgrade pip >nul
    pip install -r requirements.txt
    echo [setup] Ho gaya!
) else (
    call ".venv\Scripts\activate.bat"
)

echo.
echo  Studio UI khul rahi hai: http://127.0.0.1:5050
echo  ^(band karne ke liye Ctrl+C^)
echo.
python app.py
pause

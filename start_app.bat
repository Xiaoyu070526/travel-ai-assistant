@echo off
chcp 65001 >nul
title Travel AI Assistant - Streamlit
cd /d "%~dp0"
echo [Travel AI] Starting Streamlit app...
echo.
python -m streamlit run src\app.py --server.port 8513
echo.
echo App closed. Press any key to exit...
pause >nul

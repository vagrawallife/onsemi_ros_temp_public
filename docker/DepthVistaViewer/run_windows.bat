@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
echo DepthVista Live Camera
echo Place DepthVistaSDK.dll and its dependent DLLs in: %~dp0
if not exist venv ( python -m venv venv )
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python depthvista_camera_live.py
endlocal

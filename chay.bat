@echo off
rem Chay app binh thuong, khong co cua so console.
setlocal
cd /d "%~dp0"

if not exist "venv\Scripts\pythonw.exe" call "%~dp0caidat.bat" im
if not exist "venv\Scripts\pythonw.exe" exit /b 1

start "" "venv\Scripts\pythonw.exe" clicker.py
exit /b 0

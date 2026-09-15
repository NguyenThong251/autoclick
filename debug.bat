@echo off
rem Chay app co console de thay loi ngay. Dung khi test.
rem AUTOCLICK_NO_RELAUNCH=1 giu app o python.exe, khong bo sang pythonw,
rem nho vay console con do ma doc traceback.
setlocal
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" call "%~dp0caidat.bat" im
if not exist "venv\Scripts\python.exe" exit /b 1

set AUTOCLICK_NO_RELAUNCH=1
"venv\Scripts\python.exe" clicker.py
echo.
echo App da thoat.
pause
exit /b 0

@echo off
rem Thu rieng phan chuot ao, khong dinh giao dien.
rem Script nay khong can thu vien ngoai nao, nen Python he thong cung chay duoc.
setlocal
cd /d "%~dp0"

set "PY="
if exist "venv\Scripts\python.exe" set "PY=venv\Scripts\python.exe"
if not defined PY (
    where py >nul 2>nul
    if not errorlevel 1 set "PY=py -3"
)
if not defined PY set "PY=python"

%PY% thu_chuot_ao.py
echo.
pause
exit /b 0

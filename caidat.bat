@echo off
rem Tao venv va cai thu vien. Chay lai luc nao cung duoc, da co thi bo qua.
setlocal
cd /d "%~dp0"

if exist "venv\Scripts\python.exe" (
    echo Da co venv roi.
    goto cai_thu_vien
)

echo Dang tao venv...
py -3 -m venv venv 2>nul
if not exist "venv\Scripts\python.exe" python -m venv venv
if not exist "venv\Scripts\python.exe" goto khong_co_python

:cai_thu_vien
echo Dang cai thu vien tu requirements.txt...
"venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto loi_pip

echo.
echo Xong. Chay app bang chay.bat
if "%~1"=="" pause
exit /b 0

:khong_co_python
echo.
echo Khong tim thay Python. Cai Python 3 tu python.org, nho tick "Add to PATH".
pause
exit /b 1

:loi_pip
echo.
echo Cai thu vien that bai. Xem thong bao loi o tren.
pause
exit /b 1

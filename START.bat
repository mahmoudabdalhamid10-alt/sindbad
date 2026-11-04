@echo off
setlocal
cd /d "%~dp0"
title Sindbad B2B Marketplace
where py >nul 2>nul
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")
%PY% --version >nul 2>nul
if errorlevel 1 (
 echo Python 3 is required. Install it from https://www.python.org/downloads/
 pause
 exit /b 1
)
if not exist "venv\Scripts\python.exe" (
 echo Creating virtual environment...
 %PY% -m venv venv
 if errorlevel 1 goto error
)
call "venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto error
python -m pip install -r requirements.txt
if errorlevel 1 goto error
echo.
echo Starting Sindbad at http://127.0.0.1:8000
start "" /b cmd /c "timeout /t 3 >nul & start http://127.0.0.1:8000"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
if errorlevel 1 goto error
exit /b 0
:error
echo.
echo Startup failed. Copy the error above and share it for troubleshooting.
pause

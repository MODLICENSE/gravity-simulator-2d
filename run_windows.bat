@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set PYTHON=py
) else (
    set PYTHON=python
)

%PYTHON% -m pip install -r requirements.txt
if errorlevel 1 goto :error

%PYTHON% app.py
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo Something went wrong. Make sure Python 3.10+ is installed and added to PATH.
pause
exit /b 1

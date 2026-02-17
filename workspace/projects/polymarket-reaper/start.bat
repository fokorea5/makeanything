@echo off
REM Polymarket Reaper Bot v1.1 -- Windows launcher
REM AC-38

REM ---------------------------------------------------------------
REM 1. Check Python 3.9+
REM ---------------------------------------------------------------
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do (
    set PYMAJOR=%%a
    set PYMINOR=%%b
)

if %PYMAJOR% LSS 3 (
    echo ERROR: Python 3.9+ is required. Found Python %PYVER%.
    pause
    exit /b 1
)
if %PYMAJOR%==3 if %PYMINOR% LSS 9 (
    echo ERROR: Python 3.9+ is required. Found Python %PYVER%.
    pause
    exit /b 1
)

echo Using Python %PYVER%

REM ---------------------------------------------------------------
REM 2. Install dependencies
REM ---------------------------------------------------------------
echo Installing dependencies...
python -m pip install -r requirements.txt --quiet

REM ---------------------------------------------------------------
REM 3. Start the bot
REM ---------------------------------------------------------------
echo Starting Polymarket Reaper Bot v1.1...
python src\main.py %*

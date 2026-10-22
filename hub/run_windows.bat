@echo off
setlocal
REM CA Knowledge Hub - Windows launcher
REM Double-click this file. It installs Python itself if missing (via winget),
REM sets up the environment, starts the app server, and opens your browser
REM automatically once the server is ready. Keep this window open while using
REM the app; closing it stops the app. Everything runs on this computer only.
REM Telemetry is disabled via .streamlit\config.toml (offline-first).
cd /d %~dp0
set PORT=8506

REM --- If the app is already running, just open the browser ---
powershell -NoProfile -Command "try { $c = New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1', %PORT%); $c.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    echo CA Knowledge Hub is already running. Opening it in your browser...
    start http://127.0.0.1:%PORT%
    exit /b 0
)

REM --- Find Python, installing it automatically if missing ---
set PY=
where py >nul 2>&1 && set PY=py -3
if not defined PY where python >nul 2>&1 && set PY=python
if not defined PY (
    echo Python not found. Installing it automatically via winget...
    winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements --silent
    if errorlevel 1 goto :nopython
    where py >nul 2>&1 && set PY=py -3
    if not defined PY where python >nul 2>&1 && set PY=python
    if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
if not defined PY goto :nopython
%PY% --version >nul 2>&1
if errorlevel 1 goto :nopython
goto :havepython

:nopython
echo Could not get Python working. Please install Python 3.10+ from https://www.python.org
echo ^(check "Add python.exe to PATH"^) and run this file again.
pause
exit /b 1

:havepython
REM --- Virtual environment (one shared venv for hub + all modules) ---
if not exist .venv (
    echo First run: creating isolated environment...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo Could not create the virtual environment.
        pause
        exit /b 1
    )
)
call .venv\Scripts\activate

REM --- Dependencies (only if streamlit is missing) ---
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies ^(needs internet; takes a few minutes on first run^)...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Dependency installation failed. Check your internet connection and try again.
        pause
        exit /b 1
    )
)

set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

REM --- First run: seed the module libraries (idempotent; skipped later) ---
if not exist "data\hub.db" (
    echo First run: building the module libraries ^(takes about a minute^)...
    python seed_all.py
    if errorlevel 1 (
        echo Library build failed. The app will retry it on startup.
    )
)

REM --- Helper script: open the browser the moment the server is ready ---
set "PS1=%TEMP%\ca_hub_open.ps1"
(
echo $t = 0
echo while ^($t -lt 180^) {
echo   try {
echo     $c = New-Object Net.Sockets.TcpClient
echo     $c.Connect^('127.0.0.1', %PORT%^)
echo     $c.Close^(^)
echo     Start-Process 'http://127.0.0.1:%PORT%'
echo     exit 0
echo   } catch { }
echo   Start-Sleep 1
echo   $t++
echo }
) > "%PS1%"
start "CA Knowledge Hub opener" /min powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"

echo.
echo Starting CA Knowledge Hub... your browser will open automatically when ready.
echo Keep this window open while using the app. Close it to stop the app.
echo.
python -m streamlit run app.py --server.headless true --server.port %PORT%
echo.
echo The app has stopped.
pause

@echo off
REM =====================================================================
REM  TACIT launcher (Windows)
REM  Just double-click this file. No command line knowledge needed.
REM
REM  NOTE FOR MAINTAINERS: keep this file ASCII-only.
REM  cmd.exe reads the .bat in the OEM codepage before "chcp 65001"
REM  takes effect, so Chinese text placed here can be mangled.
REM  All Chinese messages are printed by src\_launch_common.py instead.
REM =====================================================================
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "APP=src\app.py"
set "VENV=.venv"
set "STAMP=%VENV%\.deps_ok"

if not exist "%APP%" (
  echo.
  echo [ERROR] src\app.py not found.
  echo Please keep this launcher in the same folder as the program.
  echo.
  pause
  exit /b 1
)

REM --- 1. locate Python ------------------------------------------------
set "PY="
if exist "python\python.exe" set "PY=python\python.exe"
if not defined PY (
  py -3 --version >nul 2>&1 && set "PY=py -3"
)
if not defined PY (
  python --version >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo.
  echo [ERROR] Python was not found on this computer.
  echo.
  echo Please install Python 3.9 or newer from:
  echo     https://www.python.org/downloads/
  echo.
  echo IMPORTANT: on the first installer screen, tick
  echo     [x] Add Python to PATH
  echo before clicking Install.
  echo.
  echo Opening the download page in your browser...
  start "" "https://www.python.org/downloads/"
  echo.
  pause
  exit /b 1
)

%PY% src\_launch_common.py check
if errorlevel 1 (
  REM  Reaching here means the interpreter ran but reported a problem, or it
  REM  failed to start at all. Reporting the second case as "please install
  REM  Python" would mislead when Python IS installed and it is a copied
  REM  virtual environment that is broken -- see venvcheck below.
  %PY% src\_launch_common.py msg err_python
  echo.
  echo     https://www.python.org/downloads/
  echo.
  pause
  exit /b 1
)

%PY% src\_launch_common.py msg banner

REM --- 2. virtual environment -----------------------------------------
if exist "python\python.exe" (
  REM full portable build: interpreter and packages already bundled
  set "VPY=python\python.exe"
) else (
  REM  A venv that was COPIED from another folder cannot work: the stdlib
  REM  location is baked into pyvenv.cfg at creation time, so the copy dies
  REM  with "Failed to import encodings module". Detect it and rebuild,
  REM  rather than showing a misleading "please install Python" message.
  if exist "%VENV%\Scripts\python.exe" (
    %PY% src\_launch_common.py venvcheck "%VENV%"
    if errorlevel 1 (
      %PY% src\_launch_common.py msg rebuild
      rmdir /s /q "%VENV%"
      del /q "%STAMP%" 2>nul
    )
  )
  if not exist "%VENV%\Scripts\python.exe" (
    %PY% src\_launch_common.py msg mkvenv
    %PY% -m venv "%VENV%"
    if errorlevel 1 (
      %PY% src\_launch_common.py msg err_venv
      echo.
      pause
      exit /b 1
    )
  )
  set "VPY=%VENV%\Scripts\python.exe"
)

REM --- 3. dependencies (install only when missing) ---------------------
set "NEEDINSTALL=0"
if not exist "%STAMP%" set "NEEDINSTALL=1"
if "%NEEDINSTALL%"=="1" (
  "!VPY!" src\_launch_common.py deps >nul 2>&1
  if errorlevel 1 (
    "!VPY!" src\_launch_common.py msg install
    "!VPY!" -m pip install --upgrade pip --quiet
    "!VPY!" -m pip install -r requirements.txt
    if errorlevel 1 (
      "!VPY!" src\_launch_common.py msg err_pip
      echo.
      pause
      exit /b 1
    )
    "!VPY!" src\_launch_common.py msg installed
  )
  echo. > "%STAMP%"
)

"!VPY!" src\_launch_common.py deps >nul 2>&1
if errorlevel 1 (
  "!VPY!" src\_launch_common.py msg err_deps
  "!VPY!" src\_launch_common.py deps
  echo.
  pause
  exit /b 1
)

REM --- 3b. Chinese word segmenter (optional, never fatal) --------------
REM  Pulls in PyTorch, so it is installed as its own step rather than via
REM  requirements.txt: a failure here must not stop the app from opening.
"!VPY!" src\_launch_common.py segmenter

REM --- 4. launch --------------------------------------------------------
"!VPY!" src\_launch_common.py credentials >nul 2>&1

REM  The port helper prints the port on stdout and any warning on stderr.
REM  `for /f` captures stdout only, so stderr reaches the console on its own --
REM  that is how the "an older window is still open" notice gets seen.
set "PORT=8501"
for /f "usebackq delims=" %%i in (`"!VPY!" src\_launch_common.py port 2^>con`) do set "PORT=%%i"

"!VPY!" src\_launch_common.py msg starting
echo     http://localhost:!PORT!
"!VPY!" src\_launch_common.py msg keepopen

"!VPY!" -m streamlit run "%APP%" --server.port !PORT! --server.headless false --browser.gatherUsageStats false

echo.
echo The program has stopped.
pause
endlocal

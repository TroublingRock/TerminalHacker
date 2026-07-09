@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "PYTHON="

for %%P in (
  "py -3.12"
  "py -3.11"
  "py -3.10"
  "py -3"
  "python3"
  "python"
) do (
  call :try_python %%P
  if defined PYTHON goto :run
)

call :install_python
if errorlevel 1 goto :fail

set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"

for %%P in (
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
  "py -3.12"
  "py -3"
  "python"
) do (
  call :try_python %%P
  if defined PYTHON goto :run
)

:fail
mshta "javascript:var sh=new ActiveXObject('WScript.Shell');sh.Popup('Could not find or install Python 3.10+.\n\nInstall from https://www.python.org/downloads/\nThen double-click Play Security Simulator again.',0,'Security Simulator',16);close()"
exit /b 1

:run
if /I "%~1"=="--cli" (
  "%PYTHON%" launch\bootstrap.py --cli
) else (
  "%PYTHON%" launch\bootstrap.py
)
set "ERR=!errorlevel!"
if not "!ERR!"=="0" pause
exit /b !ERR!

:try_python
set "TRY=%~1"
if exist !TRY! (
  "!TRY!" -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
) else (
  !TRY! -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
)
if errorlevel 1 exit /b 1
if exist !TRY! (
  for /f "delims=" %%V in ('"!TRY!" -c "import sys; print(sys.executable)"') do set "PYTHON=%%V"
) else (
  for /f "delims=" %%V in ('!TRY! -c "import sys; print(sys.executable)"') do set "PYTHON=%%V"
)
exit /b 0

:install_python
where winget >nul 2>&1
if errorlevel 1 (
  start "" "https://www.python.org/downloads/"
  exit /b 1
)
mshta "javascript:var sh=new ActiveXObject('WScript.Shell');var ok=sh.Popup('Security Simulator needs Python 3.10+.\n\nClick OK to install Python automatically (about 25 MB).',0,'Security Simulator',1);if(ok==1){close()}else{close(new ActiveXObject('WScript.Shell').Run('cmd /c exit 1',0,true));}"
if errorlevel 1 exit /b 1
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements --disable-interactivity
exit /b 0

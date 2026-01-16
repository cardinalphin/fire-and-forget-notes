@echo off
setlocal
cd /d %~dp0

REM Prefer Python 3.11 via the py launcher
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3.11 -c "import sys; print(sys.version)" >nul 2>nul
  if %ERRORLEVEL%==0 (
    set PY=py -3.11
  ) else (
    set PY=py
  )
) else (
  set PY=python
)

if not exist .venv (
  %PY% -m venv .venv
)

call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

python tray.py

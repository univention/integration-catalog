@echo off
:: SPDX-License-Identifier: AGPL-3.0-only
:: SPDX-FileCopyrightText: 2026 Univention GmbH
::
:: Launch the Integration Catalog UI editor on Windows.
:: Double-click this file or run it from the command prompt.
::
:: Usage:
::   start-ui.bat                        (uses catalog root two levels up)
::   start-ui.bat --root C:\path\to\catalog

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "UI_MODULE=%SCRIPT_DIR%src\integration_catalog\ui.py"

:: Default catalog root: two levels up from the editor directory
pushd "%SCRIPT_DIR%..\.."
set "CATALOG_ROOT=%CD%"
popd

:: Parse --root argument
set "EXTRA_ARGS="
:parse_args
if "%~1"=="" goto done_args
if "%~1"=="--root" (
    set "CATALOG_ROOT=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="-r" (
    set "CATALOG_ROOT=%~2"
    shift
    shift
    goto parse_args
)
set "EXTRA_ARGS=%EXTRA_ARGS% %~1"
shift
goto parse_args
:done_args

:: First-time setup
if not exist "%VENV_DIR%\Scripts\streamlit.exe" (
    echo 🔧 First-time setup: creating virtual environment...
    python -m venv "%VENV_DIR%"
    echo 📦 Installing dependencies ^(this takes a moment^)...
    "%VENV_DIR%\Scripts\pip.exe" install --quiet -e "%SCRIPT_DIR%"
    echo ✅ Setup complete.
)

echo 🚀 Starting Integration Catalog Editor...
echo    Catalog root: %CATALOG_ROOT%
echo    Open http://localhost:8501 in your browser ^(opens automatically^).
echo    Press Ctrl+C to stop.
echo.

"%VENV_DIR%\Scripts\streamlit.exe" run "%UI_MODULE%" ^
    --server.headless false ^
    --browser.gatherUsageStats false ^
    -- --root "%CATALOG_ROOT%" %EXTRA_ARGS%

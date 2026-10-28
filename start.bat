@echo off
setlocal
if "%~1"=="" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launcher\menu.ps1"
) else (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launcher\run.ps1" -Action %*
)
set "ACTION_EXIT=%ERRORLEVEL%"
if not "%ACTION_EXIT%"=="0" pause
exit /b %ACTION_EXIT%

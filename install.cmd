@echo off
rem Run this clone's setup.ps1. Path-independent; arguments pass through.
cd /d "%~dp0"
echo.
echo Running setup.ps1 in %CD% ...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File setup.ps1 %*
set EXITCODE=%ERRORLEVEL%
echo.
echo Exit code: %EXITCODE%
echo.
pause

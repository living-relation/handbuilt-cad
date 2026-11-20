@echo off
rem Copy the Cursor plugin. Does not open a browser. Does not add the plugin on claude.ai.
cd /d "%~dp0"
echo.
echo Copying .cursor-plugin and skills from %CD%. This does not open a browser.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File install-plugins.ps1 %*
set EXITCODE=%ERRORLEVEL%
echo.
echo Exit code: %EXITCODE%
echo.
pause

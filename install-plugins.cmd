@echo off
rem Open the claude.ai Plugins page and print the clicks. Does not add the plugin.
cd /d "%~dp0"
echo.
echo Opening the claude.ai Plugins page from %CD% ...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File install-plugins.ps1 %*
set EXITCODE=%ERRORLEVEL%
echo.
echo Exit code: %EXITCODE%
echo.
pause

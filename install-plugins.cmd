@echo off
rem Open the claude.ai Plugins page, print the clicks, and copy the Cursor plugin. Does not add the plugin on claude.ai.
cd /d "%~dp0"
echo.
echo Opening the claude.ai Plugins page and copying .cursor-plugin and skills from %CD% ...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File install-plugins.ps1 %*
set EXITCODE=%ERRORLEVEL%
echo.
echo Exit code: %EXITCODE%
echo.
pause

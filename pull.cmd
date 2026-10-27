@echo off
rem Fast-forward only pull of this clone. One repo; path-independent.
cd /d "%~dp0"
echo.
echo Pulling %CD% ...
echo.
git pull --ff-only
echo.
pause
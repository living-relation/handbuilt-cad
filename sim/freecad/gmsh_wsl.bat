@echo off
rem Runs gmsh inside WSL Ubuntu from the current Windows folder. Windows paths in arguments are converted.
setlocal enabledelayedexpansion
set ARGS=
for %%A in (%*) do (
  set a=%%~A
  if exist "%%~A" (for /f "delims=" %%P in ('wsl.exe -d Ubuntu wslpath -a "%%~fA"') do set a=%%P)
  set ARGS=!ARGS! "!a!"
)
wsl.exe -d Ubuntu --cd "%CD%" -- gmsh !ARGS!

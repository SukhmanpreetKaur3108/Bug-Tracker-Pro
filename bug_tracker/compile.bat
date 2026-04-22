@echo off
REM compile.bat — Compile the C priority engine on Windows (MinGW-w64 / GCC required)
REM Run this once before starting the application.
REM
REM If gcc is not on your PATH, install MinGW-w64:
REM   https://www.mingw-w64.org/

echo Compiling priority_engine.c ...
gcc -shared -o priority_engine.dll priority_engine.c -lm

if %ERRORLEVEL% == 0 (
    echo SUCCESS: priority_engine.dll created.
) else (
    echo FAILED: Check that gcc (MinGW-w64) is installed and on your PATH.
    exit /b 1
)


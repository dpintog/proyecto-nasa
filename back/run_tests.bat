@echo off
REM Quick test runner for subimage locator
REM Run this from cmd.exe or double-click in Explorer

cd /d %~dp0

echo ========================================
echo Subimage Locator - Quick Test
echo ========================================
echo.

echo Setting PYTHONPATH...
set PYTHONPATH=%~dp0src

echo.
echo Running tests...
pytest tests\test_locator.py -v

echo.
echo ========================================
if %ERRORLEVEL% EQU 0 (
    echo Tests PASSED!
    echo.
    echo Next: Try the demo
    echo   1. python create_demo.py
    echo   2. python -m subimage_locator --big demo\big_image.png --small demo\small_crop.png --out demo\result.png
) else (
    echo Tests FAILED - check output above
)
echo ========================================

pause

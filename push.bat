@echo off
cd /d "D:\Development\PythonProject\Chitrika"
echo === git status ===
git status --short
echo.
echo === pushing to origin/main ===
git push origin main
echo.
echo === done ===
pause

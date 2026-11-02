@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
echo Откройте Cookie Clicker на весь экран. Бот стартует через 3 секунды.
echo Остановка: Ctrl+C или мышь в левый верхний угол.
uv run app.py
pause

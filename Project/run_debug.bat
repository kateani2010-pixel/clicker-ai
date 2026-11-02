@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
echo Режим отладки: бот НЕ кликает, 20 кадров сохраняет в папку debug\
echo Откройте игру на весь экран. Старт через 3 секунды.
uv run app.py --dry-run --debug --max-cycles 20
pause

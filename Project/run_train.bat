@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Clicker AI: установка окружения и обучение модели ===
where uv >nul 2>&1
if errorlevel 1 (
    echo uv не найден, устанавливаю...
    powershell -NoProfile -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
)
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
uv python install 3.12
uv sync
if errorlevel 1 (
    echo Ошибка установки зависимостей.
    pause
    exit /b 1
)
echo.
echo === Обучение (10-20 минут на CPU) ===
uv run train.py
echo.
echo Готово. Модель: runs\detect\clicker\weights\best.pt
pause

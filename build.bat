@echo off
chcp 65001 >nul
title Сборка TechCheck4PyrusWebFormLite

:: Путь к вашему портативному Python
set PYTHON_EXE=python_38_full\python.exe

echo [1/3] Проверка и установка библиотек...
%PYTHON_EXE% -m pip install -r requirements.txt
%PYTHON_EXE% -m pip install pyinstaller

echo.
echo [2/3] Запуск компиляции (LITE версия - это может занять пару минут)...
:: Собираем в один файл (-F), прячем консоль (-w), ставим иконку и пакуем внутрь все ресурсы
%PYTHON_EXE% -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --icon "icon.ico" ^
    --hidden-import webview ^
    --hidden-import webview.platforms.edgechromium ^
    --hidden-import webview.platforms.mshtml ^
    --add-data "config.json;." ^
    --add-data "cpu_data.csv;." ^
    --add-data "eula.txt;." ^
    --add-data "icon.ico;." ^
    --add-data "qms_lib.exe;." ^
    --add-data "fly.png;." ^
    "main.py"

echo.
echo [3/3] Очистка временных мусорных файлов...
rmdir /s /q build
del /q main.spec

echo.
echo =======================================================
echo СБОРКА ЗАВЕРШЕНА!
echo Ваш легкий exe-файл находится в появившейся папке "dist".
echo =======================================================
pause
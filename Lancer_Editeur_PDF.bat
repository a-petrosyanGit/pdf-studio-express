@echo off
chcp 65001 > nul
title PDF Studio Express

:: Détection dynamique et propre de l'environnement Python
set "PY_CMD="

if exist "%~dp0venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0venv\Scripts\python.exe"
) else if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Python\bin\python.exe"
) else (
    where py >nul 2>&1 && set "PY_CMD=py"
    if not defined PY_CMD (
        where python >nul 2>&1 && set "PY_CMD=python"
    )
)

if not defined PY_CMD (
    echo [ERREUR] Python n'a pas été détecté sur votre ordinateur.
    echo Veuillez installer Python depuis https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Lancement de l'interface graphique de bureau
start "" "%PY_CMD%" "%~dp0app_gui.py"
exit

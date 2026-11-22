@echo off
chcp 65001 > nul
title Lancement de la version Web de PDF Studio...

:: Recherche automatique de l'exécutable Python
set "PY_CMD="

if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Python\bin\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
) else (
    where py >nul 2>&1 && set "PY_CMD=py"
    if not defined PY_CMD (
        where python >nul 2>&1 && set "PY_CMD=python"
    )
)

if not defined PY_CMD (
    echo [ERREUR] Python n'a pas été détecté sur votre système.
    echo Veuillez installer Python depuis https://www.python.org/downloads/
    pause
    exit /b 1
)

"%PY_CMD%" -m streamlit run "%~dp0app_web.py"
pause

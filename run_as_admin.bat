@echo off
REM Disk-Wiper als Administrator starten
REM Diese Batch-Datei startet die Anwendung mit erhöhten Rechten

echo ========================================
echo  Disk-Wiper (Administrator-Modus)
echo ========================================
echo.

REM Prüfen ob bereits als Admin ausgeführt
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Läuft als Administrator
    echo.
    goto :start_app
) else (
    echo [!] Nicht als Administrator gestartet
    echo.
    echo Bitte diese Datei mit Rechtsklick -^> "Als Administrator ausführen" starten
    echo.
    pause
    exit /b 1
)

:start_app
REM Wechsle ins Verzeichnis, wo dieses Batch-Skript liegt
cd /d "%~dp0"
echo Arbeitsverzeichnis: %CD%
echo.

echo Starte Disk-Wiper...
echo.

REM Aktiviere virtuelle Umgebung falls vorhanden
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Aktiviere virtuelle Umgebung...
    call venv\Scripts\activate.bat
)

REM Starte die Anwendung
python run.py

REM Falls Python nicht gefunden wurde
if %errorLevel% neq 0 (
    echo.
    echo [FEHLER] Python konnte nicht gefunden werden!
    echo Bitte stellen Sie sicher, dass Python installiert ist.
    pause
)

exit /b 0


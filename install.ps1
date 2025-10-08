# Disk Wiper Tool - Windows Installations-Skript
# Muss als Administrator ausgeführt werden

# Prüfe Administrator-Rechte
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ Dieses Skript muss als Administrator ausgeführt werden!" -ForegroundColor Red
    Write-Host "Rechtsklick auf PowerShell -> Als Administrator ausführen" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Disk Wiper Tool - Installation" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Prüfe Python
Write-Host "Prüfe Python-Installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ $pythonVersion gefunden" -ForegroundColor Green
} catch {
    Write-Host "❌ Python nicht gefunden!" -ForegroundColor Red
    Write-Host "Bitte installieren Sie Python 3.8 oder höher von https://www.python.org/" -ForegroundColor Yellow
    pause
    exit 1
}

# Prüfe smartctl
Write-Host ""
Write-Host "Prüfe smartmontools..." -ForegroundColor Yellow
try {
    smartctl --version | Out-Null
    Write-Host "✓ smartmontools gefunden" -ForegroundColor Green
} catch {
    Write-Host "⚠️  smartmontools nicht gefunden" -ForegroundColor Yellow
    Write-Host "Bitte installieren Sie smartmontools von:" -ForegroundColor Yellow
    Write-Host "https://www.smartmontools.org/wiki/Download#InstalltheWindowspackage" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Möchten Sie die Installation trotzdem fortsetzen? (j/n)" -ForegroundColor Yellow
    $continue = Read-Host
    if ($continue -ne 'j' -and $continue -ne 'J') {
        exit 1
    }
}

# Erstelle virtuelle Umgebung
Write-Host ""
Write-Host "Erstelle virtuelle Umgebung..." -ForegroundColor Yellow
python -m venv venv
Write-Host "✓ Virtuelle Umgebung erstellt" -ForegroundColor Green

# Aktiviere venv und installiere Abhängigkeiten
Write-Host ""
Write-Host "Installiere Python-Abhängigkeiten..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
pip install -r requirements.txt
Write-Host "✓ Abhängigkeiten installiert" -ForegroundColor Green

# Erstelle .env falls nicht vorhanden
if (-not (Test-Path .env)) {
    Write-Host ""
    Write-Host "Erstelle .env Datei..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    
    # Generiere zufälligen SECRET_KEY
    $secretKey = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})
    
    # Ersetze in .env
    (Get-Content .env) -replace 'your-secret-key-change-this', $secretKey | Set-Content .env
    
    Write-Host "✓ .env Datei erstellt mit zufälligem SECRET_KEY" -ForegroundColor Green
}

# Erstelle Start-Skript
Write-Host ""
Write-Host "Erstelle Start-Skript..." -ForegroundColor Yellow
@"
@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python run.py
pause
"@ | Out-File -FilePath start.bat -Encoding ASCII

Write-Host "✓ start.bat erstellt" -ForegroundColor Green

# Erstelle Windows Service (optional)
Write-Host ""
Write-Host "Möchten Sie einen Windows Service erstellen? (j/n)" -ForegroundColor Yellow
$createService = Read-Host

if ($createService -eq 'j' -or $createService -eq 'J') {
    Write-Host "⚠️  Windows Service-Erstellung erfordert zusätzliche Tools wie NSSM." -ForegroundColor Yellow
    Write-Host "Bitte folgen Sie der Anleitung im README.md für Service-Installation." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "✓ Installation abgeschlossen!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starten Sie das Tool mit:" -ForegroundColor Yellow
Write-Host "  start.bat" -ForegroundColor Cyan
Write-Host ""
Write-Host "Oder als Administrator in PowerShell:" -ForegroundColor Yellow
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "  python run.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "Das Webinterface ist dann verfügbar unter:" -ForegroundColor Yellow
Write-Host "  http://localhost:5000" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️  WICHTIG: Das Tool muss als Administrator ausgeführt werden," -ForegroundColor Red
Write-Host "   um auf Festplatten zugreifen zu können." -ForegroundColor Red
Write-Host ""

pause


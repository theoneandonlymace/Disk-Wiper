# Disk-Wiper als Administrator starten
# Diese PowerShell-Datei startet die Anwendung mit erhöhten Rechten

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Disk-Wiper (Administrator-Modus)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Prüfen ob bereits als Admin ausgeführt
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[!] Nicht als Administrator gestartet" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Versuche, das Skript als Administrator neu zu starten..." -ForegroundColor Yellow
    Write-Host ""
    
    # Starte das Skript neu als Administrator
    $scriptPath = $MyInvocation.MyCommand.Path
    Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$scriptPath`"" -Verb RunAs
    exit
}

Write-Host "[OK] Läuft als Administrator" -ForegroundColor Green
Write-Host ""

# Wechsle ins Skript-Verzeichnis
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "Arbeitsverzeichnis: $scriptDir" -ForegroundColor Cyan
Write-Host ""

# Aktiviere virtuelle Umgebung falls vorhanden
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "[INFO] Aktiviere virtuelle Umgebung..." -ForegroundColor Yellow
    & "venv\Scripts\Activate.ps1"
    Write-Host ""
}

# Starte die Anwendung
Write-Host "Starte Disk-Wiper..." -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

try {
    python run.py
} catch {
    Write-Host ""
    Write-Host "[FEHLER] Fehler beim Starten der Anwendung: $_" -ForegroundColor Red
    Write-Host ""
    Read-Host "Drücken Sie Enter zum Beenden"
    exit 1
}


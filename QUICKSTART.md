# Schnellstart-Anleitung

## Linux/macOS

### Automatische Installation

```bash
# Repository klonen
git clone <repository-url>
cd Disk-Wiper

# Installations-Skript ausführen
chmod +x install.sh
sudo ./install.sh

# Tool starten
sudo ./start.sh
```

### Manuelle Installation

```bash
# Virtuelle Umgebung erstellen
python3 -m venv venv
source venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# smartmontools installieren
sudo apt-get install smartmontools  # Linux
brew install smartmontools          # macOS

# .env konfigurieren
cp .env.example .env

# Starten
sudo -E env PATH=$PATH python run.py
```

## Windows

### Automatische Installation

```powershell
# PowerShell als Administrator öffnen
# Zum Projektverzeichnis navigieren
cd C:\Path\To\Disk-Wiper

# Installations-Skript ausführen
.\install.ps1

# Tool starten
.\start.bat
```

### Manuelle Installation

```powershell
# PowerShell als Administrator öffnen

# Virtuelle Umgebung erstellen
python -m venv venv
.\venv\Scripts\Activate.ps1

# Abhängigkeiten installieren
pip install -r requirements.txt

# smartmontools manuell von https://www.smartmontools.org/ installieren

# .env konfigurieren
copy .env.example .env

# Starten
python run.py
```

## Nach dem Start

1. Browser öffnen: `http://localhost:5000`
2. Auf "Festplatten scannen" klicken
3. Verfügbare Festplatten werden angezeigt
4. Boot-Festplatten sind automatisch geschützt

## Wichtige Hinweise

⚠️ **Das Tool erfordert Administrator-/Root-Rechte!**

⚠️ **Boot-Festplatten können NICHT gelöscht werden** - sie sind automatisch geschützt.

⚠️ **Alle Daten werden unwiderruflich gelöscht** - stellen Sie sicher, dass Sie die richtige Festplatte auswählen.

## Fehlerbehebung

### "Permission denied"
→ Mit sudo/Administrator-Rechten ausführen

### "smartctl not found"
→ smartmontools installieren (siehe oben)

### Festplatten werden nicht erkannt
→ Berechtigung prüfen, als root/Administrator ausführen

## Support

Siehe ausführliche Dokumentation in `README.md`


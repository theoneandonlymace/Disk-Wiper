# Disk Wiper Tool

Ein webbasiertes Tool zum sicheren Löschen von Festplatten mit automatischem Boot-Disk-Schutz.

## ⚠️ Wichtige Sicherheitshinweise

- **Boot-Festplatten werden IMMER automatisch erkannt und geschützt**
- **Alle Daten auf gelöschten Festplatten werden unwiderruflich vernichtet**
- **Das Tool sollte nur von autorisierten Personen verwendet werden**
- **Erfordert Administrator-/Root-Rechte für den Zugriff auf Festplatten**

## Features

- ✅ **Webinterface**: Intuitive Bedienung über den Browser
- ✅ **Boot-Disk-Schutz**: Automatische Erkennung und Schutz von Boot-Laufwerken
- ✅ **SMART-Daten**: Auslesen und Speichern von SMART-Werten vor dem Löschen
- ✅ **Mehrere Löschmethoden**:
  - Zeros (Einmal mit Nullen überschreiben)
  - Random (Einmal mit Zufallsdaten)
  - DoD 5220.22-M (3 Pässe, höchste Sicherheit)
- ✅ **Datenbank**: Lokale SQLite-Datenbank für alle Protokolle
- ✅ **Suchfunktion**: Suche nach Seriennummer oder Modell
- ✅ **Report-Generierung**: Detaillierte HTML-Reports nach Abschluss
- ✅ **Cross-Platform**: Unterstützt Windows, Linux und macOS

## Systemanforderungen

- Python 3.8 oder höher
- Administrator-/Root-Rechte (für Festplattenzugriff)
- `smartmontools` (für SMART-Daten)

### Linux
```bash
sudo apt-get install smartmontools
```

### macOS
```bash
brew install smartmontools
```

### Windows
- Smartmontools für Windows von [https://www.smartmontools.org/](https://www.smartmontools.org/) installieren
- Als Administrator ausführen

## Installation

### 1. Repository klonen
```bash
git clone <repository-url>
cd Disk-Wiper
```

### 2. Virtuelle Umgebung erstellen (empfohlen)
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Abhängigkeiten installieren
```bash
python -m pip install -r requirements.txt
```

### 4. Umgebungsvariablen konfigurieren
```bash
# Kopiere .env.example zu .env
cp .env.example .env

# Bearbeite .env und setze SECRET_KEY
```

### 5. Datenbank initialisieren
```bash
python run.py
# Die Datenbank wird automatisch erstellt beim ersten Start
```

## Verwendung

### Server starten

**Windows (als Administrator):**
```powershell
# PowerShell als Administrator öffnen
cd C:\Path\To\Disk-Wiper
venv\Scripts\activate
python run.py
```

**Linux/macOS (mit sudo):**
```bash
sudo -E env PATH=$PATH python run.py
# Oder mit aktiviertem venv:
sudo $(which python) run.py
```

Der Server läuft dann auf: `http://localhost:5000`

### Webinterface

1. **Festplatten scannen**
   - Öffnen Sie `http://localhost:5000`
   - Klicken Sie auf "Festplatten scannen"
   - Alle verfügbaren Festplatten werden angezeigt
   - Boot-Festplatten sind automatisch als "Geschützt" markiert

2. **SMART-Daten auslesen**
   - Klicken Sie bei einer Festplatte auf "SMART-Daten"
   - Die Daten werden ausgelesen und in der Datenbank gespeichert

3. **Festplatte löschen**
   - Klicken Sie auf "Löschen" bei einer nicht geschützten Festplatte
   - Wählen Sie die Löschmethode und Anzahl der Pässe
   - Bestätigen Sie den Vorgang
   - Der Fortschritt wird in Echtzeit angezeigt

4. **Wipe-Historie**
   - Navigieren Sie zu "Wipe-Historie"
   - Sehen Sie alle durchgeführten Löschvorgänge
   - Aktualisiert sich automatisch alle 5 Sekunden

5. **Reports ansehen**
   - Bei abgeschlossenen Löschvorgängen auf "Report anzeigen" klicken
   - Detaillierter HTML-Report mit allen Informationen

6. **Suchen**
   - Navigieren Sie zu "Suche"
   - Geben Sie Seriennummer oder Modell ein
   - Durchsucht Festplatten und Wipe-Protokolle

## Projektstruktur

```
Disk-Wiper/
├── app/
│   ├── __init__.py           # Flask App Factory
│   ├── models/               # Datenbank-Modelle
│   │   ├── disk.py          # Festplatten-Modell
│   │   └── wipe_log.py      # Wipe-Protokoll-Modell
│   ├── routes/              # Flask Routes
│   │   └── main.py          # Haupt-Routes
│   ├── templates/           # HTML Templates
│   │   ├── base.html        # Basis-Template
│   │   ├── index.html       # Hauptseite
│   │   ├── wipes.html       # Wipe-Historie
│   │   ├── search.html      # Suchseite
│   │   └── partials/        # HTMX Partials
│   └── utils/               # Utility-Module
│       ├── disk_manager.py  # Festplatten-Verwaltung
│       ├── smart_reader.py  # SMART-Daten
│       ├── wipe_engine.py   # Lösch-Engine
│       └── report_generator.py # Report-Generierung
├── config.py                # Konfiguration
├── run.py                   # Start-Skript
├── requirements.txt         # Python-Abhängigkeiten
└── README.md               # Diese Datei
```

## Sicherheitskonzept

### Boot-Disk-Schutz

Das Tool implementiert mehrere Sicherheitsebenen:

1. **Primäre Erkennung**: Boot-Festplatten werden beim Scannen erkannt
2. **UI-Schutz**: Boot-Festplatten können nicht im Interface gelöscht werden
3. **Backend-Validierung**: Vor jedem Löschvorgang wird erneut geprüft
4. **Doppelte Prüfung**: Unmittelbar vor dem Schreiben erfolgt eine finale Prüfung

**Erkennungsmethoden:**

- **Linux**: Prüfung auf gemountete Partitionen (/, /boot, /boot/efi)
- **Windows**: Prüfung auf System-Laufwerk (C:)
- **macOS**: Prüfung über diskutil

## Löschmethoden

### Zeros (Standard)
- Überschreibt die Festplatte einmal mit Nullen
- Schnellste Methode
- Ausreichend für die meisten Anwendungsfälle

### Random
- Überschreibt die Festplatte mit Zufallsdaten
- Mittlere Sicherheit
- Langsamer als Zeros

### DoD 5220.22-M
- Department of Defense Standard
- 3 Pässe (Zeichen, Komplement, Zufallsdaten)
- Höchste Sicherheit
- Am langsamsten

## API-Endpunkte

### Festplatten
- `GET /api/disks/scan` - Scannt verfügbare Festplatten
- `GET /api/disks` - Gibt alle Festplatten zurück
- `GET /api/disks/<id>` - Details einer Festplatte
- `GET /api/disks/<id>/smart` - SMART-Daten auslesen
- `POST /api/disks/<id>/wipe` - Löschvorgang starten

### Wipe-Vorgänge
- `GET /api/wipes` - Alle Wipe-Vorgänge
- `GET /api/wipes/<id>` - Details eines Vorgangs
- `GET /api/wipes/<id>/status` - Aktueller Status
- `GET /api/wipes/<id>/report?format=html` - Report generieren

### Suche
- `GET /api/search?q=<query>` - Suche nach SN/Modell

## Fehlerbehebung

### "Permission denied" beim Zugriff auf Festplatten
- Stellen Sie sicher, dass das Tool mit Administrator-/Root-Rechten läuft

### SMART-Daten können nicht gelesen werden
- Installieren Sie `smartmontools`
- Prüfen Sie, ob smartctl im PATH ist

### Festplatten werden nicht erkannt
- Prüfen Sie die Berechtigung
- Unter Linux: Prüfen Sie `/dev/` Zugriff
- Unter Windows: Als Administrator ausführen

### Wipe-Vorgang startet nicht
- Prüfen Sie, ob die Festplatte als Boot-Disk markiert ist
- Prüfen Sie die Logs für detaillierte Fehlermeldungen

## Entwicklung

### Datenbank-Migrationen
```bash
flask db init
flask db migrate -m "Description"
flask db upgrade
```

### Tests ausführen
```bash
pytest
```

## Lizenz

Dieses Tool dient ausschließlich zu autorisierten Zwecken. Der Autor übernimmt keine Haftung für Datenverlust oder Schäden.

## Technologie-Stack

- **Backend**: Flask, SQLAlchemy
- **Frontend**: HTMX, Tailwind CSS
- **Datenbank**: SQLite
- **System**: psutil, smartmontools

## Support

Bei Fragen oder Problemen erstellen Sie bitte ein Issue im Repository.

---

**⚠️ WARNUNG**: Dieses Tool löscht Daten unwiderruflich. Verwenden Sie es mit äußerster Vorsicht!


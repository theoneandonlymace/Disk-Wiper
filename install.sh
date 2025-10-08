#!/bin/bash

# Disk Wiper Tool - Linux/macOS Installations-Skript
# Muss mit sudo ausgeführt werden

set -e

echo "======================================"
echo "Disk Wiper Tool - Installation"
echo "======================================"
echo ""

# Prüfe ob sudo
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Bitte als root/sudo ausführen: sudo ./install.sh"
    exit 1
fi

# Erkenne OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    echo "✓ Linux erkannt"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    echo "✓ macOS erkannt"
else
    echo "❌ Nicht unterstütztes Betriebssystem: $OSTYPE"
    exit 1
fi

# Prüfe Python
echo ""
echo "Prüfe Python-Installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 nicht gefunden. Bitte installieren Sie Python 3.8 oder höher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✓ Python $PYTHON_VERSION gefunden"

# Installiere smartmontools
echo ""
echo "Installiere smartmontools..."
if [ "$OS" = "linux" ]; then
    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y smartmontools
    elif command -v yum &> /dev/null; then
        yum install -y smartmontools
    else
        echo "⚠️  Konnte smartmontools nicht automatisch installieren."
        echo "   Bitte manuell installieren: sudo apt-get install smartmontools"
    fi
elif [ "$OS" = "macos" ]; then
    if command -v brew &> /dev/null; then
        brew install smartmontools
    else
        echo "⚠️  Homebrew nicht gefunden. Bitte smartmontools manuell installieren."
    fi
fi

# Prüfe smartctl
if command -v smartctl &> /dev/null; then
    echo "✓ smartmontools installiert"
else
    echo "⚠️  smartmontools konnte nicht installiert werden"
fi

# Erstelle virtuelle Umgebung
echo ""
echo "Erstelle virtuelle Umgebung..."
python3 -m venv venv
echo "✓ Virtuelle Umgebung erstellt"

# Aktiviere venv und installiere Abhängigkeiten
echo ""
echo "Installiere Python-Abhängigkeiten..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Abhängigkeiten installiert"

# Erstelle .env falls nicht vorhanden
if [ ! -f .env ]; then
    echo ""
    echo "Erstelle .env Datei..."
    cp .env.example .env
    
    # Generiere zufälligen SECRET_KEY
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    
    # Ersetze in .env (macOS und Linux kompatibel)
    if [[ "$OS" == "macos" ]]; then
        sed -i '' "s/your-secret-key-change-this/$SECRET_KEY/" .env
    else
        sed -i "s/your-secret-key-change-this/$SECRET_KEY/" .env
    fi
    
    echo "✓ .env Datei erstellt mit zufälligem SECRET_KEY"
fi

# Erstelle Start-Skript
echo ""
echo "Erstelle Start-Skript..."
cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
sudo -E env PATH=$PATH python run.py
EOF

chmod +x start.sh
echo "✓ start.sh erstellt"

# Erstelle Systemd Service (nur Linux)
if [ "$OS" = "linux" ]; then
    echo ""
    echo "Möchten Sie einen systemd Service erstellen? (j/n)"
    read -r CREATE_SERVICE
    
    if [ "$CREATE_SERVICE" = "j" ] || [ "$CREATE_SERVICE" = "J" ]; then
        INSTALL_DIR=$(pwd)
        cat > /etc/systemd/system/disk-wiper.service << EOF
[Unit]
Description=Disk Wiper Tool
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/run.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
        
        systemctl daemon-reload
        echo "✓ systemd Service erstellt"
        echo ""
        echo "Service-Befehle:"
        echo "  sudo systemctl start disk-wiper    # Service starten"
        echo "  sudo systemctl stop disk-wiper     # Service stoppen"
        echo "  sudo systemctl enable disk-wiper   # Autostart aktivieren"
        echo "  sudo systemctl status disk-wiper   # Status anzeigen"
    fi
fi

echo ""
echo "======================================"
echo "✓ Installation abgeschlossen!"
echo "======================================"
echo ""
echo "Starten Sie das Tool mit:"
echo "  sudo ./start.sh"
echo ""
echo "Das Webinterface ist dann verfügbar unter:"
echo "  http://localhost:5000"
echo ""
echo "⚠️  WICHTIG: Das Tool muss mit sudo/root-Rechten ausgeführt werden,"
echo "   um auf Festplatten zugreifen zu können."
echo ""


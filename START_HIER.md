# 🚀 Disk-Wiper als Administrator starten

Um die erweiterten SMART-Daten (Betriebsstunden, Temperatur, Verschleiß) zu lesen, muss die Anwendung mit **Administrator-Rechten** ausgeführt werden.

## 📝 Methoden zum Starten als Administrator

### ✅ **Methode 1: Batch-Datei (Empfohlen für Windows)**

1. **Rechtsklick** auf `run_as_admin.bat`
2. Wählen Sie **"Als Administrator ausführen"**
3. Bestätigen Sie die UAC-Abfrage (Benutzerkontensteuerung)
4. Die Anwendung startet automatisch mit Admin-Rechten

### ✅ **Methode 2: PowerShell-Skript**

1. **Rechtsklick** auf `run_as_admin.ps1`
2. Wählen Sie **"Mit PowerShell ausführen"**
3. Das Skript erkennt automatisch, ob Admin-Rechte fehlen und fordert diese an
4. Bestätigen Sie die UAC-Abfrage

**Hinweis:** Falls PowerShell-Skripte blockiert sind, führen Sie zuerst aus:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### ✅ **Methode 3: PowerShell manuell als Admin**

1. Drücken Sie **Windows-Taste + X**
2. Wählen Sie **"Terminal (Administrator)"** oder **"PowerShell (Administrator)"**
3. Navigieren Sie zum Projektordner:
   ```powershell
   cd "C:\Users\smueller\Documents\Code\Disk-Wiper"
   ```
4. Starten Sie die Anwendung:
   ```powershell
   python run.py
   ```

### ✅ **Methode 4: Eingabeaufforderung als Admin**

1. Drücken Sie **Windows-Taste**
2. Tippen Sie **"cmd"**
3. **Rechtsklick** auf "Eingabeaufforderung"
4. Wählen Sie **"Als Administrator ausführen"**
5. Navigieren Sie zum Projektordner:
   ```cmd
   cd C:\Users\smueller\Documents\Code\Disk-Wiper
   ```
6. Starten Sie die Anwendung:
   ```cmd
   python run.py
   ```

### ✅ **Methode 5: Verknüpfung mit Admin-Rechten erstellen**

1. **Rechtsklick** auf `run.py` → **"Verknüpfung erstellen"**
2. **Rechtsklick** auf die neue Verknüpfung → **"Eigenschaften"**
3. Klicken Sie auf **"Erweitert..."**
4. Aktivieren Sie **"Als Administrator ausführen"**
5. Klicken Sie auf **OK** und **Übernehmen**
6. Beim Doppelklick auf die Verknüpfung wird die UAC-Abfrage angezeigt

## 🔍 Überprüfung

Nach dem Start als Administrator sollten Sie in den SMART-Daten folgende zusätzliche Informationen sehen:

- ✅ **Betriebsstunden** (Power-On Hours)
- ✅ **Temperatur** (falls vom Laufwerk unterstützt)
- ✅ **Verschleiß** (bei SSDs)
- ✅ **Lesefehler / Schreibfehler**

## ⚠️ Wichtige Hinweise

- **UAC-Abfrage:** Bei jedem Start werden Sie nach Admin-Rechten gefragt
- **Sicherheit:** Die Anwendung benötigt Admin-Rechte nur für die erweiterten SMART-Daten
- **Alternative:** Die Anwendung funktioniert auch ohne Admin-Rechte, zeigt dann aber weniger detaillierte SMART-Informationen

## 🆘 Bei Problemen

Falls die Anwendung nicht startet:

1. Überprüfen Sie, ob Python installiert ist: `python --version`
2. Installieren Sie die Abhängigkeiten: `pip install -r requirements.txt`
3. Prüfen Sie die Konsole auf Fehlermeldungen
4. Öffnen Sie ein Issue auf GitHub oder kontaktieren Sie den Support

## 📚 Weitere Informationen

- **README.md** - Vollständige Dokumentation
- **QUICKSTART.md** - Schnellstart-Anleitung
- **config.py** - Konfigurationsoptionen

---

**Viel Erfolg beim sicheren Löschen Ihrer Festplatten!** 🎉


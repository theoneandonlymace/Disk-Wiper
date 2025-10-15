# BSI CON.6 Löschmethode - Dokumentation

## Übersicht

Die **BSI CON.6** Löschmethode ist konform mit dem IT-Grundschutz-Kompendium des Bundesamts für Sicherheit in der Informationstechnik (BSI), speziell dem Baustein **CON.6 "Löschen und Vernichten"**.

## Rechtliche Grundlage

- **Baustein**: CON.6 - Löschen und Vernichten
- **Anforderung**: CON.6.A12 (Mindestanforderungen an Verfahren zur Löschung und Vernichtung)
- **Quelle**: BSI IT-Grundschutz-Kompendium, Edition 2023

## Technische Spezifikation

### Für HDDs (Festplatten)
- **Methode**: 2 Pässe mit Zufallsdaten
- **Begründung**: Erhöhter Schutzbedarf gemäß BSI-Empfehlung
- **Pattern**: Vollständiges Überschreiben mit kryptographisch sicheren Zufallswerten

### Für SSDs/NVMe
- **Methode**: 1 Pass mit Zufallsdaten
- **Begründung**: Wear Leveling macht mehrere Pässe ineffektiv
- **Pattern**: Vollständiges Überschreiben mit kryptographisch sicheren Zufallswerten

## Features

### ✅ Automatische Erkennung
Die Methode erkennt automatisch den Datenträgertyp und passt die Anzahl der Pässe entsprechend an:
- **HDD** → 2 Pässe
- **SSD/NVMe** → 1 Pass

### ✅ Verifikation
Nach dem Löschvorgang werden automatisch 10 zufällige Stichproben genommen, um sicherzustellen, dass:
- Keine erkennbaren Muster vorhanden sind
- Die Daten tatsächlich überschrieben wurden
- Keine Nullen oder 0xFF-Blöcke vorhanden sind

### ✅ Dokumentation
Jeder Löschvorgang wird dokumentiert mit:
- Verwendete Methode (BSI CON.6.A12)
- Datenträgertyp (HDD/SSD/NVMe)
- Anzahl der Pässe
- Verwendetes Pattern (Zufallsdaten)
- Verifikationsergebnisse
- Zeitstempel (Start/Ende)
- SMART-Daten vor und nach dem Wipe

## Compliance

Die Implementierung erfüllt folgende BSI-Anforderungen:

### CON.6.A12 - Mindestanforderungen
✅ **Digitale wiederbeschreibbare Datenträger**  
→ Vollständiges Überschreiben mit Zufallswerten

✅ **Dokumentation**  
→ Alle Löschvorgänge werden protokolliert und sind nachvollziehbar

✅ **Verifikation**  
→ Stichprobenhafte Überprüfung der erfolgreichen Löschung

### Schutzbedarf

#### Normaler Schutzbedarf
- **SSDs/NVMe**: 1 Pass ausreichend ✅
- **HDDs**: 2 Pässe (erhöhter Schutzbedarf) ✅

#### Erhöhter Schutzbedarf
- **Alle Datenträger**: Mindestens 2 Pässe ✅

#### Hoher Schutzbedarf
⚠️ **Hinweis**: Bei sehr hohem Schutzbedarf empfiehlt das BSI zusätzlich:
- Physische Vernichtung nach ISO/IEC 21964-2 (Sicherheitsstufe 3)
- Oder Verwendung verschlüsselter Datenträger mit kryptographischem Löschen

## Wichtige Hinweise

### ⚠️ Verschlüsselte Datenträger
Für verschlüsselte Datenträger empfiehlt das BSI:
- Sicheres Löschen des kryptographischen Schlüssels
- Nicht das Überschreiben der verschlüsselten Daten

Dies ist in der aktuellen Implementation noch nicht umgesetzt.

### 📋 Nachweisführung
Die Wipe-Reports enthalten:
- Alle relevanten Informationen für Compliance-Nachweise
- SMART-Daten vor und nach dem Wipe
- Verifikationsergebnisse
- Zeitstempel und Dauer

### 🔒 Sicherheitsstufen
Die BSI CON.6 Methode entspricht:
- **Normaler Schutzbedarf**: Vollständig erfüllt ✅
- **Erhöhter Schutzbedarf**: Vollständig erfüllt ✅
- **Hoher Schutzbedarf**: Teilweise erfüllt (zusätzliche Maßnahmen empfohlen)

## Verwendung

### In der Benutzeroberfläche
1. Festplatte auswählen
2. Lösch-Methode: **"🇩🇪 BSI CON.6"** wählen
3. "Wipe starten" klicken
4. Nach Abschluss: Report als HTML herunterladen

### Programmgesteuert
```python
from app.utils.wipe_engine import WipeEngine

success, message, wipe_log_id = WipeEngine.start_wipe(
    disk_id=1,
    device_path='/dev/sda',
    wipe_method='bsi',
    passes=1  # Wird automatisch angepasst
)
```

## Vergleich mit anderen Methoden

| Methode | Pässe | Dauer | Sicherheit | BSI-konform |
|---------|-------|-------|------------|-------------|
| Fast Clear | 0 | ⚡ Sehr schnell | ❌ Gering | ❌ Nein |
| Zeros | 1 | 🔵 Schnell | 🟡 Mittel | 🟡 Teilweise |
| Random | 1 | 🔵 Schnell | 🟢 Gut | 🟡 Teilweise |
| **BSI CON.6** | **1-2** | **🟢 Mittel** | **🟢 Hoch** | **✅ Ja** |
| DoD 5220.22-M | 3 | 🔴 Langsam | 🟢 Sehr Hoch | 🟢 Ja |

## Empfehlungen

### Wann BSI CON.6 verwenden?
✅ **Empfohlen für**:
- Deutsche Behörden und öffentliche Einrichtungen
- Unternehmen mit IT-Grundschutz-Anforderungen
- Compliance mit deutschen Datenschutzrichtlinien
- Normaler bis erhöhter Schutzbedarf

### Wann andere Methoden?
- **Fast Clear**: Nur für nicht-sensible Test-Datenträger
- **DoD 5220.22-M**: Für höchste Sicherheitsanforderungen
- **Zeros/Random**: Für einfache Anwendungsfälle ohne Compliance-Anforderungen

## Support und Referenzen

### Offizielle BSI-Dokumente
- [BSI IT-Grundschutz-Kompendium](https://www.bsi.bund.de/IT-Grundschutz)
- [CON.6 Löschen und Vernichten](https://www.bsi.bund.de/SharedDocs/Downloads/DE/BSI/Grundschutz/IT-GS-Kompendium_Einzel_PDFs_2023/03_CON_Konzepte_und_Vorgehensweisen/CON_6_Loeschen_und_Vernichten_Edition_2023.html)

### ISO-Standards
- ISO/IEC 21964-2: Techniken zur Datenträgervernichtung

---

**Version**: 1.0  
**Datum**: Oktober 2025  
**Status**: Produktionsreif ✅


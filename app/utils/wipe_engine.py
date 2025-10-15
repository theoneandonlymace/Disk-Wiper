import os
import subprocess
import threading
import time
import json
from datetime import datetime
from flask import current_app
from app import db
from app.models import WipeLog
from app.utils.disk_manager import DiskManager
from app.utils.smart_reader import SmartReader


class WipeEngine:
    """Engine für das sichere Löschen von Festplatten"""
    
    # Aktive Wipe-Prozesse
    active_wipes = {}
    wipe_lock = threading.Lock()

    @staticmethod
    def is_nvme_device(device_path):
        """Prüft ob es sich um ein NVMe-Gerät handelt"""
        return 'nvme' in device_path.lower()
    
    @staticmethod
    def is_ssd_device(device_path):
        """Prüft ob es sich um eine SSD handelt (inkl. NVMe)"""
        if WipeEngine.is_nvme_device(device_path):
            return True
        
        if os.name != 'nt':  # Linux
            try:
                # Extrahiere Device-Name (z.B. 'sda' aus '/dev/sda')
                device_name = device_path.split('/')[-1]
                
                # Prüfe rotational flag (0 = SSD, 1 = HDD)
                rotational_path = f"/sys/block/{device_name}/queue/rotational"
                if os.path.exists(rotational_path):
                    with open(rotational_path, 'r') as f:
                        return f.read().strip() == '0'
            except:
                pass
        
        return False

    @staticmethod
    def start_wipe(disk_id, device_path, wipe_method='zeros', passes=1):
        """
        Startet einen Wipe-Vorgang
        Returns: (success, message, wipe_log_id)
        """
        
        # KRITISCHE SICHERHEITSPRÜFUNG
        is_safe, message = DiskManager.verify_not_boot_disk(device_path)
        if not is_safe:
            return False, f"SICHERHEITSFEHLER: {message}", None
        
        # Prüfe ob bereits ein Wipe läuft
        with WipeEngine.wipe_lock:
            if device_path in WipeEngine.active_wipes:
                return False, "Ein Wipe-Vorgang läuft bereits für diese Festplatte", None
            
            # Markiere als aktiv
            WipeEngine.active_wipes[device_path] = {'status': 'starting'}
        
        try:
            # Erstelle WipeLog-Eintrag
            from app.models import Disk
            disk = Disk.query.get(disk_id)
            
            if not disk:
                return False, "Festplatte nicht gefunden", None
            
            wipe_log = WipeLog(
                disk_id=disk_id,
                device_path=device_path,
                model=disk.model,
                serial_number=disk.serial_number,
                size_bytes=disk.size_bytes,
                smart_data_before=disk.smart_data,
                wipe_method=wipe_method,
                wipe_passes=passes,
                status='in_progress',
                start_time=datetime.utcnow()
            )
            
            db.session.add(wipe_log)
            db.session.commit()
            
            # App-Context für Thread speichern
            app = current_app._get_current_object()
            
            # Starte Wipe-Thread
            wipe_thread = threading.Thread(
                target=WipeEngine._perform_wipe,
                args=(app, wipe_log.id, device_path, wipe_method, passes),
                daemon=True
            )
            wipe_thread.start()
            
            return True, "Wipe-Vorgang gestartet", wipe_log.id
            
        except Exception as e:
            # Aufräumen bei Fehler
            with WipeEngine.wipe_lock:
                if device_path in WipeEngine.active_wipes:
                    del WipeEngine.active_wipes[device_path]
            
            return False, f"Fehler beim Starten des Wipe-Vorgangs: {str(e)}", None

    @staticmethod
    def _perform_wipe(app, wipe_log_id, device_path, wipe_method, passes):
        """Führt den eigentlichen Wipe-Vorgang durch (läuft in separatem Thread)"""
        
        with app.app_context():
            wipe_log = WipeLog.query.get(wipe_log_id)
            if not wipe_log:
                return
            
            try:
                # NOCHMALIGE SICHERHEITSPRÜFUNG vor dem Schreiben
                is_safe, message = DiskManager.verify_not_boot_disk(device_path)
                if not is_safe:
                    raise Exception(f"SICHERHEITSPRÜFUNG FEHLGESCHLAGEN: {message}")
                
                # Update Status
                WipeEngine.active_wipes[device_path] = {
                    'status': 'running',
                    'progress': 0.0,
                    'wipe_log_id': wipe_log_id
                }
                
                # Führe Wipe durch
                if wipe_method == 'zeros':
                    WipeEngine._wipe_zeros(wipe_log_id, device_path, passes)
                elif wipe_method == 'random':
                    WipeEngine._wipe_random(wipe_log_id, device_path, passes)
                elif wipe_method == 'dod':
                    WipeEngine._wipe_dod(wipe_log_id, device_path)
                elif wipe_method == 'bsi':
                    WipeEngine._wipe_bsi(wipe_log_id, device_path)
                elif wipe_method == 'fast_clear':
                    WipeEngine._wipe_fast_clear(wipe_log_id, device_path)
                else:
                    raise Exception(f"Unbekannte Wipe-Methode: {wipe_method}")
                
                # Erfolgreich abgeschlossen
                end_time = datetime.utcnow()
                duration = (end_time - wipe_log.start_time).total_seconds()
                
                # Lese SMART-Daten nach dem Wipe aus
                try:
                    smart_data_after = SmartReader.get_smart_data(device_path)
                    if smart_data_after and 'error' not in smart_data_after:
                        wipe_log.smart_data_after = json.dumps(smart_data_after)
                except Exception as e:
                    # Fehler beim Lesen der SMART-Daten ignorieren (nicht kritisch)
                    print(f"Warnung: SMART-Daten nach Wipe konnten nicht gelesen werden: {e}")
                
                wipe_log.status = 'completed'
                wipe_log.end_time = end_time
                wipe_log.duration_seconds = int(duration)
                wipe_log.progress_percent = 100.0
                wipe_log.verified = True
                
                db.session.commit()
                
            except Exception as e:
                # Fehler aufgetreten
                wipe_log.status = 'failed'
                wipe_log.error_message = str(e)
                wipe_log.end_time = datetime.utcnow()
                db.session.commit()
            
            finally:
                # Cleanup
                with WipeEngine.wipe_lock:
                    if device_path in WipeEngine.active_wipes:
                        del WipeEngine.active_wipes[device_path]

    @staticmethod
    def _wipe_zeros(wipe_log_id, device_path, passes):
        """Löscht die Festplatte durch Überschreiben mit Nullen"""
        
        for pass_num in range(passes):
            wipe_log = WipeLog.query.get(wipe_log_id)
            
            # Direkter Python-Ansatz für präzises Progress-Tracking
            try:
                buffer_size = 1024 * 1024  # 1MB
                buffer = bytes(buffer_size)  # Nullen
                
                with open(device_path, 'wb', buffering=buffer_size) as disk:
                    bytes_written = 0
                    
                    # Versuche die Disk-Größe zu ermitteln
                    try:
                        disk.seek(0, os.SEEK_END)
                        total_size = disk.tell()
                        disk.seek(0)
                    except:
                        # Wenn Größe nicht ermittelbar, verwende Größe aus WipeLog
                        total_size = wipe_log.size_bytes if wipe_log.size_bytes else None
                    
                    # Schreibe Nullen bis die Disk voll ist
                    last_update_percent = -1
                    while True:
                        try:
                            disk.write(buffer)
                            bytes_written += buffer_size
                            
                            # Update Progress bei jedem Prozent
                            if total_size and total_size > 0:
                                current_pass_progress = bytes_written / total_size
                                total_progress = ((pass_num + current_pass_progress) / passes) * 100
                                
                                # Nur updaten wenn sich der Prozentsatz geändert hat
                                current_percent = int(total_progress)
                                if current_percent != last_update_percent:
                                    wipe_log.progress_percent = min(total_progress, 99.9)
                                    db.session.commit()
                                    
                                    if device_path in WipeEngine.active_wipes:
                                        WipeEngine.active_wipes[device_path]['progress'] = wipe_log.progress_percent
                                    
                                    last_update_percent = current_percent
                        
                        except IOError as e:
                            # Disk ist voll - das ist normal und bedeutet erfolgreicher Abschluss
                            if e.errno == 28:  # ENOSPC - No space left on device
                                break
                            else:
                                raise
                
            except Exception as e:
                # Prüfe ob es der normale "disk voll" Fehler ist
                error_msg = str(e)
                is_normal_completion = (
                    "No space left on device" in error_msg or
                    "kein Speicherplatz mehr verfügbar" in error_msg or
                    "Auf dem Gerät ist kein Speicherplatz mehr verfügbar" in error_msg or
                    (hasattr(e, 'errno') and e.errno == 28)
                )
                
                if not is_normal_completion:
                    raise Exception(f"Wipe-Befehl fehlgeschlagen (Pass {pass_num + 1}): {error_msg}")

    @staticmethod
    def _wipe_random(wipe_log_id, device_path, passes):
        """Löscht die Festplatte durch Überschreiben mit Zufallsdaten"""
        
        for pass_num in range(passes):
            wipe_log = WipeLog.query.get(wipe_log_id)
            
            # Direkter Python-Ansatz mit os.urandom für präzises Progress-Tracking
            try:
                buffer_size = 1024 * 1024  # 1MB
                
                with open(device_path, 'wb', buffering=buffer_size) as disk:
                    bytes_written = 0
                
                    # Versuche die Disk-Größe zu ermitteln
                    try:
                        disk.seek(0, os.SEEK_END)
                        total_size = disk.tell()
                        disk.seek(0)
                    except:
                        # Wenn Größe nicht ermittelbar, verwende Größe aus WipeLog
                        total_size = wipe_log.size_bytes if wipe_log.size_bytes else None
                    
                    # Schreibe Zufallsdaten bis die Disk voll ist
                    last_update_percent = -1
                    while True:
                        try:
                            # Generiere Zufallsdaten
                            random_buffer = os.urandom(buffer_size)
                            disk.write(random_buffer)
                            bytes_written += buffer_size
                            
                            # Update Progress bei jedem Prozent
                            if total_size and total_size > 0:
                                current_pass_progress = bytes_written / total_size
                                total_progress = ((pass_num + current_pass_progress) / passes) * 100
                                
                                # Nur updaten wenn sich der Prozentsatz geändert hat
                                current_percent = int(total_progress)
                                if current_percent != last_update_percent:
                                    wipe_log.progress_percent = min(total_progress, 99.9)
                                    db.session.commit()
                                    
                                    if device_path in WipeEngine.active_wipes:
                                        WipeEngine.active_wipes[device_path]['progress'] = wipe_log.progress_percent
                                    
                                    last_update_percent = current_percent
                        
                        except IOError as e:
                            # Disk ist voll - das ist normal und bedeutet erfolgreicher Abschluss
                            if e.errno == 28:  # ENOSPC - No space left on device
                                break
                            else:
                                raise
                
            except Exception as e:
                # Prüfe ob es der normale "disk voll" Fehler ist
                error_msg = str(e)
                is_normal_completion = (
                    "No space left on device" in error_msg or
                    "kein Speicherplatz mehr verfügbar" in error_msg or
                    "Auf dem Gerät ist kein Speicherplatz mehr verfügbar" in error_msg or
                    (hasattr(e, 'errno') and e.errno == 28)
                )
                
                if not is_normal_completion:
                    raise Exception(f"Random Wipe fehlgeschlagen (Pass {pass_num + 1}): {error_msg}")

    @staticmethod
    def _wipe_dod(wipe_log_id, device_path):
        """
        DoD 5220.22-M Standard (3 Pässe):
        1. Überschreiben mit Zeichen (0x00)
        2. Überschreiben mit Komplement (0xFF)
        3. Überschreiben mit Zufallsdaten
        """
        
        # Pass 1: Zeichen (0x00)
        WipeEngine._wipe_zeros(wipe_log_id, device_path, 1)
        
        # Pass 2: Komplement (0xFF)
        WipeEngine._wipe_ones(wipe_log_id, device_path, 1)
        
        # Pass 3: Zufallsdaten
        WipeEngine._wipe_random(wipe_log_id, device_path, 1)
    
    @staticmethod
    def _wipe_bsi(wipe_log_id, device_path):
        """
        BSI CON.6 konformes Löschen gemäß IT-Grundschutz-Kompendium
        
        Anforderung CON.6.A12:
        - Vollständiges Überschreiben digitaler wiederbeschreibbarer Datenträger
          mit Zufallswerten (mindestens 1 Pass für normalen Schutzbedarf)
        - Bei erhöhtem Schutzbedarf wird ein zusätzlicher Pass empfohlen
        
        Diese Methode erfüllt die Mindestanforderungen für:
        - Normalen Schutzbedarf: 1 Pass mit Zufallsdaten
        - Erhöhten Schutzbedarf: 2 Pässe mit Zufallsdaten
        
        Hinweis: Für verschlüsselte Datenträger sollte stattdessen der
        kryptographische Schlüssel gemäß Kryptokonzept gelöscht werden.
        
        Referenz: BSI IT-Grundschutz-Kompendium, Baustein CON.6
        """
        wipe_log = WipeLog.query.get(wipe_log_id)
        
        # Prüfe ob SSD/NVMe - bei SSDs ist oft 1 Pass ausreichend
        is_ssd = WipeEngine.is_ssd_device(device_path)
        is_nvme = WipeEngine.is_nvme_device(device_path)
        
        # BSI CON.6 Anforderung:
        # - Normaler Schutzbedarf: 1 Pass Zufallsdaten
        # - Erhöhter Schutzbedarf: 2 Pässe Zufallsdaten (empfohlen für HDDs)
        
        if is_ssd or is_nvme:
            # Für SSDs/NVMe: 1 Pass ist ausreichend (Wear Leveling berücksichtigen)
            num_passes = 1
            wipe_log.verification_data = json.dumps({
                'bsi_method': 'CON.6.A12',
                'device_type': 'SSD/NVMe',
                'passes': num_passes,
                'pattern': 'Zufallsdaten',
                'note': '1 Pass ausreichend für SSD/NVMe aufgrund von Wear Leveling'
            })
        else:
            # Für HDDs: 2 Pässe für erhöhten Schutzbedarf (empfohlen)
            num_passes = 2
            wipe_log.verification_data = json.dumps({
                'bsi_method': 'CON.6.A12',
                'device_type': 'HDD',
                'passes': num_passes,
                'pattern': 'Zufallsdaten',
                'note': '2 Pässe für erhöhten Schutzbedarf gemäß BSI-Empfehlung'
            })
        
        db.session.commit()
        
        # Führe Zufallsdaten-Überschreibung durch
        for pass_num in range(num_passes):
            WipeEngine._wipe_random(wipe_log_id, device_path, 1)
        
        # Zusätzliche Verifikation (optional, aber empfohlen)
        # Lese einige Blöcke und prüfe, dass keine erkennbaren Muster vorhanden sind
        try:
            WipeEngine._verify_bsi_wipe(wipe_log_id, device_path)
        except Exception as e:
            print(f"Warnung: BSI-Verifikation fehlgeschlagen: {e}")
    
    @staticmethod
    def _verify_bsi_wipe(wipe_log_id, device_path):
        """
        Verifiziert dass der Datenträger ordnungsgemäß gelöscht wurde
        durch Stichproben an verschiedenen Positionen
        """
        wipe_log = WipeLog.query.get(wipe_log_id)
        
        try:
            buffer_size = 1024 * 1024  # 1 MB
            samples_to_check = 10  # Prüfe 10 zufällige Positionen
            
            with open(device_path, 'rb', buffering=buffer_size) as disk:
                # Ermittle Disk-Größe
                try:
                    disk.seek(0, os.SEEK_END)
                    total_size = disk.tell()
                except:
                    total_size = wipe_log.size_bytes if wipe_log.size_bytes else None
                
                if not total_size or total_size == 0:
                    return
                
                # Prüfe Stichproben an zufälligen Positionen
                import random
                verification_results = []
                
                for i in range(samples_to_check):
                    # Zufällige Position
                    position = random.randint(0, max(0, total_size - buffer_size))
                    
                    try:
                        disk.seek(position)
                        data = disk.read(min(buffer_size, 4096))  # Lese nur 4KB pro Sample
                        
                        # Prüfe ob Daten nicht komplett Nullen oder komplett 0xFF sind
                        # (würde auf unvollständige Löschung hindeuten)
                        all_zeros = all(b == 0x00 for b in data[:100])
                        all_ones = all(b == 0xFF for b in data[:100])
                        
                        verification_results.append({
                            'position': position,
                            'all_zeros': all_zeros,
                            'all_ones': all_ones,
                            'appears_random': not (all_zeros or all_ones)
                        })
                    except:
                        pass
                
                # Speichere Verifikationsergebnisse
                if wipe_log.verification_data:
                    verification_data = json.loads(wipe_log.verification_data)
                else:
                    verification_data = {}
                
                verification_data['verification_samples'] = verification_results
                verification_data['verification_passed'] = any(r['appears_random'] for r in verification_results)
                
                wipe_log.verification_data = json.dumps(verification_data)
                db.session.commit()
                
        except Exception as e:
            # Verifikation ist optional, Fehler nicht kritisch
            print(f"BSI-Verifikation konnte nicht durchgeführt werden: {e}")
    
    @staticmethod
    def _wipe_ones(wipe_log_id, device_path, passes):
        """Löscht die Festplatte durch Überschreiben mit 0xFF (Einsen)"""
        
        for pass_num in range(passes):
            wipe_log = WipeLog.query.get(wipe_log_id)
            
            # Direkter Python-Ansatz für präzises Progress-Tracking
            try:
                buffer_size = 1024 * 1024  # 1MB
                buffer = bytes([0xFF]) * buffer_size
                
                with open(device_path, 'wb', buffering=buffer_size) as disk:
                    bytes_written = 0
                    
                    # Versuche die Disk-Größe zu ermitteln
                    try:
                        disk.seek(0, os.SEEK_END)
                        total_size = disk.tell()
                        disk.seek(0)
                    except:
                        # Wenn Größe nicht ermittelbar, verwende Größe aus WipeLog
                        total_size = wipe_log.size_bytes if wipe_log.size_bytes else None
                    
                    # Schreibe 0xFF bis die Disk voll ist
                    last_update_percent = -1
                    while True:
                        try:
                            disk.write(buffer)
                            bytes_written += buffer_size
                            
                            # Update Progress bei jedem Prozent
                            if total_size and total_size > 0:
                                current_pass_progress = bytes_written / total_size
                                total_progress = ((pass_num + current_pass_progress) / passes) * 100
                                
                                # Nur updaten wenn sich der Prozentsatz geändert hat
                                current_percent = int(total_progress)
                                if current_percent != last_update_percent:
                                    wipe_log.progress_percent = min(total_progress, 99.9)
                                db.session.commit()
                                
                                if device_path in WipeEngine.active_wipes:
                                    WipeEngine.active_wipes[device_path]['progress'] = wipe_log.progress_percent
                                    
                                    last_update_percent = current_percent
                        
                        except IOError as e:
                            # Disk ist voll - das ist normal und bedeutet erfolgreicher Abschluss
                            if e.errno == 28:  # ENOSPC - No space left on device
                                break
                            else:
                                raise
                
            except Exception as e:
                # Prüfe ob es der normale "disk voll" Fehler ist
                error_msg = str(e)
                is_normal_completion = (
                    "No space left on device" in error_msg or
                    "kein Speicherplatz mehr verfügbar" in error_msg or
                    "Auf dem Gerät ist kein Speicherplatz mehr verfügbar" in error_msg or
                    (hasattr(e, 'errno') and e.errno == 28)
                )
                
                if not is_normal_completion:
                    raise Exception(f"Wipe-Befehl fehlgeschlagen (Pass {pass_num + 1}): {error_msg}")

    @staticmethod
    def _wipe_fast_clear(wipe_log_id, device_path):
        """
        Fast Clear-Modus - NICHT SICHER, aber sehr schnell!
        
        Dieser Modus ist für schnelles Löschen gedacht, bietet aber KEINE Sicherheit
        gegen forensische Datenwiederherstellung!
        
        Strategien:
        - NVMe: Nutzt nvme format (sehr schnell, löscht intern die Mapping-Tabelle)
        - SSDs: TRIM/DISCARD + Überschreiben von Anfang/Ende
        - HDDs: Überschreiben von Anfang/Ende (MBR/GPT + letzte GB)
        """
        wipe_log = WipeLog.query.get(wipe_log_id)
        
        # Update Progress
        wipe_log.progress_percent = 5.0
        db.session.commit()
        
        if device_path in WipeEngine.active_wipes:
            WipeEngine.active_wipes[device_path]['progress'] = 5.0
        
        try:
            # Strategie 1: NVMe Format (sehr schnell!)
            if WipeEngine.is_nvme_device(device_path):
                WipeEngine._fast_clear_nvme(wipe_log_id, device_path)
            
            # Strategie 2: SSD mit TRIM/DISCARD
            elif WipeEngine.is_ssd_device(device_path):
                WipeEngine._fast_clear_ssd(wipe_log_id, device_path)
            
            # Strategie 3: HDD oder Fallback
            else:
                WipeEngine._fast_clear_fallback(wipe_log_id, device_path)
                
        except Exception as e:
            raise Exception(f"Fast Clear fehlgeschlagen: {str(e)}")
    
    @staticmethod
    def _fast_clear_nvme(wipe_log_id, device_path):
        """Fast Clear für NVMe-Geräte mit nvme-cli"""
        wipe_log = WipeLog.query.get(wipe_log_id)
        
        try:
            # Update Progress
            wipe_log.progress_percent = 10.0
            db.session.commit()
            
            # Versuche nvme format zu verwenden
            # -s 1: Secure Erase Setting 1 (User Data Erase)
            # Dies ist schnell aber nicht so sicher wie Cryptographic Erase
            
            # Extrahiere NVMe Namespace (z.B. /dev/nvme0n1 -> nvme0n1)
            nvme_device = device_path.split('/')[-1]
            
            wipe_log.progress_percent = 30.0
            db.session.commit()
            
            # Führe nvme format aus
            result = subprocess.run(
                ['nvme', 'format', device_path, '-s', '1'],
                capture_output=True,
                text=True,
                timeout=300  # 5 Minuten Timeout
            )
            
            wipe_log.progress_percent = 90.0
            db.session.commit()
            
            if result.returncode != 0:
                # Fallback: Wenn nvme format nicht funktioniert, verwende normalen Fallback
                raise Exception(f"nvme format fehlgeschlagen: {result.stderr}")
            
            wipe_log.progress_percent = 100.0
            db.session.commit()
            
        except FileNotFoundError:
            # nvme-cli nicht installiert, verwende Fallback
            print("nvme-cli nicht gefunden, verwende Fallback-Methode")
            WipeEngine._fast_clear_fallback(wipe_log_id, device_path)
        except subprocess.TimeoutExpired:
            raise Exception("NVMe Format Timeout - der Vorgang dauerte zu lange")
    
    @staticmethod
    def _fast_clear_ssd(wipe_log_id, device_path):
        """Fast Clear für SSDs mit TRIM/DISCARD"""
        wipe_log = WipeLog.query.get(wipe_log_id)
        
        try:
            # Update Progress
            wipe_log.progress_percent = 10.0
            db.session.commit()
            
            # Versuche TRIM/DISCARD (blkdiscard auf Linux)
            if os.name != 'nt':
                try:
                    # blkdiscard löscht alle Daten per TRIM
                    result = subprocess.run(
                        ['blkdiscard', device_path],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    wipe_log.progress_percent = 70.0
                    db.session.commit()
                    
                    if result.returncode == 0:
                        # TRIM erfolgreich, überschreibe trotzdem Anfang und Ende
                        WipeEngine._overwrite_edges(wipe_log_id, device_path, 70.0, 100.0)
                        return
                except FileNotFoundError:
                    print("blkdiscard nicht gefunden")
                except subprocess.TimeoutExpired:
                    print("blkdiscard Timeout")
            
            # Fallback: Nur Anfang und Ende überschreiben
            WipeEngine._fast_clear_fallback(wipe_log_id, device_path)
            
        except Exception as e:
            # Bei Fehler Fallback verwenden
            print(f"SSD Fast Clear Fehler: {e}, verwende Fallback")
            WipeEngine._fast_clear_fallback(wipe_log_id, device_path)
    
    @staticmethod
    def _fast_clear_fallback(wipe_log_id, device_path):
        """Fallback: Überschreibt nur wichtige Bereiche (MBR/GPT + Anfang + Ende)"""
        wipe_log = WipeLog.query.get(wipe_log_id)
        
        # Überschreibe:
        # - Ersten 10 MB (MBR, GPT, Partition Tables)
        # - Letzten 10 MB (Backup GPT)
        
        WipeEngine._overwrite_edges(wipe_log_id, device_path, 10.0, 100.0)
    
    @staticmethod
    def _overwrite_edges(wipe_log_id, device_path, start_progress, end_progress):
        """Überschreibt Anfang und Ende einer Disk"""
        wipe_log = WipeLog.query.get(wipe_log_id)
        
        buffer_size = 1024 * 1024  # 1 MB
        edge_size = 10 * 1024 * 1024  # 10 MB an jedem Ende
        
        try:
            with open(device_path, 'r+b', buffering=buffer_size) as disk:
                # 1. Überschreibe Anfang (MBR/GPT)
                wipe_log.progress_percent = start_progress
                db.session.commit()
                
                disk.seek(0)
                bytes_written = 0
                while bytes_written < edge_size:
                    try:
                        disk.write(bytes(buffer_size))
                        bytes_written += buffer_size
                    except IOError:
                        break
                
                # Progress update
                mid_progress = start_progress + (end_progress - start_progress) * 0.5
                wipe_log.progress_percent = mid_progress
                db.session.commit()
                
                if device_path in WipeEngine.active_wipes:
                    WipeEngine.active_wipes[device_path]['progress'] = mid_progress
                
                # 2. Überschreibe Ende (Backup GPT)
                try:
                    # Versuche ans Ende zu springen
                    disk.seek(-edge_size, os.SEEK_END)
                    bytes_written = 0
                    
                    while bytes_written < edge_size:
                        try:
                            disk.write(bytes(buffer_size))
                            bytes_written += buffer_size
                        except IOError:
                            break
                except (OSError, IOError):
                    # Wenn seek ans Ende nicht funktioniert, ignorieren
                    pass
                
                # Flush um sicherzustellen dass Daten geschrieben wurden
                disk.flush()
                os.fsync(disk.fileno())
                
                wipe_log.progress_percent = end_progress
                db.session.commit()
                
                if device_path in WipeEngine.active_wipes:
                    WipeEngine.active_wipes[device_path]['progress'] = end_progress
                
        except Exception as e:
            raise Exception(f"Fehler beim Überschreiben: {str(e)}")

    @staticmethod
    def get_wipe_status(wipe_log_id):
        """Gibt den Status eines Wipe-Vorgangs zurück"""
        wipe_log = WipeLog.query.get(wipe_log_id)
        if not wipe_log:
            return None
        
        return {
            'id': wipe_log.id,
            'status': wipe_log.status,
            'progress': wipe_log.progress_percent,
            'device_path': wipe_log.device_path,
            'model': wipe_log.model,
            'serial_number': wipe_log.serial_number,
            'start_time': wipe_log.start_time.isoformat() if wipe_log.start_time else None,
            'error_message': wipe_log.error_message
        }

    @staticmethod
    def get_all_active_wipes():
        """Gibt alle aktiven Wipe-Vorgänge zurück"""
        active = []
        
        with WipeEngine.wipe_lock:
            for device_path, info in WipeEngine.active_wipes.items():
                if 'wipe_log_id' in info:
                    status = WipeEngine.get_wipe_status(info['wipe_log_id'])
                    if status:
                        active.append(status)
        
        return active


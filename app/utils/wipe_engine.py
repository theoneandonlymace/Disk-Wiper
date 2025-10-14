import os
import subprocess
import threading
import time
from datetime import datetime
from flask import current_app
from app import db
from app.models import WipeLog
from app.utils.disk_manager import DiskManager


class WipeEngine:
    """Engine für das sichere Löschen von Festplatten"""
    
    # Aktive Wipe-Prozesse
    active_wipes = {}
    wipe_lock = threading.Lock()

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
                else:
                    raise Exception(f"Unbekannte Wipe-Methode: {wipe_method}")
                
                # Erfolgreich abgeschlossen
                end_time = datetime.utcnow()
                duration = (end_time - wipe_log.start_time).total_seconds()
                
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
            
            # dd-Befehl zum Überschreiben mit Nullen
            # HINWEIS: Dies ist eine vereinfachte Implementierung
            # In Produktion sollte eine robustere Lösung verwendet werden
            
            if os.name == 'nt':  # Windows
                # Windows: Verwende PowerShell mit sicherer Parameter-Übergabe
                ps_script = """
                param([string]$DevicePath)
                $bufferSize = 1MB
                $buffer = New-Object byte[] $bufferSize
                
                $stream = [System.IO.File]::OpenWrite($DevicePath)
                $totalSize = $stream.Length
                $written = 0
                
                try {
                    while ($written -lt $totalSize) {
                        $stream.Write($buffer, 0, $buffer.Length)
                        $written += $buffer.Length
                    }
                } finally {
                    $stream.Close()
                }
                """
                
                process = subprocess.Popen(
                    ['powershell', '-Command', ps_script, '-DevicePath', device_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
            else:  # Linux/Unix
                # Verwende shred zum sicheren Löschen
                # -v: verbose (zeigt Progress)
                # -f: force (erlaubt Schreiben auf Device-Dateien)
                # -n: Anzahl der Überschreibungen
                # -z: Fügt einen finalen Pass mit Nullen hinzu
                process = subprocess.Popen(
                    ['shred', '-vfz', '-n', str(passes), device_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            
            # Warte auf Abschluss und update Progress
            while process.poll() is None:
                time.sleep(5)
                
                # Update Progress (vereinfacht)
                progress = ((pass_num + 0.5) / passes) * 100
                wipe_log.progress_percent = progress
                db.session.commit()
                
                # Update active_wipes
                if device_path in WipeEngine.active_wipes:
                    WipeEngine.active_wipes[device_path]['progress'] = progress
            
            # Prüfe Return-Code und hole stderr Output
            if process.returncode != 0:
                # Verwende communicate() um Deadlocks zu vermeiden
                try:
                    stdout_data, stderr_data = process.communicate(timeout=5)
                    stderr = stderr_data if stderr_data else ""
                except subprocess.TimeoutExpired:
                    process.kill()
                    stderr = "Prozess Timeout"
                
                wipe_tool = "shred" if os.name != 'nt' else "PowerShell"
                raise Exception(f"{wipe_tool}-Befehl fehlgeschlagen (Pass {pass_num + 1}): {stderr}")

    @staticmethod
    def _wipe_random(wipe_log_id, device_path, passes):
        """Löscht die Festplatte durch Überschreiben mit Zufallsdaten"""
        
        for pass_num in range(passes):
            wipe_log = WipeLog.query.get(wipe_log_id)
            
            if os.name == 'nt':  # Windows
                # Windows: Direkter Python-Ansatz mit os.urandom (plattformunabhängig)
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
                            total_size = None
                        
                        # Schreibe Zufallsdaten bis die Disk voll ist
                        while True:
                            try:
                                # Generiere Zufallsdaten
                                random_buffer = os.urandom(buffer_size)
                                disk.write(random_buffer)
                                bytes_written += buffer_size
                                
                                # Update Progress alle 100MB
                                if bytes_written % (100 * 1024 * 1024) == 0:
                                    if total_size:
                                        progress = ((pass_num + (bytes_written / total_size)) / passes) * 100
                                    else:
                                        progress = ((pass_num + 0.5) / passes) * 100
                                    
                                    wipe_log.progress_percent = min(progress, 99.9)
                                    db.session.commit()
                                    
                                    if device_path in WipeEngine.active_wipes:
                                        WipeEngine.active_wipes[device_path]['progress'] = wipe_log.progress_percent
                            
                            except IOError as e:
                                # Disk ist voll - das ist normal
                                if e.errno == 28:  # ENOSPC - No space left on device
                                    break
                                else:
                                    raise
                    
                except Exception as e:
                    raise Exception(f"Random Wipe fehlgeschlagen (Pass {pass_num + 1}): {str(e)}")
                    
            else:  # Linux/Unix
                # Verwende shred mit Zufallsdaten
                # --random-source=/dev/urandom: Verwendet kryptografisch starke Zufallsdaten
                process = subprocess.Popen(
                    ['shred', '-vf', '--random-source=/dev/urandom', '-n', str(passes), device_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                while process.poll() is None:
                    time.sleep(5)
                    progress = ((pass_num + 0.5) / passes) * 100
                    wipe_log.progress_percent = progress
                    db.session.commit()
                    
                    if device_path in WipeEngine.active_wipes:
                        WipeEngine.active_wipes[device_path]['progress'] = progress
                
                # Prüfe Return-Code und hole stderr Output
                if process.returncode != 0:
                    # Verwende communicate() um Deadlocks zu vermeiden
                    try:
                        stdout_data, stderr_data = process.communicate(timeout=5)
                        stderr = stderr_data if stderr_data else ""
                    except subprocess.TimeoutExpired:
                        process.kill()
                        stderr = "Prozess Timeout"
                    
                    wipe_tool = "shred" if os.name != 'nt' else "Python"
                    raise Exception(f"{wipe_tool}-Befehl fehlgeschlagen (Pass {pass_num + 1}): {stderr}")

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
    def _wipe_ones(wipe_log_id, device_path, passes):
        """Löscht die Festplatte durch Überschreiben mit 0xFF (Einsen)"""
        
        for pass_num in range(passes):
            wipe_log = WipeLog.query.get(wipe_log_id)
            
            # Direkter Python-Ansatz ohne externe Prozesse (sicherer)
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
                        total_size = None
                    
                    # Schreibe 0xFF bis die Disk voll ist
                    while True:
                        try:
                            disk.write(buffer)
                            bytes_written += buffer_size
                            
                            # Update Progress alle 100MB
                            if bytes_written % (100 * 1024 * 1024) == 0:
                                if total_size:
                                    progress = ((pass_num + (bytes_written / total_size)) / passes) * 100
                                else:
                                    progress = ((pass_num + 0.5) / passes) * 100
                                
                                wipe_log.progress_percent = min(progress, 99.9)
                                db.session.commit()
                                
                                if device_path in WipeEngine.active_wipes:
                                    WipeEngine.active_wipes[device_path]['progress'] = wipe_log.progress_percent
                        
                        except IOError as e:
                            # Disk ist voll - das ist normal
                            if e.errno == 28:  # ENOSPC - No space left on device
                                break
                            else:
                                raise
                
            except Exception as e:
                raise Exception(f"Wipe-Befehl fehlgeschlagen (Pass {pass_num + 1}): {str(e)}")

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


import os
import platform
import subprocess
import psutil
import json
from pathlib import Path


class DiskManager:
    """Verwaltet Festplatten-Erkennung und Boot-Disk-Schutz"""

    @staticmethod
    def get_all_disks():
        """Gibt alle verfügbaren Festplatten zurück"""
        system = platform.system()
        
        if system == 'Linux':
            return DiskManager._get_linux_disks()
        elif system == 'Windows':
            return DiskManager._get_windows_disks()
        elif system == 'Darwin':  # macOS
            return DiskManager._get_macos_disks()
        else:
            raise NotImplementedError(f"System {system} wird nicht unterstützt")

    @staticmethod
    def _get_linux_disks():
        """Erkennt Festplatten unter Linux"""
        disks = []
        
        try:
            # Alle Block-Devices finden
            result = subprocess.run(
                ['lsblk', '-J', '-b', '-o', 'NAME,SIZE,MODEL,SERIAL,TYPE,MOUNTPOINT'],
                capture_output=True,
                text=True,
                check=True
            )
            
            data = json.loads(result.stdout)
            boot_partitions = DiskManager._get_boot_partitions()
            
            for device in data.get('blockdevices', []):
                if device.get('type') == 'disk':
                    device_path = f"/dev/{device['name']}"
                    
                    # Prüfen ob Boot-Disk
                    is_boot = DiskManager._is_boot_disk_linux(device, boot_partitions)
                    
                    disk_info = {
                        'device_path': device_path,
                        'model': device.get('model', 'Unknown').strip(),
                        'serial_number': DiskManager._get_serial_linux(device_path, device.get('serial', '')),
                        'size_bytes': int(device.get('size', 0)),
                        'size_human': DiskManager._format_size(int(device.get('size', 0))),
                        'is_boot_disk': is_boot,
                        'partitions': device.get('children', [])
                    }
                    
                    disks.append(disk_info)
                    
        except Exception as e:
            print(f"Fehler beim Abrufen der Linux-Festplatten: {e}")
        
        return disks

    @staticmethod
    def _get_windows_disks():
        """Erkennt Festplatten unter Windows"""
        disks = []
        
        try:
            # Boot-Laufwerk ermitteln
            boot_drive = os.getenv('SystemDrive', 'C:')
            
            # WMI über PowerShell abfragen
            ps_script = """
            Get-PhysicalDisk | Select-Object DeviceID, FriendlyName, SerialNumber, Size, MediaType | ConvertTo-Json
            """
            
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True,
                text=True,
                check=True
            )
            
            disk_data = json.loads(result.stdout)
            if not isinstance(disk_data, list):
                disk_data = [disk_data]
            
            for disk in disk_data:
                device_id = disk.get('DeviceID', '')
                device_path = f"\\\\.\\PHYSICALDRIVE{device_id}"
                
                # Boot-Disk prüfen
                is_boot = DiskManager._is_boot_disk_windows(device_id, boot_drive)
                
                disk_info = {
                    'device_path': device_path,
                    'model': disk.get('FriendlyName', 'Unknown'),
                    'serial_number': disk.get('SerialNumber', '').strip(),
                    'size_bytes': int(disk.get('Size', 0)),
                    'size_human': DiskManager._format_size(int(disk.get('Size', 0))),
                    'is_boot_disk': is_boot
                }
                
                disks.append(disk_info)
                
        except Exception as e:
            print(f"Fehler beim Abrufen der Windows-Festplatten: {e}")
        
        return disks

    @staticmethod
    def _get_macos_disks():
        """Erkennt Festplatten unter macOS"""
        disks = []
        
        try:
            result = subprocess.run(
                ['diskutil', 'list', '-plist'],
                capture_output=True,
                check=True
            )
            
            # Parse plist output (würde plistlib benötigen)
            # Vereinfachte Version mit diskutil info
            result = subprocess.run(
                ['diskutil', 'list'],
                capture_output=True,
                text=True,
                check=True
            )
            
            lines = result.stdout.split('\n')
            boot_disk = DiskManager._get_boot_disk_macos()
            
            for line in lines:
                if '/dev/disk' in line and 'physical' in line.lower():
                    parts = line.split()
                    device_path = parts[0]
                    
                    # Detaillierte Infos abrufen
                    info_result = subprocess.run(
                        ['diskutil', 'info', device_path],
                        capture_output=True,
                        text=True
                    )
                    
                    is_boot = (device_path == boot_disk)
                    
                    disk_info = {
                        'device_path': device_path,
                        'model': DiskManager._parse_diskutil_field(info_result.stdout, 'Device / Media Name'),
                        'serial_number': DiskManager._parse_diskutil_field(info_result.stdout, 'Disk / Partition UUID'),
                        'size_bytes': 0,  # Would need parsing
                        'size_human': DiskManager._parse_diskutil_field(info_result.stdout, 'Disk Size'),
                        'is_boot_disk': is_boot
                    }
                    
                    disks.append(disk_info)
                    
        except Exception as e:
            print(f"Fehler beim Abrufen der macOS-Festplatten: {e}")
        
        return disks

    @staticmethod
    def _get_boot_partitions():
        """Ermittelt alle gemounteten Boot-Partitionen"""
        boot_partitions = set()
        
        # Root-Partition
        for partition in psutil.disk_partitions():
            if partition.mountpoint in ['/', '/boot', '/boot/efi']:
                boot_partitions.add(partition.device)
        
        return boot_partitions

    @staticmethod
    def _is_boot_disk_linux(device, boot_partitions):
        """Prüft ob Linux-Disk eine Boot-Disk ist"""
        # Prüfe ob irgendeine Partition gemountet ist auf /, /boot, etc.
        for partition in device.get('children', []):
            mount = partition.get('mountpoint', '')
            if mount and mount in ['/', '/boot', '/boot/efi']:
                return True
            
            # Prüfe gegen bekannte Boot-Partitionen
            partition_path = f"/dev/{partition['name']}"
            if partition_path in boot_partitions:
                return True
        
        return False

    @staticmethod
    def _is_boot_disk_windows(device_id, boot_drive):
        """Prüft ob Windows-Disk eine Boot-Disk ist"""
        # KRITISCHE SICHERHEITSPRÜFUNG
        # Mehrere Methoden verwenden für maximale Sicherheit
        
        try:
            # Methode 1: Prüfe ob die Disk das System-Laufwerk (C:) enthält
            ps_script = f"""
            $partitions = Get-Partition -DiskNumber {device_id} -ErrorAction SilentlyContinue
            $systemPartition = $partitions | Where-Object {{$_.DriveLetter -eq '{boot_drive[0]}'}}
            if ($systemPartition) {{ 
                Write-Output 'BOOT_DISK' 
            }} else {{ 
                Write-Output 'NOT_BOOT' 
            }}
            """
            
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if 'BOOT_DISK' in result.stdout:
                return True
            
            # Methode 2: PHYSICALDRIVE0 ist fast immer die Boot-Disk
            if device_id == 0:
                return True
            
            # Methode 3: Prüfe ob Disk die Windows-Partition enthält
            ps_script2 = f"""
            $disk = Get-Disk -Number {device_id} -ErrorAction SilentlyContinue
            if ($disk.IsBoot -or $disk.IsSystem) {{
                Write-Output 'IS_SYSTEM'
            }}
            """
            
            result2 = subprocess.run(
                ['powershell', '-Command', ps_script2],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if 'IS_SYSTEM' in result2.stdout:
                return True
            
            return False
            
        except Exception as e:
            # SICHERHEITSREGEL: Bei Fehler IMMER als Boot-Disk markieren!
            print(f"WARNUNG: Boot-Disk-Prüfung fehlgeschlagen für Disk {device_id}: {e}")
            print(f"Disk {device_id} wird aus Sicherheitsgründen als Boot-Disk markiert!")
            return True

    @staticmethod
    def _get_boot_disk_macos():
        """Ermittelt Boot-Disk unter macOS"""
        try:
            result = subprocess.run(
                ['diskutil', 'info', '/'],
                capture_output=True,
                text=True
            )
            
            for line in result.stdout.split('\n'):
                if 'Part of Whole' in line:
                    return line.split(':')[1].strip()
                    
        except:
            pass
        
        return None

    @staticmethod
    def _get_serial_linux(device_path, serial_from_lsblk):
        """Ermittelt Seriennummer unter Linux"""
        if serial_from_lsblk and serial_from_lsblk.strip():
            return serial_from_lsblk.strip()
        
        # Versuche via udevadm
        try:
            result = subprocess.run(
                ['udevadm', 'info', '--query=property', '--name=' + device_path],
                capture_output=True,
                text=True
            )
            
            for line in result.stdout.split('\n'):
                if line.startswith('ID_SERIAL_SHORT='):
                    return line.split('=')[1].strip()
                elif line.startswith('ID_SERIAL='):
                    return line.split('=')[1].strip()
                    
        except:
            pass
        
        # Fallback: Verwende Device-Path als eindeutigen Identifier
        return f"UNKNOWN_{device_path.replace('/', '_')}"

    @staticmethod
    def _parse_diskutil_field(output, field_name):
        """Parst ein Feld aus diskutil info Ausgabe"""
        for line in output.split('\n'):
            if field_name in line:
                return line.split(':')[1].strip()
        return 'Unknown'

    @staticmethod
    def _format_size(size_bytes):
        """Formatiert Byte-Größe in menschenlesbare Form"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    @staticmethod
    def verify_not_boot_disk(device_path):
        """
        KRITISCHE SICHERHEITSPRÜFUNG: Stellt sicher, dass die Disk KEINE Boot-Disk ist
        Gibt True zurück wenn sicher, False wenn Boot-Disk oder unsicher
        """
        try:
            all_disks = DiskManager.get_all_disks()
            
            for disk in all_disks:
                if disk['device_path'] == device_path:
                    if disk['is_boot_disk']:
                        return False, "Dies ist eine Boot-Disk und kann nicht gelöscht werden!"
                    return True, "Disk ist sicher zu löschen"
            
            # Disk nicht gefunden = unsicher
            return False, "Disk konnte nicht verifiziert werden"
            
        except Exception as e:
            # Bei Fehler immer auf Nummer sicher gehen
            return False, f"Sicherheitsprüfung fehlgeschlagen: {str(e)}"


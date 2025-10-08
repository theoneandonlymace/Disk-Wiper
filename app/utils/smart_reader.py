import subprocess
import json
import platform


class SmartReader:
    """Liest SMART-Daten von Festplatten aus"""

    @staticmethod
    def get_smart_data(device_path):
        """
        Liest SMART-Daten einer Festplatte aus
        Gibt ein Dictionary mit SMART-Informationen zurück
        """
        system = platform.system()
        
        try:
            if system == 'Linux':
                return SmartReader._get_smart_linux(device_path)
            elif system == 'Windows':
                return SmartReader._get_smart_windows(device_path)
            elif system == 'Darwin':
                return SmartReader._get_smart_macos(device_path)
            else:
                return {'error': f'System {system} nicht unterstützt'}
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _get_smart_linux(device_path):
        """Liest SMART-Daten unter Linux via smartctl"""
        try:
            # Prüfe ob smartctl verfügbar ist
            result = subprocess.run(
                ['which', 'smartctl'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return {'error': 'smartctl nicht installiert. Bitte smartmontools installieren.'}
            
            # SMART-Daten als JSON abrufen
            result = subprocess.run(
                ['smartctl', '-a', '-j', device_path],
                capture_output=True,
                text=True
            )
            
            data = json.loads(result.stdout)
            
            # Extrahiere wichtige Informationen
            smart_info = {
                'device': device_path,
                'model': data.get('model_name', 'Unknown'),
                'serial': data.get('serial_number', 'Unknown'),
                'firmware': data.get('firmware_version', 'Unknown'),
                'capacity': data.get('user_capacity', {}).get('bytes', 0),
                'smart_status': 'PASSED' if data.get('smart_status', {}).get('passed', False) else 'FAILED',
                'power_on_hours': 0,
                'power_cycle_count': 0,
                'temperature': None,
                'attributes': {},
                'raw_data': json.dumps(data)
            }
            
            # Parse SMART-Attribute
            attributes = data.get('ata_smart_attributes', {}).get('table', [])
            for attr in attributes:
                attr_name = attr.get('name', '')
                attr_value = attr.get('value', 0)
                attr_raw = attr.get('raw', {}).get('value', 0)
                
                smart_info['attributes'][attr_name] = {
                    'value': attr_value,
                    'raw': attr_raw
                }
                
                # Spezielle Attribute extrahieren
                if attr_name == 'Power_On_Hours':
                    smart_info['power_on_hours'] = attr_raw
                elif attr_name == 'Power_Cycle_Count':
                    smart_info['power_cycle_count'] = attr_raw
                elif 'Temperature' in attr_name:
                    smart_info['temperature'] = attr_raw
            
            return smart_info
            
        except json.JSONDecodeError:
            # Fallback: Parse Text-Ausgabe
            return SmartReader._parse_smart_text_linux(device_path)
        except Exception as e:
            return {'error': f'Fehler beim Lesen der SMART-Daten: {str(e)}'}

    @staticmethod
    def _parse_smart_text_linux(device_path):
        """Fallback: Parse SMART-Daten aus Text-Ausgabe"""
        try:
            result = subprocess.run(
                ['smartctl', '-a', device_path],
                capture_output=True,
                text=True
            )
            
            smart_info = {
                'device': device_path,
                'model': 'Unknown',
                'serial': 'Unknown',
                'smart_status': 'UNKNOWN',
                'raw_data': result.stdout
            }
            
            for line in result.stdout.split('\n'):
                if 'Device Model:' in line:
                    smart_info['model'] = line.split(':')[1].strip()
                elif 'Serial Number:' in line:
                    smart_info['serial'] = line.split(':')[1].strip()
                elif 'SMART overall-health' in line:
                    if 'PASSED' in line:
                        smart_info['smart_status'] = 'PASSED'
                    else:
                        smart_info['smart_status'] = 'FAILED'
            
            return smart_info
            
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _get_smart_windows(device_path):
        """Liest SMART-Daten unter Windows"""
        try:
            # Extrahiere Disk-Nummer aus Path
            disk_num = device_path.replace('\\\\.\\PHYSICALDRIVE', '')
            
            # PowerShell-Skript für SMART-Daten (mit sicherer Parameter-Übergabe)
            ps_script = """
            param([int]$DeviceNumber)
            $disk = Get-PhysicalDisk -DeviceNumber $DeviceNumber
            $smart = Get-StorageReliabilityCounter -PhysicalDisk $disk
            
            $result = @{
                'model' = $disk.FriendlyName
                'serial' = $disk.SerialNumber
                'health_status' = $disk.HealthStatus
                'operational_status' = $disk.OperationalStatus
                'power_on_hours' = $smart.PowerOnHours
                'temperature' = $smart.Temperature
                'wear' = $smart.Wear
            }
            
            $result | ConvertTo-Json
            """
            
            result = subprocess.run(
                ['powershell', '-Command', ps_script, '-DeviceNumber', disk_num],
                capture_output=True,
                text=True
            )
            
            data = json.loads(result.stdout)
            
            smart_info = {
                'device': device_path,
                'model': data.get('model', 'Unknown'),
                'serial': data.get('serial', 'Unknown'),
                'smart_status': data.get('health_status', 'Unknown'),
                'power_on_hours': data.get('power_on_hours', 0),
                'temperature': data.get('temperature', None),
                'raw_data': json.dumps(data)
            }
            
            return smart_info
            
        except Exception as e:
            return {'error': f'Fehler beim Lesen der Windows SMART-Daten: {str(e)}'}

    @staticmethod
    def _get_smart_macos(device_path):
        """Liest SMART-Daten unter macOS"""
        try:
            result = subprocess.run(
                ['smartctl', '-a', device_path],
                capture_output=True,
                text=True
            )
            
            # Ähnlich wie Linux-Parsing
            smart_info = {
                'device': device_path,
                'model': 'Unknown',
                'serial': 'Unknown',
                'smart_status': 'UNKNOWN',
                'raw_data': result.stdout
            }
            
            for line in result.stdout.split('\n'):
                if 'Device Model:' in line or 'Model:' in line:
                    smart_info['model'] = line.split(':')[1].strip()
                elif 'Serial Number:' in line or 'Serial number:' in line:
                    smart_info['serial'] = line.split(':')[1].strip()
                elif 'SMART overall-health' in line or 'SMART Health Status:' in line:
                    if 'PASSED' in line.upper() or 'OK' in line.upper():
                        smart_info['smart_status'] = 'PASSED'
                    else:
                        smart_info['smart_status'] = 'FAILED'
            
            return smart_info
            
        except Exception as e:
            return {'error': f'Fehler beim Lesen der macOS SMART-Daten: {str(e)}'}

    @staticmethod
    def format_smart_summary(smart_data):
        """Erstellt eine lesbare Zusammenfassung der SMART-Daten"""
        if 'error' in smart_data:
            return f"Fehler: {smart_data['error']}"
        
        summary = []
        summary.append(f"Modell: {smart_data.get('model', 'N/A')}")
        summary.append(f"Seriennummer: {smart_data.get('serial', 'N/A')}")
        summary.append(f"SMART-Status: {smart_data.get('smart_status', 'N/A')}")
        
        if smart_data.get('power_on_hours'):
            hours = smart_data['power_on_hours']
            days = hours / 24
            summary.append(f"Betriebsstunden: {hours} h ({days:.1f} Tage)")
        
        if smart_data.get('temperature'):
            summary.append(f"Temperatur: {smart_data['temperature']} °C")
        
        return "\n".join(summary)


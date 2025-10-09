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
            
            # Vereinfachtes PowerShell-Skript ohne Get-StorageReliabilityCounter
            # (benötigt oft Admin-Rechte und ist nicht immer verfügbar)
            ps_script = """
            param([int]$DeviceNumber)
            try {
                $disk = Get-PhysicalDisk -DeviceNumber $DeviceNumber
                
                $result = @{
                    'model' = $disk.FriendlyName
                    'serial' = $disk.SerialNumber
                    'health_status' = $disk.HealthStatus.ToString()
                    'operational_status' = $disk.OperationalStatus.ToString()
                    'media_type' = $disk.MediaType.ToString()
                    'bus_type' = $disk.BusType.ToString()
                    'size_bytes' = $disk.Size
                }
                
                # Versuche StorageReliabilityCounter zu lesen (funktioniert nicht immer)
                try {
                    $smart = Get-StorageReliabilityCounter -PhysicalDisk $disk -ErrorAction SilentlyContinue
                    if ($smart) {
                        $result['power_on_hours'] = $smart.PowerOnHours
                        $result['temperature'] = $smart.Temperature
                        $result['wear'] = $smart.Wear
                        $result['read_errors'] = $smart.ReadErrorsTotal
                        $result['write_errors'] = $smart.WriteErrorsTotal
                    }
                } catch {
                    # Ignoriere Fehler beim Lesen der Reliability-Daten
                }
                
                $result | ConvertTo-Json
            } catch {
                @{'error' = $_.Exception.Message} | ConvertTo-Json
            }
            """
            
            result = subprocess.run(
                ['powershell', '-Command', ps_script, '-DeviceNumber', disk_num],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Sichere Konvertierung der Werte
            def safe_int(value):
                """Konvertiert Wert sicher zu Int, gibt None zurück bei Fehler"""
                if value is None or value == '':
                    return None
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return None
            
            # Parse JSON-Antwort
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                return {
                    'error': f'PowerShell-Antwort konnte nicht geparst werden',
                    'raw_output': result.stdout,
                    'raw_error': result.stderr
                }
            
            # Prüfe auf Fehler in der Antwort
            if 'error' in data:
                return {'error': f'PowerShell-Fehler: {data["error"]}'}
            
            smart_info = {
                'device': device_path,
                'model': data.get('model', 'Unknown'),
                'serial': data.get('serial', 'Unknown'),
                'smart_status': data.get('health_status', 'Unknown'),
                'health_status': data.get('health_status', 'Unknown'),
                'operational_status': data.get('operational_status', 'Unknown'),
                'media_type': data.get('media_type'),
                'bus_type': data.get('bus_type'),
                'size_bytes': safe_int(data.get('size_bytes')),
                'power_on_hours': safe_int(data.get('power_on_hours')),
                'temperature': safe_int(data.get('temperature')),
                'wear': safe_int(data.get('wear')),
                'read_errors': safe_int(data.get('read_errors')),
                'write_errors': safe_int(data.get('write_errors')),
                'raw_data': json.dumps(data, indent=2)
            }
            
            return smart_info
            
        except subprocess.TimeoutExpired:
            return {'error': 'PowerShell-Timeout: Vorgang dauerte zu lange'}
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


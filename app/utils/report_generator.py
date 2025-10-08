from datetime import datetime
import json


class ReportGenerator:
    """Generiert Reports für Wipe-Vorgänge"""

    @staticmethod
    def generate_wipe_report(wipe_log):
        """Erstellt einen detaillierten Report für einen Wipe-Vorgang"""
        
        report = {
            'report_type': 'Disk Wipe Report',
            'generated_at': datetime.utcnow().isoformat(),
            'wipe_information': {
                'id': wipe_log.id,
                'status': wipe_log.status,
                'device_path': wipe_log.device_path,
                'model': wipe_log.model,
                'serial_number': wipe_log.serial_number,
                'size_bytes': wipe_log.size_bytes,
                'size_human': ReportGenerator._format_size(wipe_log.size_bytes) if wipe_log.size_bytes else 'N/A',
                'wipe_method': wipe_log.wipe_method,
                'wipe_passes': wipe_log.wipe_passes,
            },
            'timing': {
                'start_time': wipe_log.start_time.isoformat() if wipe_log.start_time else None,
                'end_time': wipe_log.end_time.isoformat() if wipe_log.end_time else None,
                'duration_seconds': wipe_log.duration_seconds,
                'duration_human': ReportGenerator._format_duration(wipe_log.duration_seconds) if wipe_log.duration_seconds else 'N/A'
            },
            'verification': {
                'verified': wipe_log.verified,
                'verification_data': wipe_log.verification_data
            }
        }
        
        # SMART-Daten hinzufügen falls vorhanden
        if wipe_log.smart_data_before:
            try:
                smart_data = json.loads(wipe_log.smart_data_before)
                report['smart_data_before_wipe'] = smart_data
            except:
                report['smart_data_before_wipe'] = wipe_log.smart_data_before
        
        # Fehler hinzufügen falls vorhanden
        if wipe_log.error_message:
            report['error'] = wipe_log.error_message
        
        return report

    @staticmethod
    def generate_html_report(wipe_log):
        """Erstellt einen HTML-Report für einen Wipe-Vorgang"""
        
        report_data = ReportGenerator.generate_wipe_report(wipe_log)
        
        # Status-Badge-Farbe
        status_color = {
            'completed': 'green',
            'failed': 'red',
            'in_progress': 'blue',
            'pending': 'gray'
        }.get(wipe_log.status, 'gray')
        
        html = f"""
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Disk Wipe Report - {wipe_log.serial_number}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .report-container {{
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            border-bottom: 3px solid #2563eb;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            color: #1e40af;
        }}
        .status-badge {{
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            font-weight: bold;
            text-transform: uppercase;
            font-size: 14px;
            background-color: {status_color};
            color: white;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section-title {{
            font-size: 20px;
            font-weight: bold;
            color: #1e40af;
            margin-bottom: 15px;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 8px;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: 200px 1fr;
            gap: 12px;
            line-height: 1.8;
        }}
        .info-label {{
            font-weight: bold;
            color: #4b5563;
        }}
        .info-value {{
            color: #1f2937;
        }}
        .success {{
            color: green;
            font-weight: bold;
        }}
        .error {{
            color: red;
            font-weight: bold;
            background-color: #fee;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid red;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e5e7eb;
            color: #6b7280;
            font-size: 14px;
            text-align: center;
        }}
        .smart-data {{
            background: #f9fafb;
            padding: 15px;
            border-radius: 6px;
            border: 1px solid #e5e7eb;
            max-height: 400px;
            overflow-y: auto;
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <div class="header">
            <h1>🗑️ Disk Wipe Report</h1>
            <p>Generiert am: {report_data['generated_at']}</p>
            <div class="status-badge">{wipe_log.status}</div>
        </div>
        
        <div class="section">
            <div class="section-title">Festplatten-Informationen</div>
            <div class="info-grid">
                <div class="info-label">Modell:</div>
                <div class="info-value">{wipe_log.model or 'N/A'}</div>
                
                <div class="info-label">Seriennummer:</div>
                <div class="info-value">{wipe_log.serial_number}</div>
                
                <div class="info-label">Device Path:</div>
                <div class="info-value">{wipe_log.device_path}</div>
                
                <div class="info-label">Größe:</div>
                <div class="info-value">{report_data['wipe_information']['size_human']}</div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">Wipe-Vorgang</div>
            <div class="info-grid">
                <div class="info-label">Methode:</div>
                <div class="info-value">{wipe_log.wipe_method}</div>
                
                <div class="info-label">Anzahl Pässe:</div>
                <div class="info-value">{wipe_log.wipe_passes}</div>
                
                <div class="info-label">Startzeit:</div>
                <div class="info-value">{report_data['timing']['start_time'] or 'N/A'}</div>
                
                <div class="info-label">Endzeit:</div>
                <div class="info-value">{report_data['timing']['end_time'] or 'N/A'}</div>
                
                <div class="info-label">Dauer:</div>
                <div class="info-value">{report_data['timing']['duration_human']}</div>
                
                <div class="info-label">Verifiziert:</div>
                <div class="info-value {'success' if wipe_log.verified else ''}">
                    {'✓ Ja' if wipe_log.verified else '✗ Nein'}
                </div>
            </div>
        </div>
        
        {'<div class="section"><div class="section-title">Fehler</div><div class="error">' + wipe_log.error_message + '</div></div>' if wipe_log.error_message else ''}
        
        {ReportGenerator._generate_smart_html_section(wipe_log.smart_data_before) if wipe_log.smart_data_before else ''}
        
        <div class="footer">
            <p>Dieser Report wurde automatisch vom Disk Wiper Tool generiert.</p>
            <p>Report ID: {wipe_log.id}</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html

    @staticmethod
    def _generate_smart_html_section(smart_data_str):
        """Generiert HTML-Abschnitt für SMART-Daten"""
        if not smart_data_str:
            return ''
        
        try:
            smart_data = json.loads(smart_data_str)
            smart_summary = json.dumps(smart_data, indent=2)
        except:
            smart_summary = smart_data_str
        
        return f"""
        <div class="section">
            <div class="section-title">SMART-Daten vor Wipe</div>
            <div class="smart-data">
                <pre>{smart_summary}</pre>
            </div>
        </div>
        """

    @staticmethod
    def _format_size(size_bytes):
        """Formatiert Byte-Größe"""
        if not size_bytes:
            return 'N/A'
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    @staticmethod
    def _format_duration(seconds):
        """Formatiert Zeitdauer"""
        if not seconds:
            return 'N/A'
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")
        
        return " ".join(parts)


from datetime import datetime, timezone
import json
from xhtml2pdf import pisa
import io


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
        
        if wipe_log.smart_data_after:
            try:
                smart_data = json.loads(wipe_log.smart_data_after)
                report['smart_data_after_wipe'] = smart_data
            except:
                report['smart_data_after_wipe'] = wipe_log.smart_data_after
        
        # Fehler hinzufügen falls vorhanden
        if wipe_log.error_message:
            report['error'] = wipe_log.error_message
        
        return report

    @staticmethod
    def generate_pdf_report(wipe_log):
        """Erstellt einen PDF-Report für einen Wipe-Vorgang"""
        # Generiere HTML mit PDF-spezifischen Styles (Seitenumbruch)
        html_content = ReportGenerator.generate_html_report(wipe_log, for_pdf=True)
        
        # Konvertiere HTML zu PDF mit xhtml2pdf
        pdf_file = io.BytesIO()
        pisa_status = pisa.CreatePDF(
            src=io.BytesIO(html_content.encode('utf-8')),
            dest=pdf_file,
            encoding='utf-8'
        )
        
        if pisa_status.err:
            raise Exception(f"Fehler bei der PDF-Generierung: {pisa_status.err}")
        
        pdf_file.seek(0)
        return pdf_file

    @staticmethod
    def generate_html_report(wipe_log, for_pdf=False):
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
        .header p {{
            color: #4b5563;
            font-size: 15px;
            margin: 8px 0;
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
        .datetime-value {{
            color: #1f2937;
            font-family: 'Courier New', monospace;
            font-weight: 500;
            background: #f3f4f6;
            padding: 2px 8px;
            border-radius: 4px;
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
        .smart-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            background: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .smart-table th {{
            background: #2563eb;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
        }}
        .smart-table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e5e7eb;
        }}
        .smart-table tr:hover {{
            background: #f9fafb;
        }}
        .smart-table .attr-name {{
            font-weight: 600;
            color: #374151;
        }}
        .smart-value-changed {{
            background: #fef3c7;
            font-weight: bold;
        }}
        .smart-value-improved {{
            color: #059669;
        }}
        .smart-value-degraded {{
            color: #dc2626;
        }}
        details {{
            margin-top: 15px;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            padding: 10px;
            background: #f9fafb;
        }}
        summary {{
            cursor: pointer;
            font-weight: bold;
            color: #2563eb;
            padding: 8px;
            user-select: none;
        }}
        summary:hover {{
            background: #eff6ff;
            border-radius: 4px;
        }}
        details[open] summary {{
            margin-bottom: 15px;
            border-bottom: 2px solid #e5e7eb;
        }}
        .raw-data {{
            background: #1f2937;
            color: #f3f4f6;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.5;
        }}
        {f'''
        /* PDF-spezifische Styles */
        .smart-section {{
            page-break-before: always;
            break-before: page;
        }}
        @media print {{
            .smart-section {{
                page-break-before: always;
            }}
        }}
        ''' if for_pdf else ''}
    </style>
</head>
<body>
    <div class="report-container">
        <div class="header">
            <h1>🗑️ Disk Wipe Report</h1>
            <p><strong>Generiert am:</strong> {ReportGenerator._format_datetime(datetime.now())}</p>
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
                <div class="datetime-value">{ReportGenerator._format_datetime(wipe_log.start_time)}</div>
                
                <div class="info-label">Endzeit:</div>
                <div class="datetime-value">{ReportGenerator._format_datetime(wipe_log.end_time)}</div>
                
                <div class="info-label">Dauer:</div>
                <div class="info-value">{report_data['timing']['duration_human']}</div>
                
                <div class="info-label">Verifiziert:</div>
                <div class="info-value {'success' if wipe_log.verified else ''}">
                    {'✓ Ja' if wipe_log.verified else '✗ Nein'}
                </div>
            </div>
        </div>
        
        {'<div class="section"><div class="section-title">Fehler</div><div class="error">' + wipe_log.error_message + '</div></div>' if wipe_log.error_message else ''}
        
        {ReportGenerator._generate_smart_comparison_section(wipe_log.smart_data_before, wipe_log.smart_data_after) if (wipe_log.smart_data_before or wipe_log.smart_data_after) else ''}
        
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
    def _generate_smart_comparison_section(smart_data_before_str, smart_data_after_str):
        """Generiert HTML-Abschnitt mit SMART-Daten-Vergleich"""
        if not smart_data_before_str and not smart_data_after_str:
            return ''
        
        # Parse SMART-Daten
        smart_before = None
        smart_after = None
        
        try:
            if smart_data_before_str:
                smart_before = json.loads(smart_data_before_str)
        except:
            smart_before = {'raw': smart_data_before_str}
        
        try:
            if smart_data_after_str:
                smart_after = json.loads(smart_data_after_str)
        except:
            smart_after = {'raw': smart_data_after_str}
        
        # Generiere Tabellen-HTML
        table_html = ReportGenerator._generate_smart_table(smart_before, smart_after)
        
        # Generiere Rohdaten-HTML (ausklappbar)
        raw_data_html = ReportGenerator._generate_raw_smart_data(smart_before, smart_after)
        
        return f"""
        <div class="section smart-section">
            <div class="section-title">📊 SMART-Daten Vergleich</div>
            {table_html}
            {raw_data_html}
        </div>
        """
    
    @staticmethod
    def _generate_smart_table(smart_before, smart_after):
        """Generiert eine Vergleichstabelle für SMART-Werte"""
        if not smart_before and not smart_after:
            return '<p>Keine SMART-Daten verfügbar.</p>'
        
        # Wichtige SMART-Attribute zum Anzeigen
        attributes_to_show = [
            ('model', 'Modell'),
            ('serial', 'Seriennummer'),
            ('smart_status', 'SMART Status'),
            ('health_status', 'Gesundheitsstatus'),
            ('power_on_hours', 'Betriebsstunden'),
            ('power_cycle_count', 'Power Cycle Count'),
            ('temperature', 'Temperatur (°C)'),
            ('wear', 'Abnutzung'),
            ('read_errors', 'Lesefehler'),
            ('write_errors', 'Schreibfehler'),
        ]
        
        rows = []
        for key, label in attributes_to_show:
            value_before = smart_before.get(key) if smart_before else None
            value_after = smart_after.get(key) if smart_after else None
            
            # Überspringe Zeilen wo beide Werte None/leer sind
            if value_before is None and value_after is None:
                continue
            
            # Formatiere Werte
            value_before_str = ReportGenerator._format_smart_value(value_before)
            value_after_str = ReportGenerator._format_smart_value(value_after)
            
            # Prüfe ob Wert sich geändert hat
            changed = value_before != value_after and value_before is not None and value_after is not None
            changed_class = 'smart-value-changed' if changed else ''
            
            rows.append(f"""
                <tr>
                    <td class="attr-name">{label}</td>
                    <td>{value_before_str}</td>
                    <td class="{changed_class}">{value_after_str}</td>
                </tr>
            """)
        
        # Wenn wir SMART-Attribute haben (z.B. von Linux), zeige diese auch
        if smart_before and 'attributes' in smart_before:
            for attr_name, attr_data in smart_before.get('attributes', {}).items():
                value_before = attr_data.get('raw', attr_data.get('value', 'N/A'))
                
                value_after = 'N/A'
                if smart_after and 'attributes' in smart_after:
                    attr_after = smart_after.get('attributes', {}).get(attr_name, {})
                    value_after = attr_after.get('raw', attr_after.get('value', 'N/A'))
                
                changed = value_before != value_after and value_before != 'N/A' and value_after != 'N/A'
                changed_class = 'smart-value-changed' if changed else ''
                
                rows.append(f"""
                    <tr>
                        <td class="attr-name">{attr_name}</td>
                        <td>{value_before}</td>
                        <td class="{changed_class}">{value_after}</td>
                    </tr>
                """)
        
        if not rows:
            return '<p>Keine vergleichbaren SMART-Daten verfügbar.</p>'
        
        return f"""
        <table class="smart-table">
            <thead>
                <tr>
                    <th>Attribut</th>
                    <th>Vor Wipe</th>
                    <th>Nach Wipe</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    @staticmethod
    def _generate_raw_smart_data(smart_before, smart_after):
        """Generiert ausklappbaren Bereich für Roh-SMART-Daten"""
        sections = []
        
        if smart_before:
            raw_before = json.dumps(smart_before, indent=2, ensure_ascii=False)
            sections.append(f"""
            <details>
                <summary>🔍 Rohdaten vor Wipe anzeigen</summary>
                <div class="raw-data">
                    <pre>{raw_before}</pre>
                </div>
            </details>
            """)
        
        if smart_after:
            raw_after = json.dumps(smart_after, indent=2, ensure_ascii=False)
            sections.append(f"""
            <details>
                <summary>🔍 Rohdaten nach Wipe anzeigen</summary>
                <div class="raw-data">
                    <pre>{raw_after}</pre>
                </div>
            </details>
            """)
        
        return ''.join(sections)
    
    @staticmethod
    def _format_smart_value(value):
        """Formatiert einen SMART-Wert für die Anzeige"""
        if value is None or value == '':
            return 'N/A'
        if isinstance(value, bool):
            return '✓ Ja' if value else '✗ Nein'
        return str(value)

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
    
    @staticmethod
    def _format_datetime(dt):
        """Formatiert Datum und Uhrzeit im deutschen Format"""
        if not dt:
            return 'N/A'
        
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except:
                return dt
        
        # Wenn das datetime-Objekt naive ist (keine Timezone), behandle es als UTC
        if dt.tzinfo is None:
            # Nehme an, es ist UTC und konvertiere zur lokalen Zeit
            dt = dt.replace(tzinfo=timezone.utc).astimezone()
        
        # Formatiere im deutschen Format: TT.MM.JJJJ, HH:MM:SS Uhr
        return dt.strftime('%d.%m.%Y um %H:%M:%S Uhr')


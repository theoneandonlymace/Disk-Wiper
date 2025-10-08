from flask import Blueprint, render_template, jsonify, request, send_file
from app import db
from app.models import Disk, WipeLog
from app.utils import DiskManager, SmartReader, WipeEngine, ReportGenerator
from datetime import datetime
import json
import io

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """Hauptseite mit Festplattenübersicht"""
    return render_template('index.html')


@bp.route('/api/disks/scan')
def scan_disks():
    """Scannt alle verfügbaren Festplatten und aktualisiert die Datenbank"""
    try:
        disks = DiskManager.get_all_disks()
        
        updated_disks = []
        for disk_info in disks:
            # Suche nach existierender Disk in DB
            disk = Disk.query.filter_by(serial_number=disk_info['serial_number']).first()
            
            if disk:
                # Update existierende Disk
                disk.device_path = disk_info['device_path']
                disk.model = disk_info['model']
                disk.size_bytes = disk_info['size_bytes']
                disk.size_human = disk_info['size_human']
                disk.is_boot_disk = disk_info['is_boot_disk']
                disk.last_seen = datetime.utcnow()
            else:
                # Erstelle neue Disk
                disk = Disk(
                    device_path=disk_info['device_path'],
                    model=disk_info['model'],
                    serial_number=disk_info['serial_number'],
                    size_bytes=disk_info['size_bytes'],
                    size_human=disk_info['size_human'],
                    is_boot_disk=disk_info['is_boot_disk']
                )
                db.session.add(disk)
            
            updated_disks.append(disk)
        
        db.session.commit()
        
        # Render Partial Template für HTMX
        return render_template('partials/disk_list.html', disks=updated_disks)
        
    except Exception as e:
        return f'<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">Fehler: {str(e)}</div>', 500


@bp.route('/api/disks')
def get_disks():
    """Gibt alle Festplatten aus der Datenbank zurück"""
    try:
        disks = Disk.query.all()
        disks_data = [disk.to_dict() for disk in disks]
        
        return jsonify({
            'success': True,
            'disks': disks_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/disks/<int:disk_id>')
def get_disk(disk_id):
    """Gibt Details einer spezifischen Festplatte zurück"""
    try:
        disk = Disk.query.get_or_404(disk_id)
        
        return jsonify({
            'success': True,
            'disk': disk.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404


@bp.route('/api/disks/<int:disk_id>/smart')
def get_disk_smart(disk_id):
    """Liest SMART-Daten einer Festplatte aus und speichert sie"""
    try:
        disk = Disk.query.get_or_404(disk_id)
        
        # SMART-Daten auslesen
        smart_data = SmartReader.get_smart_data(disk.device_path)
        
        # In Datenbank speichern
        disk.smart_data = json.dumps(smart_data)
        disk.smart_status = smart_data.get('smart_status', 'UNKNOWN')
        db.session.commit()
        
        return jsonify({
            'success': True,
            'smart_data': smart_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/disks/<int:disk_id>/wipe', methods=['POST'])
def wipe_disk(disk_id):
    """Startet einen Wipe-Vorgang für eine Festplatte"""
    try:
        disk = Disk.query.get_or_404(disk_id)
        
        # Parameter aus Request
        data = request.get_json() or {}
        wipe_method = data.get('method', 'zeros')
        passes = int(data.get('passes', 1))
        
        # Validierung
        if wipe_method not in ['zeros', 'random', 'dod']:
            return jsonify({
                'success': False,
                'error': 'Ungültige Wipe-Methode'
            }), 400
        
        if passes < 1 or passes > 10:
            return jsonify({
                'success': False,
                'error': 'Anzahl Pässe muss zwischen 1 und 10 liegen'
            }), 400
        
        # SMART-Daten vor Wipe auslesen und speichern
        smart_data = SmartReader.get_smart_data(disk.device_path)
        disk.smart_data = json.dumps(smart_data)
        disk.smart_status = smart_data.get('smart_status', 'UNKNOWN')
        db.session.commit()
        
        # Wipe starten
        success, message, wipe_log_id = WipeEngine.start_wipe(
            disk_id,
            disk.device_path,
            wipe_method,
            passes
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'wipe_log_id': wipe_log_id
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/wipes')
def get_wipes():
    """Gibt alle Wipe-Vorgänge zurück (als HTML für HTMX)"""
    try:
        wipes = WipeLog.query.order_by(WipeLog.start_time.desc()).all()
        
        # Wenn HTMX-Request, gebe Partial zurück
        if request.headers.get('HX-Request'):
            return render_template('partials/wipe_list.html', wipes=wipes)
        
        # Sonst JSON
        wipes_data = [wipe.to_dict() for wipe in wipes]
        return jsonify({
            'success': True,
            'wipes': wipes_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/wipes/<int:wipe_id>')
def get_wipe(wipe_id):
    """Gibt Details eines Wipe-Vorgangs zurück"""
    try:
        wipe = WipeLog.query.get_or_404(wipe_id)
        
        return jsonify({
            'success': True,
            'wipe': wipe.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404


@bp.route('/api/wipes/<int:wipe_id>/status')
def get_wipe_status(wipe_id):
    """Gibt den aktuellen Status eines Wipe-Vorgangs zurück"""
    try:
        status = WipeEngine.get_wipe_status(wipe_id)
        
        if status:
            return jsonify({
                'success': True,
                'status': status
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Wipe-Vorgang nicht gefunden'
            }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/wipes/<int:wipe_id>/report')
def get_wipe_report(wipe_id):
    """Generiert und gibt einen Report für einen Wipe-Vorgang zurück"""
    try:
        wipe = WipeLog.query.get_or_404(wipe_id)
        
        # Format bestimmen
        report_format = request.args.get('format', 'json')
        
        if report_format == 'html':
            html = ReportGenerator.generate_html_report(wipe)
            return html
        else:
            report = ReportGenerator.generate_wipe_report(wipe)
            return jsonify({
                'success': True,
                'report': report
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/search')
def search_disks():
    """Sucht nach Festplatten anhand von Seriennummer oder Modell"""
    try:
        query = request.args.get('q', '')
        
        if not query:
            return render_template('partials/search_results.html', disks=[], wipe_logs=[], query='')
        
        # Suche in Disk-Tabelle
        disks = Disk.query.filter(
            (Disk.serial_number.ilike(f'%{query}%')) |
            (Disk.model.ilike(f'%{query}%'))
        ).all()
        
        # Suche in WipeLog-Tabelle
        wipe_logs = WipeLog.query.filter(
            (WipeLog.serial_number.ilike(f'%{query}%')) |
            (WipeLog.model.ilike(f'%{query}%'))
        ).all()
        
        # Wenn HTMX-Request, gebe Partial zurück
        if request.headers.get('HX-Request'):
            return render_template('partials/search_results.html', disks=disks, wipe_logs=wipe_logs, query=query)
        
        return jsonify({
            'success': True,
            'disks': [disk.to_dict() for disk in disks],
            'wipe_logs': [wipe.to_dict() for wipe in wipe_logs]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/wipes')
def wipes_page():
    """Seite mit Wipe-Historie"""
    return render_template('wipes.html')


@bp.route('/search')
def search_page():
    """Suchseite"""
    return render_template('search.html')

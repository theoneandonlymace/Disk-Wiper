#!/usr/bin/env python3
from app import create_app, db
from app.models import Disk, WipeLog
from waitress import serve

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Disk': Disk, 'WipeLog': WipeLog}


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    print("Starte Disk-Wiper mit Waitress WSGI-Server...")
    print("Server läuft auf http://0.0.0.0:5000")
    print("Drücken Sie Ctrl+C zum Beenden")
    
    # Waitress ist ein production-ready WSGI-Server
    # threads=4: Anzahl der Worker-Threads für gleichzeitige Anfragen
    # channel_timeout=300: Timeout für Long-Running-Requests (z.B. Disk-Wipes)
    serve(app, host='0.0.0.0', port=5000, threads=4, channel_timeout=300)


import os
from pathlib import Path
import tempfile

basedir = os.path.abspath(os.path.dirname(__file__))

# Verwende das User-Temp-Verzeichnis für die Datenbank (hat garantiert Schreibrechte)
db_dir = os.path.join(os.path.expanduser('~'), '.disk_wiper')
os.makedirs(db_dir, exist_ok=True)


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    # Datenbank im User-Verzeichnis speichern (schreibbar)
    db_path = os.path.join(db_dir, 'disk_wiper.db').replace('\\', '/')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{db_path}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    MAX_WIPE_THREADS = 4  # Mehrere Disks gleichzeitig löschen


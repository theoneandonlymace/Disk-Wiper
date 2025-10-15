from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from config import Config
from datetime import datetime, timezone

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Jinja2-Filter für Zeitkonvertierung UTC -> Lokal
    @app.template_filter('localtime')
    def localtime_filter(dt):
        """Konvertiert UTC-Zeit in lokale Serverzeit"""
        if not dt:
            return None
        # Wenn naive datetime (ohne Timezone), behandle als UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # Konvertiere zu lokaler Zeit
        return dt.astimezone()
    
    from app.routes import main
    app.register_blueprint(main.bp)

    return app


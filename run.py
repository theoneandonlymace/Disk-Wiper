#!/usr/bin/env python3
from app import create_app, db
from app.models import Disk, WipeLog

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Disk': Disk, 'WipeLog': WipeLog}


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)


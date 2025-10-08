from datetime import datetime
from app import db


class Disk(db.Model):
    __tablename__ = 'disks'

    id = db.Column(db.Integer, primary_key=True)
    device_path = db.Column(db.String(255), nullable=False)
    model = db.Column(db.String(255))
    serial_number = db.Column(db.String(255), unique=True, nullable=False, index=True)
    size_bytes = db.Column(db.BigInteger)
    size_human = db.Column(db.String(50))
    is_boot_disk = db.Column(db.Boolean, default=False)
    
    # SMART Data (stored as JSON string or individual fields)
    smart_status = db.Column(db.String(50))
    smart_data = db.Column(db.Text)  # JSON string
    
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    wipe_logs = db.relationship('WipeLog', backref='disk', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Disk {self.serial_number} - {self.model}>'

    def to_dict(self):
        return {
            'id': self.id,
            'device_path': self.device_path,
            'model': self.model,
            'serial_number': self.serial_number,
            'size_bytes': self.size_bytes,
            'size_human': self.size_human,
            'is_boot_disk': self.is_boot_disk,
            'smart_status': self.smart_status,
            'smart_data': self.smart_data,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'wipe_count': self.wipe_logs.count()
        }


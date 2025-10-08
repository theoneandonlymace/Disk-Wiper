from datetime import datetime
from app import db


class WipeLog(db.Model):
    __tablename__ = 'wipe_logs'

    id = db.Column(db.Integer, primary_key=True)
    disk_id = db.Column(db.Integer, db.ForeignKey('disks.id'), nullable=False)
    
    # Disk Info at time of wipe
    device_path = db.Column(db.String(255), nullable=False)
    model = db.Column(db.String(255))
    serial_number = db.Column(db.String(255), nullable=False, index=True)
    size_bytes = db.Column(db.BigInteger)
    
    # SMART Data before wipe
    smart_data_before = db.Column(db.Text)  # JSON string
    
    # Wipe Details
    wipe_method = db.Column(db.String(100))  # e.g., "DoD 5220.22-M", "zeros", "random"
    wipe_passes = db.Column(db.Integer, default=1)
    
    # Status and Timing
    status = db.Column(db.String(50), default='pending')  # pending, in_progress, completed, failed
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)
    
    # Progress and Errors
    progress_percent = db.Column(db.Float, default=0.0)
    error_message = db.Column(db.Text)
    
    # Verification
    verified = db.Column(db.Boolean, default=False)
    verification_data = db.Column(db.Text)  # JSON string with verification results

    def __repr__(self):
        return f'<WipeLog {self.serial_number} - {self.status}>'

    def to_dict(self):
        return {
            'id': self.id,
            'disk_id': self.disk_id,
            'device_path': self.device_path,
            'model': self.model,
            'serial_number': self.serial_number,
            'size_bytes': self.size_bytes,
            'smart_data_before': self.smart_data_before,
            'wipe_method': self.wipe_method,
            'wipe_passes': self.wipe_passes,
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'progress_percent': self.progress_percent,
            'error_message': self.error_message,
            'verified': self.verified,
            'verification_data': self.verification_data
        }


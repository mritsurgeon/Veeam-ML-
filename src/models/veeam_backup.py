from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class VeeamBackup(db.Model):
    """Model representing a Veeam backup job or backup file."""
    __tablename__ = 'veeam_backups'
    
    id = db.Column(db.Integer, primary_key=True)
    backup_id = db.Column(db.String(255), unique=True, nullable=False)
    backup_name = db.Column(db.String(255), nullable=False)
    backup_path = db.Column(db.String(500), nullable=False)
    mount_point = db.Column(db.String(500), nullable=True)
    backup_date = db.Column(db.DateTime, nullable=False)
    backup_size = db.Column(db.BigInteger, nullable=True)
    status = db.Column(db.String(50), default='available')  # available, mounted, processing, error
    os_type = db.Column(db.String(50), default='unknown')  # windows, linux, unknown
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ml_jobs = db.relationship('MLJob', backref='backup', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'backup_id': self.backup_id,
            'backup_name': self.backup_name,
            'backup_path': self.backup_path,
            'mount_point': self.mount_point,
            'backup_date': self.backup_date.isoformat() if self.backup_date else None,
            'backup_size': self.backup_size,
            'status': self.status,
            'os_type': self.os_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class MLJob(db.Model):
    """Model representing a machine learning job performed on backup data."""
    __tablename__ = 'ml_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    job_name = db.Column(db.String(255), nullable=False)
    ml_algorithm = db.Column(db.String(100), nullable=False)  # classification, regression, clustering, etc.
    backup_id = db.Column(db.Integer, db.ForeignKey('veeam_backups.id'), nullable=False)
    data_source_path = db.Column(db.String(500), nullable=True)  # Path within the mounted backup
    parameters = db.Column(db.Text, nullable=True)  # JSON string of ML parameters
    status = db.Column(db.String(50), default='pending')  # pending, running, completed, failed
    progress = db.Column(db.Float, default=0.0)  # Progress percentage (0-100)
    results = db.Column(db.Text, nullable=True)  # JSON string of results
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'job_name': self.job_name,
            'ml_algorithm': self.ml_algorithm,
            'backup_id': self.backup_id,
            'data_source_path': self.data_source_path,
            'parameters': self.parameters,
            'status': self.status,
            'progress': self.progress,
            'results': self.results,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class DataExtraction(db.Model):
    """Model representing extracted data from backups."""
    __tablename__ = 'data_extractions'
    
    id = db.Column(db.Integer, primary_key=True)
    ml_job_id = db.Column(db.Integer, db.ForeignKey('ml_jobs.id'), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)  # Path to the source file within backup
    file_type = db.Column(db.String(100), nullable=False)  # log, database, config, document, etc.
    extraction_method = db.Column(db.String(100), nullable=False)  # direct_read, log_parse, db_query, etc.
    extracted_records = db.Column(db.Integer, default=0)
    extraction_status = db.Column(db.String(50), default='pending')  # pending, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    ml_job = db.relationship('MLJob', backref='data_extractions', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'ml_job_id': self.ml_job_id,
            'file_path': self.file_path,
            'file_type': self.file_type,
            'extraction_method': self.extraction_method,
            'extracted_records': self.extracted_records,
            'extraction_status': self.extraction_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


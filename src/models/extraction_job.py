"""
Configurable Extraction Job Models

This module defines the database models for configurable extraction jobs,
allowing users to create and manage different types of data extraction tasks.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from enum import Enum
import json
from typing import Dict, Any, List

# Import the existing db instance from veeam_backup
from src.models.veeam_backup import db

class ExtractionLevel(Enum):
    """Extraction levels available for jobs."""
    METADATA_ONLY = "metadata_only"
    CONTENT_PARSING = "content_parsing" 
    DATABASE_EXTRACTION = "database_extraction"
    FULL_PIPELINE = "full_pipeline"

class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class FileTypeFilter(Enum):
    """File type filters for extraction jobs."""
    ALL_FILES = "all_files"
    DOCUMENTS_ONLY = "documents_only"
    DATABASES_ONLY = "databases_only"
    LOGS_ONLY = "logs_only"
    CONFIG_ONLY = "config_only"
    CUSTOM = "custom"

class ExtractionJob(db.Model):
    """
    Configurable extraction job that defines what data to extract and how.
    """
    __tablename__ = 'extraction_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # Job Configuration
    extraction_level = db.Column(db.Enum(ExtractionLevel), nullable=False)
    file_type_filter = db.Column(db.Enum(FileTypeFilter), nullable=False, default=FileTypeFilter.ALL_FILES)
    custom_file_types = db.Column(db.Text)  # JSON array of custom file extensions
    
    # Scope Configuration
    backup_id = db.Column(db.String(255), nullable=False)
    directory_path = db.Column(db.String(500), default='/')
    max_depth = db.Column(db.Integer, default=3)
    max_file_size = db.Column(db.BigInteger, default=50 * 1024 * 1024)  # 50MB default
    
    # Processing Configuration
    chunk_size = db.Column(db.Integer, default=2000)
    include_attributes = db.Column(db.Boolean, default=False)
    parallel_processing = db.Column(db.Boolean, default=True)
    max_workers = db.Column(db.Integer, default=4)
    
    # Content Parsing Options
    enable_document_parsing = db.Column(db.Boolean, default=True)
    enable_spreadsheet_parsing = db.Column(db.Boolean, default=True)
    enable_presentation_parsing = db.Column(db.Boolean, default=True)
    enable_log_parsing = db.Column(db.Boolean, default=True)
    enable_config_parsing = db.Column(db.Boolean, default=True)
    
    # Database Extraction Options
    enable_sqlite_extraction = db.Column(db.Boolean, default=True)
    enable_sql_dump_parsing = db.Column(db.Boolean, default=True)
    enable_enterprise_db_extraction = db.Column(db.Boolean, default=False)
    max_db_rows_per_table = db.Column(db.Integer, default=1000)
    
    # Output Configuration
    output_format = db.Column(db.String(50), default='json')  # json, csv, parquet
    include_raw_content = db.Column(db.Boolean, default=True)
    include_chunks = db.Column(db.Boolean, default=True)
    include_embeddings = db.Column(db.Boolean, default=False)
    
    # Job Status and Timing
    status = db.Column(db.Enum(JobStatus), default=JobStatus.PENDING)
    created_by = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Progress Tracking
    total_files = db.Column(db.Integer, default=0)
    processed_files = db.Column(db.Integer, default=0)
    failed_files = db.Column(db.Integer, default=0)
    progress_percentage = db.Column(db.Float, default=0.0)
    
    # Results
    results_summary = db.Column(db.Text)  # JSON summary of results
    error_message = db.Column(db.Text)
    
    # Relationships
    executions = db.relationship('ExtractionJobExecution', backref='job', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'extraction_level': self.extraction_level.value if self.extraction_level else None,
            'file_type_filter': self.file_type_filter.value if self.file_type_filter else None,
            'custom_file_types': json.loads(self.custom_file_types) if self.custom_file_types else [],
            'backup_id': self.backup_id,
            'directory_path': self.directory_path,
            'max_depth': self.max_depth,
            'max_file_size': self.max_file_size,
            'chunk_size': self.chunk_size,
            'include_attributes': self.include_attributes,
            'parallel_processing': self.parallel_processing,
            'max_workers': self.max_workers,
            'enable_document_parsing': self.enable_document_parsing,
            'enable_spreadsheet_parsing': self.enable_spreadsheet_parsing,
            'enable_presentation_parsing': self.enable_presentation_parsing,
            'enable_log_parsing': self.enable_log_parsing,
            'enable_config_parsing': self.enable_config_parsing,
            'enable_sqlite_extraction': self.enable_sqlite_extraction,
            'enable_sql_dump_parsing': self.enable_sql_dump_parsing,
            'enable_enterprise_db_extraction': self.enable_enterprise_db_extraction,
            'max_db_rows_per_table': self.max_db_rows_per_table,
            'output_format': self.output_format,
            'include_raw_content': self.include_raw_content,
            'include_chunks': self.include_chunks,
            'include_embeddings': self.include_embeddings,
            'status': self.status.value if self.status else None,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_files': self.total_files,
            'processed_files': self.processed_files,
            'failed_files': self.failed_files,
            'progress_percentage': self.progress_percentage,
            'results_summary': json.loads(self.results_summary) if self.results_summary else None,
            'error_message': self.error_message
        }
    
    def update_progress(self, processed: int, failed: int = 0):
        """Update job progress."""
        self.processed_files = processed
        self.failed_files = failed
        if self.total_files > 0:
            self.progress_percentage = (processed / self.total_files) * 100
        db.session.commit()
    
    def set_status(self, status: JobStatus, error_message: str = None):
        """Update job status."""
        self.status = status
        if status == JobStatus.RUNNING and not self.started_at:
            self.started_at = datetime.utcnow()
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            self.completed_at = datetime.utcnow()
        
        if error_message:
            self.error_message = error_message
        
        db.session.commit()

class ExtractionJobExecution(db.Model):
    """
    Individual execution of an extraction job.
    """
    __tablename__ = 'extraction_job_executions'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('extraction_jobs.id'), nullable=False)
    
    # Execution Details
    execution_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum(JobStatus), default=JobStatus.PENDING)
    
    # Input Parameters
    session_id = db.Column(db.String(255))
    mount_type = db.Column(db.String(50))
    unc_path = db.Column(db.String(500))
    
    # Results
    files_processed = db.Column(db.Integer, default=0)
    chunks_created = db.Column(db.Integer, default=0)
    databases_extracted = db.Column(db.Integer, default=0)
    errors_count = db.Column(db.Integer, default=0)
    
    # Output
    output_path = db.Column(db.String(500))
    results_data = db.Column(db.Text)  # JSON results
    error_log = db.Column(db.Text)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert execution to dictionary."""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'execution_timestamp': self.execution_timestamp.isoformat() if self.execution_timestamp else None,
            'status': self.status.value if self.status else None,
            'session_id': self.session_id,
            'mount_type': self.mount_type,
            'unc_path': self.unc_path,
            'files_processed': self.files_processed,
            'chunks_created': self.chunks_created,
            'databases_extracted': self.databases_extracted,
            'errors_count': self.errors_count,
            'output_path': self.output_path,
            'results_data': json.loads(self.results_data) if self.results_data else None,
            'error_log': self.error_log
        }

class ExtractionJobTemplate(db.Model):
    """
    Predefined templates for common extraction scenarios.
    """
    __tablename__ = 'extraction_job_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))  # e.g., 'compliance', 'forensics', 'analytics'
    
    # Template Configuration (JSON)
    configuration = db.Column(db.Text, nullable=False)
    
    # Template Metadata
    created_by = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=True)
    usage_count = db.Column(db.Integer, default=0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'configuration': json.loads(self.configuration),
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_public': self.is_public,
            'usage_count': self.usage_count
        }
    
    def create_job_from_template(self, name: str, backup_id: str, created_by: str = None) -> ExtractionJob:
        """Create a new job from this template."""
        config = json.loads(self.configuration)
        
        # Convert string enum values to actual enum instances
        if 'extraction_level' in config:
            config['extraction_level'] = ExtractionLevel(config['extraction_level'])
        if 'file_type_filter' in config:
            config['file_type_filter'] = FileTypeFilter(config['file_type_filter'])
        
        job = ExtractionJob(
            name=name,
            description=f"Created from template: {self.name}",
            backup_id=backup_id,
            created_by=created_by,
            **config
        )
        
        # Increment usage count
        self.usage_count += 1
        
        db.session.add(job)
        db.session.commit()
        
        return job

# Predefined templates
DEFAULT_TEMPLATES = [
    {
        'name': 'File System Census',
        'description': 'Extract metadata only for file system analysis',
        'category': 'analytics',
        'configuration': {
            'extraction_level': ExtractionLevel.METADATA_ONLY.value,
            'file_type_filter': FileTypeFilter.ALL_FILES.value,
            'max_depth': 5,
            'include_attributes': True,
            'output_format': 'json'
        }
    },
    {
        'name': 'Document Analysis',
        'description': 'Extract and parse document content for NLP analysis',
        'category': 'analytics',
        'configuration': {
            'extraction_level': ExtractionLevel.CONTENT_PARSING.value,
            'file_type_filter': FileTypeFilter.DOCUMENTS_ONLY.value,
            'max_depth': 3,
            'chunk_size': 2000,
            'enable_document_parsing': True,
            'enable_spreadsheet_parsing': True,
            'enable_presentation_parsing': True,
            'include_chunks': True,
            'include_embeddings': True,
            'output_format': 'json'
        }
    },
    {
        'name': 'Database Forensics',
        'description': 'Extract database content for forensic analysis',
        'category': 'forensics',
        'configuration': {
            'extraction_level': ExtractionLevel.DATABASE_EXTRACTION.value,
            'file_type_filter': FileTypeFilter.DATABASES_ONLY.value,
            'max_depth': 2,
            'enable_sqlite_extraction': True,
            'enable_sql_dump_parsing': True,
            'enable_enterprise_db_extraction': True,
            'max_db_rows_per_table': 5000,
            'output_format': 'json'
        }
    },
    {
        'name': 'Compliance Audit',
        'description': 'Full pipeline extraction for compliance auditing',
        'category': 'compliance',
        'configuration': {
            'extraction_level': ExtractionLevel.FULL_PIPELINE.value,
            'file_type_filter': FileTypeFilter.ALL_FILES.value,
            'max_depth': 4,
            'max_file_size': 100 * 1024 * 1024,  # 100MB
            'chunk_size': 1500,
            'include_attributes': True,
            'enable_document_parsing': True,
            'enable_log_parsing': True,
            'enable_config_parsing': True,
            'include_raw_content': True,
            'include_chunks': True,
            'output_format': 'json'
        }
    },
    {
        'name': 'Log Analysis',
        'description': 'Extract and parse log files for security analysis',
        'category': 'security',
        'configuration': {
            'extraction_level': ExtractionLevel.CONTENT_PARSING.value,
            'file_type_filter': FileTypeFilter.LOGS_ONLY.value,
            'max_depth': 3,
            'chunk_size': 1000,
            'enable_log_parsing': True,
            'include_raw_content': True,
            'include_chunks': True,
            'output_format': 'json'
        }
    }
]

def create_default_templates():
    """Create default job templates."""
    for template_data in DEFAULT_TEMPLATES:
        existing = ExtractionJobTemplate.query.filter_by(name=template_data['name']).first()
        if not existing:
            template = ExtractionJobTemplate(
                name=template_data['name'],
                description=template_data['description'],
                category=template_data['category'],
                configuration=json.dumps(template_data['configuration']),
                created_by='system'
            )
            db.session.add(template)
    
    db.session.commit()

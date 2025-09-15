"""
Tests for database models.
"""
import pytest
from datetime import datetime
from src.models.veeam_backup import VeeamBackup, MLJob, DataExtraction


class TestVeeamBackupModel:
    """Test cases for VeeamBackup model."""
    
    def test_create_backup(self, app):
        """Test creating a VeeamBackup record."""
        with app.app_context():
            backup = VeeamBackup(
                backup_id='test-backup-1',
                name='Test Backup',
                size=1024000,
                created_date=datetime.now(),
                status='Success',
                repository='Test Repository'
            )
            
            assert backup.backup_id == 'test-backup-1'
            assert backup.name == 'Test Backup'
            assert backup.size == 1024000
            assert backup.status == 'Success'
    
    def test_backup_serialization(self, app):
        """Test backup model serialization."""
        with app.app_context():
            backup = VeeamBackup(
                backup_id='test-backup-1',
                name='Test Backup',
                size=1024000,
                created_date=datetime.now(),
                status='Success',
                repository='Test Repository'
            )
            
            serialized = backup.to_dict()
            
            assert isinstance(serialized, dict)
            assert serialized['backup_id'] == 'test-backup-1'
            assert serialized['name'] == 'Test Backup'
            assert serialized['size'] == 1024000


class TestMLJobModel:
    """Test cases for MLJob model."""
    
    def test_create_ml_job(self, app):
        """Test creating an MLJob record."""
        with app.app_context():
            job = MLJob(
                name='Test ML Job',
                algorithm='classification',
                parameters={'n_estimators': 100, 'max_depth': 10},
                backup_id='test-backup-1',
                status='pending'
            )
            
            assert job.name == 'Test ML Job'
            assert job.algorithm == 'classification'
            assert job.parameters['n_estimators'] == 100
            assert job.status == 'pending'
    
    def test_ml_job_serialization(self, app):
        """Test ML job model serialization."""
        with app.app_context():
            job = MLJob(
                name='Test ML Job',
                algorithm='classification',
                parameters={'n_estimators': 100},
                backup_id='test-backup-1',
                status='pending'
            )
            
            serialized = job.to_dict()
            
            assert isinstance(serialized, dict)
            assert serialized['name'] == 'Test ML Job'
            assert serialized['algorithm'] == 'classification'
            assert serialized['parameters']['n_estimators'] == 100
    
    def test_ml_job_status_updates(self, app):
        """Test ML job status updates."""
        with app.app_context():
            job = MLJob(
                name='Test ML Job',
                algorithm='classification',
                parameters={},
                backup_id='test-backup-1',
                status='pending'
            )
            
            # Test status transitions
            job.status = 'running'
            assert job.status == 'running'
            
            job.status = 'completed'
            assert job.status == 'completed'
            
            job.status = 'failed'
            assert job.status == 'failed'


class TestDataExtractionModel:
    """Test cases for DataExtraction model."""
    
    def test_create_data_extraction(self, app):
        """Test creating a DataExtraction record."""
        with app.app_context():
            extraction = DataExtraction(
                backup_id='test-backup-1',
                file_path='/path/to/file.txt',
                file_type='text',
                file_size=1024,
                extraction_status='completed',
                extracted_data={'content': 'sample text'}
            )
            
            assert extraction.backup_id == 'test-backup-1'
            assert extraction.file_path == '/path/to/file.txt'
            assert extraction.file_type == 'text'
            assert extraction.file_size == 1024
            assert extraction.extraction_status == 'completed'
    
    def test_data_extraction_serialization(self, app):
        """Test data extraction model serialization."""
        with app.app_context():
            extraction = DataExtraction(
                backup_id='test-backup-1',
                file_path='/path/to/file.txt',
                file_type='text',
                file_size=1024,
                extraction_status='completed',
                extracted_data={'content': 'sample text'}
            )
            
            serialized = extraction.to_dict()
            
            assert isinstance(serialized, dict)
            assert serialized['backup_id'] == 'test-backup-1'
            assert serialized['file_path'] == '/path/to/file.txt'
            assert serialized['file_type'] == 'text'
            assert serialized['extracted_data']['content'] == 'sample text'

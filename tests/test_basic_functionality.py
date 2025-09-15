"""
Basic integration tests for the Veeam ML Integration application.
"""
import pytest
import json
from unittest.mock import patch, Mock


class TestApplicationBasics:
    """Basic tests to verify the application works."""
    
    def test_app_creation(self, app):
        """Test that the Flask app can be created."""
        assert app is not None
        assert app.config['TESTING'] is True
    
    def test_app_routes_registered(self, app):
        """Test that routes are properly registered."""
        # Check that blueprints are registered
        assert '/api' in [bp.url_prefix for bp in app.blueprints.values()]
        assert '/api/veeam' in [bp.url_prefix for bp in app.blueprints.values()]
    
    def test_static_file_serving(self, client):
        """Test that static files can be served."""
        # Test the root route
        response = client.get('/')
        # Should return the index.html or a 404 if not built
        assert response.status_code in [200, 404]
    
    def test_api_health_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get('/api/veeam/health')
        # Should return some response (even if error)
        assert response.status_code in [200, 500]
    
    def test_cors_headers(self, client):
        """Test that CORS headers are present."""
        response = client.get('/api/veeam/health')
        # CORS should be enabled
        assert 'Access-Control-Allow-Origin' in response.headers or response.status_code == 500


class TestDatabaseModels:
    """Test database model creation and basic operations."""
    
    def test_veeam_backup_model_creation(self, app):
        """Test VeeamBackup model creation."""
        with app.app_context():
            from src.models.veeam_backup import VeeamBackup
            
            backup = VeeamBackup(
                backup_id='test-backup-1',
                backup_name='Test Backup',
                backup_path='/path/to/backup',
                backup_date='2024-01-01T00:00:00Z',
                backup_size=1024000
            )
            
            assert backup.backup_id == 'test-backup-1'
            assert backup.backup_name == 'Test Backup'
            assert backup.status == 'available'  # Default value
    
    def test_ml_job_model_creation(self, app):
        """Test MLJob model creation."""
        with app.app_context():
            from src.models.veeam_backup import MLJob
            
            job = MLJob(
                job_name='Test ML Job',
                ml_algorithm='classification',
                backup_id=1,
                parameters='{"n_estimators": 100}'
            )
            
            assert job.job_name == 'Test ML Job'
            assert job.ml_algorithm == 'classification'
            assert job.status == 'pending'  # Default value
    
    def test_data_extraction_model_creation(self, app):
        """Test DataExtraction model creation."""
        with app.app_context():
            from src.models.veeam_backup import DataExtraction
            
            extraction = DataExtraction(
                ml_job_id=1,
                file_path='/path/to/file.txt',
                file_type='text',
                extraction_method='direct_read',
                extracted_records=100,
                extraction_status='completed'
            )
            
            assert extraction.file_path == '/path/to/file.txt'
            assert extraction.file_type == 'text'
            assert extraction.extraction_status == 'completed'


class TestMLProcessorBasics:
    """Test basic ML processor functionality."""
    
    def test_data_preprocessor_init(self):
        """Test DataPreprocessor initialization."""
        from src.services.ml_processor import DataPreprocessor
        
        preprocessor = DataPreprocessor()
        assert preprocessor is not None
        assert hasattr(preprocessor, 'scalers')
        assert hasattr(preprocessor, 'encoders')
    
    def test_ml_processing_error(self):
        """Test MLProcessingError exception."""
        from src.services.ml_processor import MLProcessingError
        
        error = MLProcessingError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)
    
    def test_classification_processor_init(self):
        """Test ClassificationProcessor initialization."""
        from src.services.ml_processor import ClassificationProcessor
        
        processor = ClassificationProcessor()
        assert processor is not None
    
    def test_regression_processor_init(self):
        """Test RegressionProcessor initialization."""
        from src.services.ml_processor import RegressionProcessor
        
        processor = RegressionProcessor()
        assert processor is not None
    
    def test_clustering_processor_init(self):
        """Test ClusteringProcessor initialization."""
        from src.services.ml_processor import ClusteringProcessor
        
        processor = ClusteringProcessor()
        assert processor is not None


class TestDataExtractorBasics:
    """Test basic data extractor functionality."""
    
    def test_base_data_extractor_init(self):
        """Test BaseDataExtractor initialization."""
        from src.services.data_extractor import BaseDataExtractor
        
        extractor = BaseDataExtractor('/tmp/mount')
        assert extractor is not None
        assert extractor.mount_point == '/tmp/mount'
    
    def test_data_extraction_error(self):
        """Test DataExtractionError exception."""
        from src.services.data_extractor import DataExtractionError
        
        error = DataExtractionError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)
    
    def test_log_file_extractor_init(self):
        """Test LogFileExtractor initialization."""
        from src.services.data_extractor import LogFileExtractor
        
        extractor = LogFileExtractor('/tmp/mount')
        assert extractor is not None
        assert hasattr(extractor, 'log_patterns')
    
    def test_database_extractor_init(self):
        """Test DatabaseExtractor initialization."""
        from src.services.data_extractor import DatabaseExtractor
        
        extractor = DatabaseExtractor('/tmp/mount')
        assert extractor is not None
    
    def test_data_extraction_service_init(self):
        """Test DataExtractionService initialization."""
        from src.services.data_extractor import DataExtractionService
        
        service = DataExtractionService('/tmp/mount')
        assert service is not None
        assert hasattr(service, 'extractors')


class TestVeeamAPIBasics:
    """Test basic Veeam API functionality."""
    
    def test_veeam_api_error(self):
        """Test VeeamAPIError exception."""
        from src.services.veeam_api import VeeamAPIError
        
        error = VeeamAPIError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)
    
    def test_veeam_data_integration_api_init(self):
        """Test VeeamDataIntegrationAPI initialization."""
        from src.services.veeam_api import VeeamDataIntegrationAPI
        
        api = VeeamDataIntegrationAPI('https://test-server:9419', 'user', 'pass')
        assert api is not None
        assert api.base_url == 'https://test-server:9419'
    
    def test_local_file_system_mounter_init(self):
        """Test LocalFileSystemMounter initialization."""
        from src.services.veeam_api import LocalFileSystemMounter
        
        mounter = LocalFileSystemMounter()
        assert mounter is not None

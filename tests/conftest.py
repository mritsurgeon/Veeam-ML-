"""
Pytest configuration and fixtures for the Veeam ML Integration tests.
"""
import os
import sys
import tempfile
import pytest
from flask import Flask
from unittest.mock import Mock, patch

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.main import app as flask_app
from src.models.user import db


@pytest.fixture
def app():
    """Create and configure a test Flask application."""
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp()
    
    # Configure test app
    flask_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': 'test-secret-key'
    })
    
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner for the Flask application."""
    return app.test_cli_runner()


@pytest.fixture
def mock_veeam_api():
    """Mock Veeam API responses for testing."""
    with patch('src.services.veeam_api.VeeamAPI') as mock_api:
        mock_instance = Mock()
        mock_api.return_value = mock_instance
        
        # Mock successful API responses
        mock_instance.test_connection.return_value = True
        mock_instance.list_backups.return_value = [
            {
                'id': 'backup-1',
                'name': 'Test Backup',
                'size': 1024000,
                'created': '2024-01-01T00:00:00Z',
                'status': 'Success'
            }
        ]
        mock_instance.mount_backup.return_value = {'mount_path': '/tmp/mount-123'}
        mock_instance.unmount_backup.return_value = True
        
        yield mock_instance


@pytest.fixture
def sample_backup_data():
    """Sample backup data for testing."""
    return {
        'id': 'backup-1',
        'name': 'Test Backup',
        'size': 1024000,
        'created': '2024-01-01T00:00:00Z',
        'status': 'Success',
        'repository': 'Test Repository'
    }


@pytest.fixture
def sample_ml_job_data():
    """Sample ML job data for testing."""
    return {
        'name': 'Test ML Job',
        'algorithm': 'classification',
        'parameters': {
            'n_estimators': 100,
            'max_depth': 10,
            'random_state': 42
        },
        'backup_id': 'backup-1',
        'status': 'pending'
    }

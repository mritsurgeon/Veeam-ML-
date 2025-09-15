"""
Tests for Veeam API routes and endpoints.
"""
import json
import pytest
from unittest.mock import patch, Mock


class TestVeeamRoutes:
    """Test cases for Veeam API routes."""
    
    def test_configure_veeam_connection_success(self, client, mock_veeam_api):
        """Test successful Veeam connection configuration."""
        config_data = {
            'veeam_url': 'https://test-veeam-server:9419',
            'username': 'testuser',
            'password': 'testpass'
        }
        
        response = client.post('/api/veeam/configure', 
                             data=json.dumps(config_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'message' in data
    
    def test_configure_veeam_connection_invalid_data(self, client):
        """Test Veeam connection configuration with invalid data."""
        config_data = {
            'veeam_url': '',  # Invalid empty URL
            'username': 'testuser',
            'password': 'testpass'
        }
        
        response = client.post('/api/veeam/configure',
                             data=json.dumps(config_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_list_backups_success(self, client, mock_veeam_api):
        """Test successful backup listing."""
        response = client.get('/api/veeam/backups')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'backups' in data
        assert len(data['backups']) > 0
        assert data['backups'][0]['id'] == 'backup-1'
    
    def test_list_backups_api_error(self, client):
        """Test backup listing when API fails."""
        with patch('src.services.veeam_api.VeeamAPI') as mock_api:
            mock_instance = Mock()
            mock_api.return_value = mock_instance
            mock_instance.list_backups.side_effect = Exception("API Error")
            
            response = client.get('/api/veeam/backups')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
    
    def test_mount_backup_success(self, client, mock_veeam_api, sample_backup_data):
        """Test successful backup mounting."""
        response = client.post('/api/veeam/backups/backup-1/mount')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'mount_path' in data
    
    def test_unmount_backup_success(self, client, mock_veeam_api):
        """Test successful backup unmounting."""
        response = client.post('/api/veeam/backups/backup-1/unmount')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_create_ml_job_success(self, client, sample_ml_job_data):
        """Test successful ML job creation."""
        response = client.post('/api/veeam/ml-jobs',
                             data=json.dumps(sample_ml_job_data),
                             content_type='application/json')
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'job_id' in data
    
    def test_create_ml_job_invalid_algorithm(self, client):
        """Test ML job creation with invalid algorithm."""
        job_data = {
            'name': 'Test Job',
            'algorithm': 'invalid_algorithm',
            'parameters': {},
            'backup_id': 'backup-1'
        }
        
        response = client.post('/api/veeam/ml-jobs',
                             data=json.dumps(job_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_list_ml_jobs(self, client):
        """Test listing ML jobs."""
        response = client.get('/api/veeam/ml-jobs')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'jobs' in data
        assert isinstance(data['jobs'], list)
    
    def test_get_ml_job_status(self, client):
        """Test getting ML job status."""
        # First create a job
        job_data = {
            'name': 'Test Job',
            'algorithm': 'classification',
            'parameters': {'n_estimators': 100},
            'backup_id': 'backup-1'
        }
        
        create_response = client.post('/api/veeam/ml-jobs',
                                    data=json.dumps(job_data),
                                    content_type='application/json')
        
        if create_response.status_code == 201:
            job_id = json.loads(create_response.data)['job_id']
            
            # Get job status
            response = client.get(f'/api/veeam/ml-jobs/{job_id}/status')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'status' in data
    
    def test_delete_ml_job(self, client):
        """Test deleting ML job."""
        # First create a job
        job_data = {
            'name': 'Test Job',
            'algorithm': 'classification',
            'parameters': {'n_estimators': 100},
            'backup_id': 'backup-1'
        }
        
        create_response = client.post('/api/veeam/ml-jobs',
                                    data=json.dumps(job_data),
                                    content_type='application/json')
        
        if create_response.status_code == 201:
            job_id = json.loads(create_response.data)['job_id']
            
            # Delete job
            response = client.delete(f'/api/veeam/ml-jobs/{job_id}')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/api/veeam/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data
        assert 'timestamp' in data

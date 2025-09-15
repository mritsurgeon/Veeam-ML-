from flask import Blueprint, request, jsonify
from src.models.veeam_backup import db, VeeamBackup, MLJob, DataExtraction
from src.services.veeam_api import VeeamDataIntegrationAPI, VeeamAPIError
from src.services.data_extractor import DataExtractionService, DataExtractionError
from src.services.ml_processor import MLProcessingService, MLProcessingError
import logging
import json
import os
from datetime import datetime
import pandas as pd
from typing import Dict, Any

logger = logging.getLogger(__name__)

veeam_bp = Blueprint('veeam', __name__)

# Global instances (in production, these should be properly managed)
veeam_api = None
ml_service = MLProcessingService()

@veeam_bp.route('/config', methods=['POST'])
def configure_veeam_connection():
    """Configure Veeam API connection settings."""
    global veeam_api
    
    try:
        data = request.get_json()
        
        required_fields = ['base_url', 'username', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Initialize Veeam API client
        veeam_api = VeeamDataIntegrationAPI(
            base_url=data['base_url'],
            username=data['username'],
            password=data['password'],
            verify_ssl=data.get('verify_ssl', True)
        )
        
        # Test authentication
        if veeam_api.authenticate():
            return jsonify({
                'message': 'Veeam API connection configured successfully',
                'status': 'connected'
            })
        else:
            return jsonify({'error': 'Failed to authenticate with Veeam API'}), 401
            
    except Exception as e:
        logger.error(f"Failed to configure Veeam connection: {str(e)}")
        return jsonify({'error': str(e)}), 500

@veeam_bp.route('/backups', methods=['GET'])
def list_backups():
    """List available Veeam backups."""
    global veeam_api
    
    if veeam_api is None:
        return jsonify({'error': 'Veeam API not configured'}), 400
    
    try:
        # Get query parameters
        vm_name = request.args.get('vm_name')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Convert date strings to datetime objects if provided
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        # Fetch backups from Veeam API
        backups = veeam_api.get_backups(vm_name=vm_name, start_date=start_dt, end_date=end_dt)
        
        # Store/update backups in database
        for backup_info in backups:
            existing_backup = VeeamBackup.query.filter_by(backup_id=backup_info['id']).first()
            
            if existing_backup:
                # Update existing backup
                existing_backup.backup_name = backup_info.get('name', existing_backup.backup_name)
                existing_backup.backup_path = backup_info.get('path', existing_backup.backup_path)
                existing_backup.backup_size = backup_info.get('size', existing_backup.backup_size)
                existing_backup.updated_at = datetime.utcnow()
            else:
                # Create new backup record
                new_backup = VeeamBackup(
                    backup_id=backup_info['id'],
                    backup_name=backup_info.get('name', 'Unknown'),
                    backup_path=backup_info.get('path', ''),
                    backup_date=datetime.fromisoformat(backup_info['created_date']) if 'created_date' in backup_info else datetime.utcnow(),
                    backup_size=backup_info.get('size', 0)
                )
                db.session.add(new_backup)
        
        db.session.commit()
        
        # Return backup list
        db_backups = VeeamBackup.query.all()
        return jsonify({
            'backups': [backup.to_dict() for backup in db_backups],
            'total_count': len(db_backups)
        })
        
    except VeeamAPIError as e:
        logger.error(f"Veeam API error: {str(e)}")
        return jsonify({'error': f'Veeam API error: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Failed to list backups: {str(e)}")
        return jsonify({'error': str(e)}), 500

@veeam_bp.route('/backups/<int:backup_id>/mount', methods=['POST'])
def mount_backup(backup_id):
    """Mount a Veeam backup as a file system."""
    global veeam_api
    
    if veeam_api is None:
        return jsonify({'error': 'Veeam API not configured'}), 400
    
    try:
        # Get backup from database
        backup = VeeamBackup.query.get_or_404(backup_id)
        
        if backup.status == 'mounted':
            return jsonify({'error': 'Backup is already mounted'}), 400
        
        # Generate mount point
        mount_point = f"/tmp/veeam_mounts/{backup.backup_id}"
        
        # Mount backup using Veeam API
        mount_session = veeam_api.mount_backup(backup.backup_id, mount_point)
        
        # Update backup status
        backup.mount_point = mount_point
        backup.status = 'mounted'
        backup.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Backup mounted successfully',
            'mount_point': mount_point,
            'session_info': mount_session,
            'backup': backup.to_dict()
        })
        
    except VeeamAPIError as e:
        logger.error(f"Failed to mount backup: {str(e)}")
        return jsonify({'error': f'Mount failed: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Failed to mount backup: {str(e)}")
        return jsonify({'error': str(e)}), 500

@veeam_bp.route('/backups/<int:backup_id>/unmount', methods=['POST'])
def unmount_backup(backup_id):
    """Unmount a Veeam backup."""
    global veeam_api
    
    if veeam_api is None:
        return jsonify({'error': 'Veeam API not configured'}), 400
    
    try:
        # Get backup from database
        backup = VeeamBackup.query.get_or_404(backup_id)
        
        if backup.status != 'mounted':
            return jsonify({'error': 'Backup is not currently mounted'}), 400
        
        # Get session ID from request or find it in veeam_api.mount_sessions
        session_id = None
        for sid, session_info in veeam_api.mount_sessions.items():
            if session_info['backup_id'] == backup.backup_id:
                session_id = sid
                break
        
        if session_id:
            # Unmount backup using Veeam API
            success = veeam_api.unmount_backup(session_id)
            
            if success:
                # Update backup status
                backup.mount_point = None
                backup.status = 'available'
                backup.updated_at = datetime.utcnow()
                db.session.commit()
                
                return jsonify({
                    'message': 'Backup unmounted successfully',
                    'backup': backup.to_dict()
                })
            else:
                return jsonify({'error': 'Failed to unmount backup'}), 500
        else:
            return jsonify({'error': 'Mount session not found'}), 404
            
    except VeeamAPIError as e:
        logger.error(f"Failed to unmount backup: {str(e)}")
        return jsonify({'error': f'Unmount failed: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Failed to unmount backup: {str(e)}")
        return jsonify({'error': str(e)}), 500

@veeam_bp.route('/backups/<int:backup_id>/scan', methods=['POST'])
def scan_backup_files(backup_id):
    """Scan files in a mounted backup and identify extractable data."""
    try:
        # Get backup from database
        backup = VeeamBackup.query.get_or_404(backup_id)
        
        if backup.status != 'mounted' or not backup.mount_point:
            return jsonify({'error': 'Backup must be mounted first'}), 400
        
        # Get scan parameters
        data = request.get_json() or {}
        directory_path = data.get('directory_path', '/')
        
        # Initialize data extraction service
        extraction_service = DataExtractionService(backup.mount_point)
        
        # Scan directory for extractable files
        extractable_files = extraction_service.scan_directory(directory_path)
        
        return jsonify({
            'backup_id': backup_id,
            'mount_point': backup.mount_point,
            'scanned_directory': directory_path,
            'extractable_files': extractable_files,
            'total_files': len(extractable_files),
            'extractable_count': sum(1 for f in extractable_files if f['extractable'])
        })
        
    except DataExtractionError as e:
        logger.error(f"Failed to scan backup files: {str(e)}")
        return jsonify({'error': f'Scan failed: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Failed to scan backup files: {str(e)}")
        return jsonify({'error': str(e)}), 500

@veeam_bp.route('/ml-jobs', methods=['POST'])
def create_ml_job():
    """Create a new machine learning job."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['job_name', 'ml_algorithm', 'backup_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate backup exists and is mounted
        backup = VeeamBackup.query.get(data['backup_id'])
        if not backup:
            return jsonify({'error': 'Backup not found'}), 404
        
        if backup.status != 'mounted':
            return jsonify({'error': 'Backup must be mounted first'}), 400
        
        # Create ML job
        ml_job = MLJob(
            job_name=data['job_name'],
            ml_algorithm=data['ml_algorithm'],
            backup_id=data['backup_id'],
            data_source_path=data.get('data_source_path'),
            parameters=json.dumps(data.get('parameters', {}))
        )
        
        db.session.add(ml_job)
        db.session.commit()
        
        return jsonify({
            'message': 'ML job created successfully',
            'ml_job': ml_job.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to create ML job: {str(e)}")
        return jsonify({'error': str(e)}), 500

@veeam_bp.route('/ml-jobs/<int:job_id>/execute', methods=['POST'])
def execute_ml_job(job_id):
    """Execute a machine learning job."""
    try:
        # Get ML job from database
        ml_job = MLJob.query.get_or_404(job_id)
        backup = ml_job.backup
        
        if backup.status != 'mounted':
            return jsonify({'error': 'Associated backup must be mounted'}), 400
        
        # Update job status
        ml_job.status = 'running'
        ml_job.started_at = datetime.utcnow()
        ml_job.progress = 0.0
        db.session.commit()
        
        try:
            # Initialize data extraction service
            extraction_service = DataExtractionService(backup.mount_point)
            
            # Extract data from specified source
            if ml_job.data_source_path:
                # Extract from specific file
                extracted_data = extraction_service.auto_detect_and_extract(ml_job.data_source_path)
            else:
                # Scan and extract from multiple files (simplified for demo)
                extractable_files = extraction_service.scan_directory('/')
                if not extractable_files:
                    raise MLProcessingError("No extractable files found in backup")
                
                # Use the first extractable file for demo
                first_file = next((f for f in extractable_files if f['extractable']), None)
                if not first_file:
                    raise MLProcessingError("No extractable files found")
                
                extracted_data = extraction_service.auto_detect_and_extract(first_file['path'])
            
            # Update progress
            ml_job.progress = 50.0
            db.session.commit()
            
            # Parse job parameters
            parameters = json.loads(ml_job.parameters) if ml_job.parameters else {}
            
            # Execute ML task
            ml_results = ml_service.process_ml_task(
                data=extracted_data,
                task_type=ml_job.ml_algorithm,
                target_column=parameters.get('target_column'),
                **parameters
            )
            
            # Update job with results
            ml_job.status = 'completed'
            ml_job.progress = 100.0
            ml_job.completed_at = datetime.utcnow()
            ml_job.results = json.dumps(ml_results)
            
            # Record data extraction details
            data_extraction = DataExtraction(
                ml_job_id=ml_job.id,
                file_path=ml_job.data_source_path or first_file['path'],
                file_type='auto_detected',
                extraction_method='auto_detect_and_extract',
                extracted_records=len(extracted_data),
                extraction_status='completed'
            )
            db.session.add(data_extraction)
            
            db.session.commit()
            
            return jsonify({
                'message': 'ML job executed successfully',
                'ml_job': ml_job.to_dict(),
                'results': ml_results
            })
            
        except (DataExtractionError, MLProcessingError) as e:
            # Update job with error
            ml_job.status = 'failed'
            ml_job.error_message = str(e)
            ml_job.completed_at = datetime.utcnow()
            db.session.commit()
            
            logger.error(f"ML job {job_id} failed: {str(e)}")
            return jsonify({'error': f'ML job failed: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Failed to execute ML job: {str(e)}")
        return jsonify({'error': str(e)}), 500

@veeam_bp.route('/ml-jobs', methods=['GET'])
def list_ml_jobs():
    """List all ML jobs."""
    try:
        # Get query parameters
        backup_id = request.args.get('backup_id', type=int)
        status = request.args.get('status')
        
        # Build query
        query = MLJob.query
        
        if backup_id:
            query = query.filter_by(backup_id=backup_id)
        
        if status:
            query = query.filter_by(status=status)
        
        # Order by creation date (newest first)
        ml_jobs = query.order_by(MLJob.created_at.desc()).all()
        
        return jsonify({
            'ml_jobs': [job.to_dict() for job in ml_jobs],
            'total_count': len(ml_jobs)
        })
        
    except Exception as e:
        logger.error(f"Failed to list ML jobs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@veeam_bp.route('/ml-jobs/<int:job_id>', methods=['GET'])
def get_ml_job(job_id):
    """Get details of a specific ML job."""
    try:
        ml_job = MLJob.query.get_or_404(job_id)
        
        job_dict = ml_job.to_dict()
        
        # Include parsed results if available
        if ml_job.results:
            try:
                job_dict['parsed_results'] = json.loads(ml_job.results)
            except json.JSONDecodeError:
                job_dict['parsed_results'] = None
        
        # Include data extraction details
        job_dict['data_extractions'] = [
            extraction.to_dict() for extraction in ml_job.data_extractions
        ]
        
        return jsonify(job_dict)
        
    except Exception as e:
        logger.error(f"Failed to get ML job: {str(e)}")
        return jsonify({'error': str(e)}), 500

@veeam_bp.route('/ml-jobs/<int:job_id>', methods=['DELETE'])
def delete_ml_job(job_id):
    """Delete an ML job."""
    try:
        ml_job = MLJob.query.get_or_404(job_id)
        
        # Don't delete running jobs
        if ml_job.status == 'running':
            return jsonify({'error': 'Cannot delete running job'}), 400
        
        db.session.delete(ml_job)
        db.session.commit()
        
        return jsonify({'message': 'ML job deleted successfully'})
        
    except Exception as e:
        logger.error(f"Failed to delete ML job: {str(e)}")
        return jsonify({'error': str(e)}), 500

@veeam_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    global veeam_api
    
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'veeam_api_configured': veeam_api is not None,
        'database_connected': True  # Simplified check
    }
    
    try:
        # Test database connection
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        
        # Test Veeam API connection if configured
        if veeam_api is not None:
            # This is a simplified check - in production you might want to test actual API connectivity
            health_status['veeam_api_authenticated'] = veeam_api.auth_token is not None
        
        return jsonify(health_status)
        
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['error'] = str(e)
        return jsonify(health_status), 500


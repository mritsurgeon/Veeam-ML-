from flask import Blueprint, request, jsonify
from src.models.veeam_backup import db, VeeamBackup, MLJob, DataExtraction
from src.services.unc_file_scanner import scan_unc_path
from src.services.data_extractor import DataExtractionService, DataExtractionError
from src.services.ml_processor import MLProcessingService, MLProcessingError
from src.services.veeam_api import VeeamDataIntegrationAPI, VeeamAPIError
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
        
        # Initialize Veeam API client with mount server configuration
        veeam_api = VeeamDataIntegrationAPI(
            base_url=data['base_url'],
            username=data['username'],
            password=data['password'],
            verify_ssl=data.get('verify_ssl', True),
            mount_server_name=data.get('mount_server_name'),
            mount_server_username=data.get('mount_server_username'),
            mount_server_password=data.get('mount_server_password'),
            mount_host_id=data.get('mount_host_id')
        )
        
        # Test authentication
        try:
            if veeam_api.authenticate():
                return jsonify({
                    'message': 'Veeam API connection configured successfully',
                    'status': 'connected'
                })
            else:
                return jsonify({'error': 'Authentication failed'}), 401
        except VeeamAPIError as e:
            logger.error(f"Veeam API authentication error: {str(e)}")
            return jsonify({'error': str(e)}), 401
            
    except Exception as e:
        logger.error(f"Failed to configure Veeam connection: {str(e)}")
        return jsonify({'error': str(e)}), 500

def identify_os_type(restore_point):
    """
    Identify the OS type from restore point information.
    
    Args:
        restore_point: Restore point data from Veeam API
        
    Returns:
        str: OS type ('windows', 'linux', 'unknown')
    """
    # Check various fields that might indicate OS type
    name = restore_point.get('name', '').lower()
    platform = restore_point.get('platform', '').lower()
    vm_name = restore_point.get('vmName', '').lower()
    backup_object_name = restore_point.get('backup_object_name', '').lower()
    
    # Windows indicators
    windows_indicators = ['windows', 'win', 'server', 'desktop', 'nt', 'vbr', 'target']
    
    # Linux indicators  
    linux_indicators = ['linux', 'ubuntu', 'centos', 'rhel', 'debian', 'suse', 'redhat']
    
    # Check all text fields for OS indicators
    all_text = f"{name} {vm_name} {backup_object_name}".lower()
    
    # Look for Windows indicators
    for indicator in windows_indicators:
        if indicator in all_text:
            return 'windows'
    
    # Look for Linux indicators
    for indicator in linux_indicators:
        if indicator in all_text:
            return 'linux'
    
    # Check platform field
    if 'windows' in platform:
        return 'windows'
    elif 'linux' in platform:
        return 'linux'
    
    # Check for common Windows patterns in names
    if any(pattern in all_text for pattern in ['win-', 'server-', 'desktop-', 'target']):
        return 'windows'
    
    # Default to unknown if we can't determine
    return 'unknown'

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
        
        # Get backup objects first
        backup_objects_url = f"{veeam_api.base_url}/api/v1/backupObjects"
        headers = {
            'accept': 'application/json',
            'x-api-version': '1.2-rev0',
            'Authorization': f'Bearer {veeam_api.auth_token}'
        }
        
        response = veeam_api.session.get(backup_objects_url, headers=headers)
        if response.status_code != 200:
            return jsonify({'error': f'Failed to get backup objects: {response.text}'}), 500
            
        backup_objects_response = response.json()
        backup_objects = backup_objects_response.get('data', [])
        
        # Get restore points for each backup object
        all_restore_points = []
        for backup_obj in backup_objects:
            try:
                # Get restore points for this backup object
                restore_points_url = f"{veeam_api.base_url}/api/v1/backupObjects/{backup_obj['id']}/restorePoints"
                response = veeam_api.session.get(restore_points_url, headers=headers)
                
                if response.status_code == 200:
                    restore_points_response = response.json()
                    restore_points = restore_points_response.get('data', [])
                    
                    # Add restore points with backup object info
                    for rp in restore_points:
                        rp['backup_object_name'] = backup_obj.get('name', 'Unknown')
                        rp['backup_object_id'] = backup_obj['id']
                        all_restore_points.append(rp)
                        
            except Exception as e:
                logger.error(f"Failed to get restore points for {backup_obj['id']}: {str(e)}")
                continue
        
        # Store/update restore points in database (treating them as "backups")
        for restore_point in all_restore_points:
            existing_backup = VeeamBackup.query.filter_by(backup_id=restore_point['id']).first()
            
            # Identify OS type from restore point
            os_type = identify_os_type(restore_point)
            
            if existing_backup:
                # Update existing backup
                existing_backup.backup_name = f"{restore_point.get('backup_object_name', 'Unknown')} - {restore_point.get('name', 'Unknown')}"
                existing_backup.backup_path = restore_point.get('backupFileId', existing_backup.backup_path)
                existing_backup.backup_size = 0  # Restore points don't have size info
                existing_backup.os_type = os_type  # Update OS type
                existing_backup.updated_at = datetime.utcnow()
            else:
                # Create new backup record (actually a restore point)
                new_backup = VeeamBackup(
                    backup_id=restore_point['id'],  # This is the restore point ID we need for mounting
                    backup_name=f"{restore_point.get('backup_object_name', 'Unknown')} - {restore_point.get('name', 'Unknown')}",
                    backup_path=restore_point.get('backupFileId', ''),
                    backup_date=datetime.fromisoformat(restore_point['creationTime'].replace('Z', '+00:00')) if 'creationTime' in restore_point else datetime.utcnow(),
                    backup_size=0,
                    os_type=os_type  # Set OS type
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

@veeam_bp.route('/debug/credentials', methods=['GET'])
def debug_credentials():
    """Debug endpoint to see what credentials are available."""
    global veeam_api
    
    if veeam_api is None:
        return jsonify({'error': 'Veeam API not configured'}), 400
    
    try:
        # Get credentials directly
        credentials_url = f"{veeam_api.base_url}/api/v1/credentials"
        headers = {
            'accept': 'application/json',
            'x-api-version': '1.2-rev0',
            'Authorization': f'Bearer {veeam_api.auth_token}'
        }
        
        response = veeam_api.session.get(credentials_url, headers=headers)
        response.raise_for_status()
        credentials_response = response.json()
        
        return jsonify({
            'credentials': credentials_response
        })
        
    except Exception as e:
        logger.error(f"Failed to get credentials: {str(e)}")
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
        
        # Mount backup using FLR API for direct UNC path access
        mount_session = veeam_api.mount_backup(backup.backup_id)
        session_id = mount_session.get('session_id')
        mount_type = mount_session.get('mount_type', 'FLR')
        
        if not session_id:
            return jsonify({'error': 'Failed to create mount session'}), 500
        
        # Update backup status with actual UNC path
        backup.mount_point = mount_session.get('mount_point', session_id)
        backup.status = 'mounted'
        backup.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Backup mounted successfully',
            'mount_point': mount_session.get('mount_point'),
            'mount_type': mount_type,
            'os_type': backup.os_type,
            'session_info': mount_session,
            'backup': backup.to_dict()
        })
        
    except VeeamAPIError as e:
        logger.error(f"Failed to mount backup: {str(e)}")
        return jsonify({'error': f'Mount failed: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Failed to mount backup: {str(e)}")
        return jsonify({'error': str(e)}), 500

@veeam_bp.route('/mount-sessions', methods=['GET'])
def get_mount_sessions():
    """Get all active mount sessions."""
    global veeam_api
    
    if veeam_api is None:
        return jsonify({'error': 'Veeam API not configured'}), 400
    
    try:
        # Get mount sessions from Veeam API
        sessions = veeam_api.get_mount_sessions()
        
        return jsonify({
            'mount_sessions': sessions,
            'total_count': len(sessions)
        })
        
    except VeeamAPIError as e:
        logger.error(f"Veeam API error: {str(e)}")
        return jsonify({'error': f'Veeam API error: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Failed to get mount sessions: {str(e)}")
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
            try:
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
            except VeeamAPIError as e:
                # Check if the error indicates the session doesn't exist
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in ['not found', 'session not found', 'does not exist', 'invalid session']):
                    # Session doesn't exist in Veeam - assume it's already unmounted
                    logger.warning(f"Session {session_id} not found in Veeam, assuming already unmounted")
                    backup.mount_point = None
                    backup.status = 'available'
                    backup.updated_at = datetime.utcnow()
                    db.session.commit()
                    
                    return jsonify({
                        'message': 'Backup was already unmounted in Veeam - state synchronized',
                        'backup': backup.to_dict()
                    })
                else:
                    # Re-raise other VeeamAPIError exceptions
                    raise e
        else:
            # No session found locally - assume it's already unmounted
            logger.warning(f"No mount session found for backup {backup_id}, assuming already unmounted")
            backup.mount_point = None
            backup.status = 'available'
            backup.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'message': 'Backup was already unmounted - state synchronized',
                'backup': backup.to_dict()
            })
            
    except VeeamAPIError as e:
        logger.error(f"Failed to unmount backup: {str(e)}")
        return jsonify({'error': f'Unmount failed: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Failed to unmount backup: {str(e)}")
        return jsonify({'error': str(e)}), 500

@veeam_bp.route('/backups/<int:backup_id>/scan', methods=['POST'])
def scan_backup_files(backup_id):
    """Scan files in a mounted backup and identify extractable data."""
    global veeam_api
    
    if veeam_api is None:
        return jsonify({'error': 'Veeam API not configured'}), 400
    
    try:
        # Get backup from database
        backup = VeeamBackup.query.get_or_404(backup_id)
        
        if backup.status != 'mounted':
            return jsonify({'error': 'Backup must be mounted first'}), 400
        
        # Get scan parameters
        data = request.get_json() or {}
        directory_path = data.get('directory_path', '/')
        
        # Get session ID from database (stored in mount_point field)
        session_id = backup.mount_point
        if not session_id:
            return jsonify({'error': 'Backup is not mounted'}), 400
        
        # Get mount session info to determine mount type
        mount_session_info = None
        for sid, session_info in veeam_api.mount_sessions.items():
            if sid == session_id:
                mount_session_info = session_info
                break
        
        mount_type = mount_session_info.get('mount_type', 'FLR') if mount_session_info else 'FLR'
        
        # Handle FLR mounts with UNC path access
        if mount_type == 'FLR':
            # FLR mounts provide direct UNC path access
            unc_path = mount_session_info.get('mount_point') if mount_session_info else f"\\\\172.21.234.6\\VeeamFLR\\{session_id}"
            
            try:
                logger.info(f"Scanning UNC path: {unc_path}")
                scanned_files = scan_unc_path(
                    unc_path, 
                    username='Administrator', 
                    password='Veeam123',
                    max_depth=2  # Limit depth to avoid scanning too much
                )
                
                # Filter for extractable files only
                extractable_files = [
                    file for file in scanned_files 
                    if file.get('extractable', False)
                ]
                
                logger.info(f"Found {len(scanned_files)} total files, {len(extractable_files)} extractable")
                
                return jsonify({
                    'backup_id': backup_id,
                    'mount_point': backup.mount_point,
                    'unc_path': unc_path,
                    'mount_type': 'FLR',
                    'os_type': backup.os_type,
                    'session_id': session_id,
                    'scanned_directory': directory_path,
                    'extractable_files': extractable_files,
                    'total_files': len(scanned_files),
                    'extractable_count': len(extractable_files),
                    'message': f'FLR mounted - accessible via UNC path: {unc_path}'
                })
                
            except Exception as e:
                logger.error(f"Failed to scan UNC path {unc_path}: {str(e)}")
                return jsonify({'error': f'Scanning failed: {str(e)}'}), 500
        
        # Fallback for Data Integration mounts (if any)
        return jsonify({
            'backup_id': backup_id,
            'mount_point': backup.mount_point,
            'mount_type': mount_type,
            'os_type': backup.os_type,
            'session_id': session_id,
            'scanned_directory': directory_path,
            'extractable_files': [],
            'total_files': 0,
            'extractable_count': 0,
            'message': f'Mount type {mount_type} - scanning not implemented for this type'
        })
        
    except VeeamAPIError as e:
        logger.error(f"Veeam API error: {str(e)}")
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

@veeam_bp.route('/reconcile-state', methods=['POST'])
def reconcile_mount_state():
    """Reconcile local mount state with actual Veeam server state."""
    global veeam_api
    
    if veeam_api is None:
        return jsonify({'error': 'Veeam API not configured'}), 400
    
    try:
        # Reconcile mount state
        reconciliation_result = veeam_api.reconcile_mount_state()
        
        # Update database backup statuses based on reconciled state
        for session_id, session_info in veeam_api.mount_sessions.items():
            # Find backup in database by backup_id
            backup = VeeamBackup.query.filter_by(backup_id=session_info['backup_id']).first()
            if backup:
                if session_info['state'] == 'Working':
                    backup.status = 'mounted'
                    backup.mount_point = session_info.get('mount_point', session_id)
                else:
                    backup.status = 'available'
                    backup.mount_point = None
                backup.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Mount state reconciled successfully',
            'reconciliation_result': reconciliation_result,
            'active_sessions': len(veeam_api.mount_sessions)
        })
        
    except VeeamAPIError as e:
        logger.error(f"Veeam API error during reconciliation: {str(e)}")
        return jsonify({'error': f'Reconciliation failed: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Failed to reconcile mount state: {str(e)}")
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


"""
Configurable Extraction Job API Routes

This module provides REST API endpoints for managing configurable extraction jobs,
allowing users to create, configure, and monitor data extraction tasks through the UI.
"""

from flask import Blueprint, request, jsonify
from src.models.extraction_job import (
    ExtractionJob, ExtractionJobExecution, ExtractionJobTemplate,
    ExtractionLevel, JobStatus, FileTypeFilter, db, create_default_templates
)
from src.services.extraction_job_service import ExtractionJobService
import logging
import json
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

extraction_bp = Blueprint('extraction', __name__)

# Global service instance
extraction_service = ExtractionJobService()

# Global Veeam API instance (set by main app)
veeam_api = None

def set_veeam_api(api_instance):
    """Set the global Veeam API instance."""
    global veeam_api
    veeam_api = api_instance

@extraction_bp.route('/templates', methods=['GET'])
def list_templates():
    """List available job templates."""
    try:
        templates = ExtractionJobTemplate.query.filter_by(is_public=True).all()
        
        return jsonify({
            'templates': [template.to_dict() for template in templates],
            'total_count': len(templates)
        })
        
    except Exception as e:
        logger.error(f"Failed to list templates: {str(e)}")
        return jsonify({'error': str(e)}), 500

@extraction_bp.route('/templates/<int:template_id>', methods=['GET'])
def get_template(template_id):
    """Get details of a specific template."""
    try:
        template = ExtractionJobTemplate.query.get_or_404(template_id)
        return jsonify(template.to_dict())
        
    except Exception as e:
        logger.error(f"Failed to get template: {str(e)}")
        return jsonify({'error': str(e)}), 500

@extraction_bp.route('/templates', methods=['POST'])
def create_template():
    """Create a new job template."""
    try:
        data = request.get_json()
        
        required_fields = ['name', 'description', 'category', 'configuration']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        template = ExtractionJobTemplate(
            name=data['name'],
            description=data['description'],
            category=data['category'],
            configuration=json.dumps(data['configuration']),
            created_by=data.get('created_by', 'unknown'),
            is_public=data.get('is_public', True)
        )
        
        db.session.add(template)
        db.session.commit()
        
        return jsonify({
            'message': 'Template created successfully',
            'template': template.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to create template: {str(e)}")
        return jsonify({'error': str(e)}), 500

@extraction_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """List extraction jobs."""
    try:
        # Get query parameters
        status = request.args.get('status')
        backup_id = request.args.get('backup_id')
        created_by = request.args.get('created_by')
        
        # Build query
        query = ExtractionJob.query
        
        if status:
            query = query.filter_by(status=JobStatus(status))
        if backup_id:
            query = query.filter_by(backup_id=backup_id)
        if created_by:
            query = query.filter_by(created_by=created_by)
        
        # Order by creation date (newest first)
        jobs = query.order_by(ExtractionJob.created_at.desc()).all()
        
        return jsonify({
            'jobs': [job.to_dict() for job in jobs],
            'total_count': len(jobs)
        })
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@extraction_bp.route('/jobs', methods=['POST'])
def create_job():
    """Create a new extraction job."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'extraction_level', 'backup_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate extraction level
        try:
            ExtractionLevel(data['extraction_level'])
        except ValueError:
            return jsonify({'error': f'Invalid extraction level: {data["extraction_level"]}'}), 400
        
        # Create job
        job = extraction_service.create_job(data, created_by=data.get('created_by'))
        
        return jsonify({
            'message': 'Job created successfully',
            'job': job.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to create job: {str(e)}")
        return jsonify({'error': str(e)}), 500

@extraction_bp.route('/jobs/from-template', methods=['POST'])
def create_job_from_template():
    """Create a job from a template."""
    try:
        data = request.get_json()
        
        required_fields = ['template_id', 'name', 'backup_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        job = extraction_service.create_job_from_template(
            template_id=data['template_id'],
            name=data['name'],
            backup_id=data['backup_id'],
            created_by=data.get('created_by')
        )
        
        return jsonify({
            'message': 'Job created from template successfully',
            'job': job.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to create job from template: {str(e)}")
        return jsonify({'error': str(e)}), 500

@extraction_bp.route('/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    """Get details of a specific job."""
    try:
        job = ExtractionJob.query.get_or_404(job_id)
        
        # Get job status including execution info
        status_info = extraction_service.get_job_status(job_id)
        
        return jsonify(status_info)
        
    except Exception as e:
        logger.error(f"Failed to get job: {str(e)}")
        return jsonify({'error': str(e)}), 500

@extraction_bp.route('/jobs/<int:job_id>/execute', methods=['POST'])
def execute_job(job_id):
    """Execute an extraction job."""
    try:
        if veeam_api is None:
            return jsonify({'error': 'Veeam API not configured'}), 400
        
        execution = extraction_service.execute_job(job_id, veeam_api)
        
        return jsonify({
            'message': 'Job execution started',
            'execution': execution.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Failed to execute job: {str(e)}")
        return jsonify({'error': str(e)}), 500

@extraction_bp.route('/jobs/<int:job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    """Cancel a running job."""
    try:
        success = extraction_service.cancel_job(job_id)
        
        if success:
            return jsonify({'message': 'Job cancelled successfully'})
        else:
            return jsonify({'error': 'Job not found or not running'}), 404
        
    except Exception as e:
        logger.error(f"Failed to cancel job: {str(e)}")
        return jsonify({'error': str(e)}), 500

@extraction_bp.route('/jobs/<int:job_id>/executions', methods=['GET'])
def list_job_executions(job_id):
    """List executions for a specific job."""
    try:
        job = ExtractionJob.query.get_or_404(job_id)
        executions = ExtractionJobExecution.query.filter_by(job_id=job_id)\
            .order_by(ExtractionJobExecution.execution_timestamp.desc()).all()
        
        return jsonify({
            'job': job.to_dict(),
            'executions': [execution.to_dict() for execution in executions],
            'total_count': len(executions)
        })
        
    except Exception as e:
        logger.error(f"Failed to list job executions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@extraction_bp.route('/jobs/<int:job_id>/executions/<int:execution_id>', methods=['GET'])
def get_execution(job_id, execution_id):
    """Get details of a specific execution."""
    try:
        execution = ExtractionJobExecution.query.filter_by(
            id=execution_id, job_id=job_id
        ).first_or_404()
        
        return jsonify(execution.to_dict())
        
    except Exception as e:
        logger.error(f"Failed to get execution: {str(e)}")
        return jsonify({'error': str(e)}), 500

@extraction_bp.route('/jobs/<int:job_id>', methods=['PUT'])
def update_job(job_id):
    """Update job configuration."""
    try:
        job = ExtractionJob.query.get_or_404(job_id)
        
        if job.status != JobStatus.PENDING:
            return jsonify({'error': 'Cannot update job that is not in pending status'}), 400
        
        data = request.get_json()
        
        # Update allowed fields
        updatable_fields = [
            'name', 'description', 'directory_path', 'max_depth', 'max_file_size',
            'chunk_size', 'include_attributes', 'parallel_processing', 'max_workers',
            'enable_document_parsing', 'enable_spreadsheet_parsing', 'enable_presentation_parsing',
            'enable_log_parsing', 'enable_config_parsing', 'enable_sqlite_extraction',
            'enable_sql_dump_parsing', 'enable_enterprise_db_extraction', 'max_db_rows_per_table',
            'output_format', 'include_raw_content', 'include_chunks', 'include_embeddings'
        ]
        
        for field in updatable_fields:
            if field in data:
                setattr(job, field, data[field])
        
        # Handle special fields
        if 'custom_file_types' in data:
            job.custom_file_types = json.dumps(data['custom_file_types'])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Job updated successfully',
            'job': job.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Failed to update job: {str(e)}")
        return jsonify({'error': str(e)}), 500

@extraction_bp.route('/jobs/<int:job_id>', methods=['DELETE'])
def delete_job(job_id):
    """Delete a job."""
    try:
        job = ExtractionJob.query.get_or_404(job_id)
        
        if job.status == JobStatus.RUNNING:
            return jsonify({'error': 'Cannot delete running job'}), 400
        
        db.session.delete(job)
        db.session.commit()
        
        return jsonify({'message': 'Job deleted successfully'})
        
    except Exception as e:
        logger.error(f"Failed to delete job: {str(e)}")
        return jsonify({'error': str(e)}), 500

@extraction_bp.route('/active-jobs', methods=['GET'])
def get_active_jobs():
    """Get currently active jobs."""
    try:
        active_jobs = extraction_service.get_active_jobs()
        
        return jsonify({
            'active_jobs': active_jobs,
            'total_count': len(active_jobs)
        })
        
    except Exception as e:
        logger.error(f"Failed to get active jobs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@extraction_bp.route('/config/levels', methods=['GET'])
def get_extraction_levels():
    """Get available extraction levels."""
    return jsonify({
        'extraction_levels': [
            {
                'value': level.value,
                'label': level.value.replace('_', ' ').title(),
                'description': _get_level_description(level)
            }
            for level in ExtractionLevel
        ]
    })

@extraction_bp.route('/config/file-filters', methods=['GET'])
def get_file_filters():
    """Get available file type filters."""
    return jsonify({
        'file_filters': [
            {
                'value': filter_type.value,
                'label': filter_type.value.replace('_', ' ').title(),
                'description': _get_filter_description(filter_type)
            }
            for filter_type in FileTypeFilter
        ]
    })

@extraction_bp.route('/config/file-types', methods=['GET'])
def get_supported_file_types():
    """Get supported file types for extraction."""
    return jsonify({
        'file_types': {
            'documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf'],
            'spreadsheets': ['.xls', '.xlsx', '.csv'],
            'presentations': ['.ppt', '.pptx'],
            'databases': ['.mdf', '.ldf', '.ndf', '.dbf', '.ora', '.sqlite', '.db', '.sqlite3', '.sql', '.dump'],
            'logs': ['.log', '.txt'],
            'config': ['.ini', '.cfg', '.conf', '.config', '.xml', '.json', '.yaml', '.yml'],
            'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'],
            'audio': ['.mp3', '.wav', '.flac', '.aac'],
            'video': ['.mp4', '.avi', '.mkv', '.mov', '.wmv'],
            'executables': ['.exe', '.dll', '.sys'],
            'archives': ['.zip', '.rar', '.7z', '.tar', '.gz']
        }
    })

@extraction_bp.route('/stats', methods=['GET'])
def get_extraction_stats():
    """Get extraction statistics."""
    try:
        # Get job statistics
        total_jobs = ExtractionJob.query.count()
        completed_jobs = ExtractionJob.query.filter_by(status=JobStatus.COMPLETED).count()
        failed_jobs = ExtractionJob.query.filter_by(status=JobStatus.FAILED).count()
        running_jobs = ExtractionJob.query.filter_by(status=JobStatus.RUNNING).count()
        
        # Get execution statistics
        total_executions = ExtractionJobExecution.query.count()
        successful_executions = ExtractionJobExecution.query.filter_by(status=JobStatus.COMPLETED).count()
        
        # Get template statistics
        total_templates = ExtractionJobTemplate.query.count()
        
        return jsonify({
            'jobs': {
                'total': total_jobs,
                'completed': completed_jobs,
                'failed': failed_jobs,
                'running': running_jobs
            },
            'executions': {
                'total': total_executions,
                'successful': successful_executions
            },
            'templates': {
                'total': total_templates
            },
            'active_jobs': len(extraction_service.active_jobs)
        })
        
    except Exception as e:
        logger.error(f"Failed to get extraction stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

def _get_level_description(level: ExtractionLevel) -> str:
    """Get description for extraction level."""
    descriptions = {
        ExtractionLevel.METADATA_ONLY: "Extract file system metadata only (paths, sizes, timestamps)",
        ExtractionLevel.CONTENT_PARSING: "Extract and parse file content for text analysis",
        ExtractionLevel.DATABASE_EXTRACTION: "Extract structured data from database files",
        ExtractionLevel.FULL_PIPELINE: "Complete extraction pipeline with all levels"
    }
    return descriptions.get(level, "Unknown extraction level")

def _get_filter_description(filter_type: FileTypeFilter) -> str:
    """Get description for file type filter."""
    descriptions = {
        FileTypeFilter.ALL_FILES: "Process all file types",
        FileTypeFilter.DOCUMENTS_ONLY: "Process only document files (PDF, DOCX, TXT, etc.)",
        FileTypeFilter.DATABASES_ONLY: "Process only database files (SQLite, SQL Server, etc.)",
        FileTypeFilter.LOGS_ONLY: "Process only log files",
        FileTypeFilter.CONFIG_ONLY: "Process only configuration files",
        FileTypeFilter.CUSTOM: "Process files matching custom file extensions"
    }
    return descriptions.get(filter_type, "Unknown filter type")

# Initialize default templates on first import
try:
    create_default_templates()
except Exception as e:
    logger.warning(f"Failed to create default templates: {str(e)}")

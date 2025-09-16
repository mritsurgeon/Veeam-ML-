"""
Configurable Extraction Job Service

This service manages configurable extraction jobs with UI-driven configuration,
allowing users to create and manage different types of data extraction tasks.
"""

import os
import logging
import json
import threading
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

from src.models.extraction_job import (
    ExtractionJob, ExtractionJobExecution, ExtractionJobTemplate,
    ExtractionLevel, JobStatus, FileTypeFilter
)
from src.services.veeam_api import VeeamDataIntegrationAPI, VeeamAPIError
from src.services.multi_level_extractor import MultiLevelExtractor
from src.services.unc_file_scanner import scan_unc_path

logger = logging.getLogger(__name__)

class ExtractionJobService:
    """
    Service for managing configurable extraction jobs.
    """
    
    def __init__(self):
        self.active_jobs = {}  # Track running jobs
        self.extractor = MultiLevelExtractor()
    
    def create_job(self, job_config: Dict[str, Any], created_by: str = None) -> ExtractionJob:
        """
        Create a new extraction job from configuration.
        
        Args:
            job_config: Job configuration dictionary
            created_by: User who created the job
            
        Returns:
            Created ExtractionJob instance
        """
        try:
            # Validate required fields
            required_fields = ['name', 'extraction_level', 'backup_id']
            for field in required_fields:
                if field not in job_config:
                    raise ValueError(f"Missing required field: {field}")
            
            # Create job
            job = ExtractionJob(
                name=job_config['name'],
                description=job_config.get('description', ''),
                extraction_level=ExtractionLevel(job_config['extraction_level']),
                file_type_filter=FileTypeFilter(job_config.get('file_type_filter', 'all_files')),
                custom_file_types=json.dumps(job_config.get('custom_file_types', [])),
                backup_id=job_config['backup_id'],
                directory_path=job_config.get('directory_path', '/'),
                max_depth=job_config.get('max_depth', 3),
                max_file_size=job_config.get('max_file_size', 50 * 1024 * 1024),
                chunk_size=job_config.get('chunk_size', 2000),
                include_attributes=job_config.get('include_attributes', False),
                parallel_processing=job_config.get('parallel_processing', True),
                max_workers=job_config.get('max_workers', 4),
                enable_document_parsing=job_config.get('enable_document_parsing', True),
                enable_spreadsheet_parsing=job_config.get('enable_spreadsheet_parsing', True),
                enable_presentation_parsing=job_config.get('enable_presentation_parsing', True),
                enable_log_parsing=job_config.get('enable_log_parsing', True),
                enable_config_parsing=job_config.get('enable_config_parsing', True),
                enable_sqlite_extraction=job_config.get('enable_sqlite_extraction', True),
                enable_sql_dump_parsing=job_config.get('enable_sql_dump_parsing', True),
                enable_enterprise_db_extraction=job_config.get('enable_enterprise_db_extraction', False),
                max_db_rows_per_table=job_config.get('max_db_rows_per_table', 1000),
                output_format=job_config.get('output_format', 'json'),
                include_raw_content=job_config.get('include_raw_content', True),
                include_chunks=job_config.get('include_chunks', True),
                include_embeddings=job_config.get('include_embeddings', False),
                created_by=created_by
            )
            
            from src.models.extraction_job import db
            db.session.add(job)
            db.session.commit()
            
            logger.info(f"Created extraction job: {job.name} (ID: {job.id})")
            return job
            
        except Exception as e:
            logger.error(f"Failed to create extraction job: {str(e)}")
            raise
    
    def create_job_from_template(self, template_id: int, name: str, backup_id: str, 
                                created_by: str = None) -> ExtractionJob:
        """
        Create a job from a predefined template.
        
        Args:
            template_id: ID of the template to use
            name: Name for the new job
            backup_id: Backup ID to extract from
            created_by: User creating the job
            
        Returns:
            Created ExtractionJob instance
        """
        try:
            template = ExtractionJobTemplate.query.get(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            job = template.create_job_from_template(name, backup_id, created_by)
            logger.info(f"Created job from template {template.name}: {job.name} (ID: {job.id})")
            return job
            
        except Exception as e:
            logger.error(f"Failed to create job from template: {str(e)}")
            raise
    
    def execute_job(self, job_id: int, veeam_api: VeeamDataIntegrationAPI) -> ExtractionJobExecution:
        """
        Execute an extraction job.
        
        Args:
            job_id: ID of the job to execute
            veeam_api: Veeam API instance
            
        Returns:
            ExtractionJobExecution instance
        """
        try:
            job = ExtractionJob.query.get(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            if job.status != JobStatus.PENDING:
                raise ValueError(f"Job {job_id} is not in pending status")
            
            # Create execution record
            execution = ExtractionJobExecution(
                job_id=job.id,
                status=JobStatus.PENDING
            )
            
            from src.models.extraction_job import db
            db.session.add(execution)
            db.session.commit()
            
            # Start execution in background thread
            thread = threading.Thread(
                target=self._execute_job_background,
                args=(job, execution, veeam_api)
            )
            thread.daemon = True
            thread.start()
            
            # Track active job
            self.active_jobs[job_id] = {
                'job': job,
                'execution': execution,
                'thread': thread,
                'start_time': datetime.utcnow()
            }
            
            logger.info(f"Started execution of job {job.name} (Execution ID: {execution.id})")
            return execution
            
        except Exception as e:
            logger.error(f"Failed to execute job {job_id}: {str(e)}")
            raise
    
    def _execute_job_background(self, job: ExtractionJob, execution: ExtractionJobExecution, 
                               veeam_api: VeeamDataIntegrationAPI):
        """
        Execute job in background thread.
        
        Args:
            job: Job to execute
            execution: Execution record
            veeam_api: Veeam API instance
        """
        try:
            # Update job status
            job.set_status(JobStatus.RUNNING)
            execution.status = JobStatus.RUNNING
            
            # Get mount session info
            session_id = None
            mount_type = 'FLR'
            unc_path = None
            
            # Find the mount session for this backup
            for sid, session_info in veeam_api.mount_sessions.items():
                if session_info.get('backup_id') == job.backup_id:
                    session_id = sid
                    mount_type = session_info.get('mount_type', 'FLR')
                    unc_path = session_info.get('mount_point')
                    break
            
            if not session_id:
                raise ValueError(f"No active mount session found for backup {job.backup_id}")
            
            execution.session_id = session_id
            execution.mount_type = mount_type
            execution.unc_path = unc_path
            
            # Execute based on extraction level
            if job.extraction_level == ExtractionLevel.METADATA_ONLY:
                results = self._execute_metadata_extraction(job, execution, veeam_api)
            elif job.extraction_level == ExtractionLevel.CONTENT_PARSING:
                results = self._execute_content_extraction(job, execution, veeam_api)
            elif job.extraction_level == ExtractionLevel.DATABASE_EXTRACTION:
                results = self._execute_database_extraction(job, execution, veeam_api)
            elif job.extraction_level == ExtractionLevel.FULL_PIPELINE:
                results = self._execute_full_pipeline(job, execution, veeam_api)
            else:
                raise ValueError(f"Unknown extraction level: {job.extraction_level}")
            
            # Update execution results
            execution.files_processed = results.get('files_processed', 0)
            execution.chunks_created = results.get('chunks_created', 0)
            execution.databases_extracted = results.get('databases_extracted', 0)
            execution.errors_count = results.get('errors_count', 0)
            execution.results_data = json.dumps(results.get('results', {}))
            execution.status = JobStatus.COMPLETED
            
            # Update job results
            job.results_summary = json.dumps({
                'total_files': results.get('total_files', 0),
                'processed_files': results.get('files_processed', 0),
                'failed_files': results.get('errors_count', 0),
                'chunks_created': results.get('chunks_created', 0),
                'databases_extracted': results.get('databases_extracted', 0),
                'execution_time': results.get('execution_time', 0),
                'extraction_level': job.extraction_level.value
            })
            job.set_status(JobStatus.COMPLETED)
            
            logger.info(f"Completed execution of job {job.name}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Job execution failed: {error_msg}")
            logger.error(traceback.format_exc())
            
            execution.error_log = traceback.format_exc()
            execution.status = JobStatus.FAILED
            job.set_status(JobStatus.FAILED, error_msg)
            
        finally:
            # Clean up active job tracking
            if job.id in self.active_jobs:
                del self.active_jobs[job.id]
            
            from src.models.extraction_job import db
            db.session.commit()
    
    def _execute_metadata_extraction(self, job: ExtractionJob, execution: ExtractionJobExecution, 
                                   veeam_api: VeeamDataIntegrationAPI) -> Dict[str, Any]:
        """Execute metadata-only extraction."""
        start_time = time.time()
        
        try:
            # Extract file system metadata using Veeam API
            metadata = veeam_api.extract_file_system_metadata(
                session_id=execution.session_id,
                mount_type=execution.mount_type,
                max_depth=job.max_depth,
                include_attributes=job.include_attributes
            )
            
            # Filter files based on job configuration
            filtered_files = self._filter_files(metadata['files'], job)
            
            results = {
                'total_files': len(metadata['files']),
                'files_processed': len(filtered_files),
                'chunks_created': 0,
                'databases_extracted': 0,
                'errors_count': 0,
                'execution_time': time.time() - start_time,
                'results': {
                    'metadata': metadata,
                    'filtered_files': filtered_files,
                    'statistics': metadata['statistics']
                }
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Metadata extraction failed: {str(e)}")
            raise
    
    def _execute_content_extraction(self, job: ExtractionJob, execution: ExtractionJobExecution, 
                                  veeam_api: VeeamDataIntegrationAPI) -> Dict[str, Any]:
        """Execute content parsing extraction."""
        start_time = time.time()
        
        try:
            # Get file list
            metadata = veeam_api.extract_file_system_metadata(
                session_id=execution.session_id,
                mount_type=execution.mount_type,
                max_depth=job.max_depth,
                include_attributes=job.include_attributes
            )
            
            # Filter files for content extraction
            content_files = [
                f for f in metadata['files'] 
                if self._should_extract_content(f, job)
            ]
            
            job.total_files = len(content_files)
            job.update_progress(0)
            
            # Process files
            results = {
                'total_files': len(content_files),
                'files_processed': 0,
                'chunks_created': 0,
                'databases_extracted': 0,
                'errors_count': 0,
                'execution_time': 0,
                'results': {
                    'extracted_files': [],
                    'chunks': [],
                    'errors': []
                }
            }
            
            if job.parallel_processing:
                results = self._process_files_parallel(content_files, job, execution, results)
            else:
                results = self._process_files_sequential(content_files, job, execution, results)
            
            results['execution_time'] = time.time() - start_time
            return results
            
        except Exception as e:
            logger.error(f"Content extraction failed: {str(e)}")
            raise
    
    def _execute_database_extraction(self, job: ExtractionJob, execution: ExtractionJobExecution, 
                                    veeam_api: VeeamDataIntegrationAPI) -> Dict[str, Any]:
        """Execute database extraction."""
        start_time = time.time()
        
        try:
            # Get file list
            metadata = veeam_api.extract_file_system_metadata(
                session_id=execution.session_id,
                mount_type=execution.mount_type,
                max_depth=job.max_depth,
                include_attributes=job.include_attributes
            )
            
            # Filter database files
            db_files = [
                f for f in metadata['files'] 
                if f.get('file_type') in ['sqlite_db', 'sqlserver_db', 'oracle_db', 'sql_dump']
            ]
            
            job.total_files = len(db_files)
            job.update_progress(0)
            
            results = {
                'total_files': len(db_files),
                'files_processed': 0,
                'chunks_created': 0,
                'databases_extracted': 0,
                'errors_count': 0,
                'execution_time': 0,
                'results': {
                    'extracted_databases': [],
                    'errors': []
                }
            }
            
            # Process database files
            for file_info in db_files:
                try:
                    unc_path = f"{execution.unc_path}\\{file_info['path']}"
                    db_data = self.extractor.extract_data(
                        file_info=file_info,
                        unc_path=unc_path,
                        extraction_level='database'
                    )
                    
                    results['results']['extracted_databases'].append(db_data)
                    results['databases_extracted'] += 1
                    results['files_processed'] += 1
                    
                    job.update_progress(results['files_processed'])
                    
                except Exception as e:
                    logger.error(f"Failed to extract database {file_info['name']}: {str(e)}")
                    results['errors_count'] += 1
                    results['results']['errors'].append({
                        'file': file_info['name'],
                        'error': str(e)
                    })
            
            results['execution_time'] = time.time() - start_time
            return results
            
        except Exception as e:
            logger.error(f"Database extraction failed: {str(e)}")
            raise
    
    def _execute_full_pipeline(self, job: ExtractionJob, execution: ExtractionJobExecution, 
                              veeam_api: VeeamDataIntegrationAPI) -> Dict[str, Any]:
        """Execute full pipeline extraction."""
        start_time = time.time()
        
        try:
            # Get file list
            metadata = veeam_api.extract_file_system_metadata(
                session_id=execution.session_id,
                mount_type=execution.mount_type,
                max_depth=job.max_depth,
                include_attributes=job.include_attributes
            )
            
            # Filter files
            filtered_files = self._filter_files(metadata['files'], job)
            job.total_files = len(filtered_files)
            job.update_progress(0)
            
            results = {
                'total_files': len(filtered_files),
                'files_processed': 0,
                'chunks_created': 0,
                'databases_extracted': 0,
                'errors_count': 0,
                'execution_time': 0,
                'results': {
                    'metadata': metadata,
                    'extracted_files': [],
                    'chunks': [],
                    'databases': [],
                    'errors': []
                }
            }
            
            # Process all files
            for file_info in filtered_files:
                try:
                    unc_path = f"{execution.unc_path}\\{file_info['path']}"
                    
                    # Determine extraction level for this file
                    extraction_level = self._determine_file_extraction_level(file_info, job)
                    
                    extracted_data = self.extractor.extract_data(
                        file_info=file_info,
                        unc_path=unc_path,
                        extraction_level=extraction_level
                    )
                    
                    results['results']['extracted_files'].append(extracted_data)
                    
                    if extracted_data.get('chunks'):
                        results['results']['chunks'].extend(extracted_data['chunks'])
                        results['chunks_created'] += len(extracted_data['chunks'])
                    
                    if extracted_data.get('extracted_data', {}).get('level') == 'database':
                        results['results']['databases'].append(extracted_data)
                        results['databases_extracted'] += 1
                    
                    results['files_processed'] += 1
                    job.update_progress(results['files_processed'])
                    
                except Exception as e:
                    logger.error(f"Failed to process file {file_info['name']}: {str(e)}")
                    results['errors_count'] += 1
                    results['results']['errors'].append({
                        'file': file_info['name'],
                        'error': str(e)
                    })
            
            results['execution_time'] = time.time() - start_time
            return results
            
        except Exception as e:
            logger.error(f"Full pipeline extraction failed: {str(e)}")
            raise
    
    def _filter_files(self, files: List[Dict[str, Any]], job: ExtractionJob) -> List[Dict[str, Any]]:
        """Filter files based on job configuration."""
        filtered = []
        
        for file_info in files:
            if file_info.get('is_directory', False):
                continue
            
            # Apply file type filter
            if job.file_type_filter == FileTypeFilter.ALL_FILES:
                filtered.append(file_info)
            elif job.file_type_filter == FileTypeFilter.DOCUMENTS_ONLY:
                if file_info.get('file_type') in ['document', 'spreadsheet', 'presentation']:
                    filtered.append(file_info)
            elif job.file_type_filter == FileTypeFilter.DATABASES_ONLY:
                if file_info.get('file_type') in ['sqlite_db', 'sqlserver_db', 'oracle_db', 'sql_dump']:
                    filtered.append(file_info)
            elif job.file_type_filter == FileTypeFilter.LOGS_ONLY:
                if file_info.get('file_type') == 'log':
                    filtered.append(file_info)
            elif job.file_type_filter == FileTypeFilter.CONFIG_ONLY:
                if file_info.get('file_type') == 'config':
                    filtered.append(file_info)
            elif job.file_type_filter == FileTypeFilter.CUSTOM:
                custom_types = json.loads(job.custom_file_types) if job.custom_file_types else []
                file_ext = os.path.splitext(file_info.get('name', ''))[1].lower()
                if file_ext in custom_types:
                    filtered.append(file_info)
        
        return filtered
    
    def _should_extract_content(self, file_info: Dict[str, Any], job: ExtractionJob) -> bool:
        """Determine if file should have content extracted."""
        file_type = file_info.get('file_type', 'unknown')
        file_size = file_info.get('size', 0)
        
        # Check file size limit
        if file_size > job.max_file_size:
            return False
        
        # Check if parsing is enabled for this file type
        if file_type == 'document' and not job.enable_document_parsing:
            return False
        elif file_type == 'spreadsheet' and not job.enable_spreadsheet_parsing:
            return False
        elif file_type == 'presentation' and not job.enable_presentation_parsing:
            return False
        elif file_type == 'log' and not job.enable_log_parsing:
            return False
        elif file_type == 'config' and not job.enable_config_parsing:
            return False
        
        return True
    
    def _determine_file_extraction_level(self, file_info: Dict[str, Any], job: ExtractionJob) -> str:
        """Determine extraction level for a specific file."""
        file_type = file_info.get('file_type', 'unknown')
        
        if file_type in ['sqlite_db', 'sqlserver_db', 'oracle_db', 'sql_dump']:
            return 'database'
        elif file_type in ['document', 'spreadsheet', 'presentation', 'log', 'config']:
            return 'content'
        else:
            return 'metadata'
    
    def _process_files_parallel(self, files: List[Dict[str, Any]], job: ExtractionJob, 
                               execution: ExtractionJobExecution, results: Dict[str, Any]) -> Dict[str, Any]:
        """Process files in parallel."""
        with ThreadPoolExecutor(max_workers=job.max_workers) as executor:
            future_to_file = {}
            
            for file_info in files:
                future = executor.submit(self._process_single_file, file_info, job, execution)
                future_to_file[future] = file_info
            
            for future in as_completed(future_to_file):
                file_info = future_to_file[future]
                try:
                    result = future.result()
                    results['results']['extracted_files'].append(result)
                    
                    if result.get('chunks'):
                        results['results']['chunks'].extend(result['chunks'])
                        results['chunks_created'] += len(result['chunks'])
                    
                    results['files_processed'] += 1
                    job.update_progress(results['files_processed'])
                    
                except Exception as e:
                    logger.error(f"Failed to process file {file_info['name']}: {str(e)}")
                    results['errors_count'] += 1
                    results['results']['errors'].append({
                        'file': file_info['name'],
                        'error': str(e)
                    })
        
        return results
    
    def _process_files_sequential(self, files: List[Dict[str, Any]], job: ExtractionJob, 
                                execution: ExtractionJobExecution, results: Dict[str, Any]) -> Dict[str, Any]:
        """Process files sequentially."""
        for file_info in files:
            try:
                result = self._process_single_file(file_info, job, execution)
                results['results']['extracted_files'].append(result)
                
                if result.get('chunks'):
                    results['results']['chunks'].extend(result['chunks'])
                    results['chunks_created'] += len(result['chunks'])
                
                results['files_processed'] += 1
                job.update_progress(results['files_processed'])
                
            except Exception as e:
                logger.error(f"Failed to process file {file_info['name']}: {str(e)}")
                results['errors_count'] += 1
                results['results']['errors'].append({
                    'file': file_info['name'],
                    'error': str(e)
                })
        
        return results
    
    def _process_single_file(self, file_info: Dict[str, Any], job: ExtractionJob, 
                           execution: ExtractionJobExecution) -> Dict[str, Any]:
        """Process a single file."""
        unc_path = f"{execution.unc_path}\\{file_info['path']}"
        extraction_level = self._determine_file_extraction_level(file_info, job)
        
        return self.extractor.extract_data(
            file_info=file_info,
            unc_path=unc_path,
            extraction_level=extraction_level
        )
    
    def get_job_status(self, job_id: int) -> Dict[str, Any]:
        """Get current status of a job."""
        if job_id in self.active_jobs:
            job_info = self.active_jobs[job_id]
            job = job_info['job']
            execution = job_info['execution']
            start_time = job_info['start_time']
            
            return {
                'job': job.to_dict(),
                'execution': execution.to_dict(),
                'is_running': True,
                'runtime': (datetime.utcnow() - start_time).total_seconds()
            }
        else:
            job = ExtractionJob.query.get(job_id)
            if job:
                return {
                    'job': job.to_dict(),
                    'execution': None,
                    'is_running': False,
                    'runtime': 0
                }
            else:
                raise ValueError(f"Job {job_id} not found")
    
    def cancel_job(self, job_id: int) -> bool:
        """Cancel a running job."""
        if job_id in self.active_jobs:
            job_info = self.active_jobs[job_id]
            job = job_info['job']
            execution = job_info['execution']
            
            # Note: Thread cancellation is not easily implemented in Python
            # This is a placeholder for future implementation
            job.set_status(JobStatus.CANCELLED)
            execution.status = JobStatus.CANCELLED
            
            del self.active_jobs[job_id]
            
            from src.models.extraction_job import db
            db.session.commit()
            
            logger.info(f"Cancelled job {job.name}")
            return True
        else:
            return False
    
    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get list of currently active jobs."""
        return [
            {
                'job_id': job_id,
                'job_name': job_info['job'].name,
                'status': job_info['job'].status.value,
                'progress': job_info['job'].progress_percentage,
                'start_time': job_info['start_time'].isoformat(),
                'runtime': (datetime.utcnow() - job_info['start_time']).total_seconds()
            }
            for job_id, job_info in self.active_jobs.items()
        ]

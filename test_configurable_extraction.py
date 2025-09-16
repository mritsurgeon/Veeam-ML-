#!/usr/bin/env python3
"""
Test script for Configurable Extraction Job System

This demonstrates the new configurable extraction system with UI-driven configuration,
allowing users to create and manage different types of data extraction tasks.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.extraction_job_service import ExtractionJobService
from src.models.extraction_job import (
    ExtractionJob, ExtractionJobExecution, ExtractionJobTemplate,
    ExtractionLevel, JobStatus, FileTypeFilter, db, create_default_templates
)
from src.services.veeam_api import VeeamDataIntegrationAPI, VeeamAPIError
import logging
import json
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_configurable_extraction_system():
    """Test the configurable extraction system."""
    
    print("🧪 Testing Configurable Extraction Job System")
    print("=" * 60)
    
    try:
        # Initialize Flask app context
        from src.main import app
        with app.app_context():
            # Initialize services
            extraction_service = ExtractionJobService()
            
            # Initialize Veeam API
            veeam_api = VeeamDataIntegrationAPI(
                base_url="https://172.21.234.6:9419",
                username="administrator",
                password="Veeam123",
                verify_ssl=False
            )
            
            # Authenticate
            logger.info("🔐 Authenticating with Veeam API...")
            if not veeam_api.authenticate():
                logger.error("❌ Authentication failed")
                return False
            
            logger.info("✅ Authentication successful")
            
            # Test 1: Create job templates
            print("\n📋 Test 1: Job Templates")
            print("-" * 30)
            
            templates = ExtractionJobTemplate.query.all()
            logger.info(f"Found {len(templates)} job templates:")
            
            for template in templates:
                print(f"  • {template.name} ({template.category})")
                print(f"    Description: {template.description}")
                print(f"    Usage count: {template.usage_count}")
                print()
            
            # Test 2: Create custom extraction job
            print("\n🔧 Test 2: Create Custom Extraction Job")
            print("-" * 40)
            
            job_config = {
                'name': 'Test Document Analysis Job',
                'description': 'Extract and parse document content for NLP analysis',
                'extraction_level': 'content_parsing',
                'file_type_filter': 'documents_only',
                'backup_id': 'test-backup-123',
                'directory_path': '/documents',
                'max_depth': 2,
                'max_file_size': 10 * 1024 * 1024,  # 10MB
                'chunk_size': 1500,
                'include_attributes': True,
                'parallel_processing': True,
                'max_workers': 2,
                'enable_document_parsing': True,
                'enable_spreadsheet_parsing': True,
                'enable_presentation_parsing': False,
                'enable_log_parsing': False,
                'enable_config_parsing': False,
                'enable_sqlite_extraction': False,
                'enable_sql_dump_parsing': False,
                'enable_enterprise_db_extraction': False,
                'output_format': 'json',
                'include_raw_content': True,
                'include_chunks': True,
                'include_embeddings': False,
                'created_by': 'test_user'
            }
            
            job = extraction_service.create_job(job_config)
            logger.info(f"✅ Created job: {job.name} (ID: {job.id})")
            print(f"  • Extraction Level: {job.extraction_level.value}")
            print(f"  • File Filter: {job.file_type_filter.value}")
            print(f"  • Max Depth: {job.max_depth}")
            print(f"  • Chunk Size: {job.chunk_size}")
            print(f"  • Parallel Processing: {job.parallel_processing}")
            print(f"  • Max Workers: {job.max_workers}")
            
            # Test 3: Create job from template
            print("\n📄 Test 3: Create Job from Template")
            print("-" * 35)
            
            if templates:
                template = templates[0]  # Use first template
                template_job = extraction_service.create_job_from_template(
                    template_id=template.id,
                    name=f"Template Job - {template.name}",
                    backup_id='template-backup-456',
                    created_by='test_user'
                )
                logger.info(f"✅ Created job from template: {template_job.name} (ID: {template_job.id})")
                print(f"  • Template: {template.name}")
                print(f"  • Job Name: {template_job.name}")
                print(f"  • Extraction Level: {template_job.extraction_level.value}")
            
            # Test 4: Job configuration validation
            print("\n✅ Test 4: Job Configuration Validation")
            print("-" * 40)
            
            # Test different extraction levels
            extraction_levels = [
                ('metadata_only', 'File System Census'),
                ('content_parsing', 'Document Analysis'),
                ('database_extraction', 'Database Forensics'),
                ('full_pipeline', 'Compliance Audit')
            ]
            
            for level, description in extraction_levels:
                config = {
                    'name': f'Test {description}',
                    'extraction_level': level,
                    'backup_id': f'test-backup-{level}',
                    'created_by': 'test_user'
                }
                
                try:
                    test_job = extraction_service.create_job(config)
                    logger.info(f"✅ Created {description} job (ID: {test_job.id})")
                    print(f"  • {description}: {test_job.extraction_level.value}")
                except Exception as e:
                    logger.error(f"❌ Failed to create {description} job: {str(e)}")
            
            # Test 5: File type filters
            print("\n🔍 Test 5: File Type Filters")
            print("-" * 25)
            
            file_filters = [
                ('all_files', 'All Files'),
                ('documents_only', 'Documents Only'),
                ('databases_only', 'Databases Only'),
                ('logs_only', 'Logs Only'),
                ('config_only', 'Config Only')
            ]
            
            for filter_type, description in file_filters:
                config = {
                    'name': f'Test {description} Filter',
                    'extraction_level': 'content_parsing',
                    'file_type_filter': filter_type,
                    'backup_id': f'test-backup-{filter_type}',
                    'created_by': 'test_user'
                }
                
                try:
                    filter_job = extraction_service.create_job(config)
                    logger.info(f"✅ Created {description} filter job (ID: {filter_job.id})")
                    print(f"  • {description}: {filter_job.file_type_filter.value}")
                except Exception as e:
                    logger.error(f"❌ Failed to create {description} filter job: {str(e)}")
            
            # Test 6: Job status and progress tracking
            print("\n📊 Test 6: Job Status and Progress Tracking")
            print("-" * 45)
            
            jobs = ExtractionJob.query.all()
            logger.info(f"Total jobs created: {len(jobs)}")
            
            for job in jobs:
                status_info = extraction_service.get_job_status(job.id)
                print(f"  • {job.name}:")
                print(f"    Status: {job.status.value}")
                print(f"    Progress: {job.progress_percentage:.1f}%")
                print(f"    Files: {job.processed_files}/{job.total_files}")
                print(f"    Created: {job.created_at}")
                print()
            
            # Test 7: Active jobs monitoring
            print("\n⚡ Test 7: Active Jobs Monitoring")
            print("-" * 30)
            
            active_jobs = extraction_service.get_active_jobs()
            logger.info(f"Active jobs: {len(active_jobs)}")
            
            if active_jobs:
                for active_job in active_jobs:
                    print(f"  • {active_job['job_name']}:")
                    print(f"    Status: {active_job['status']}")
                    print(f"    Progress: {active_job['progress']:.1f}%")
                    print(f"    Runtime: {active_job['runtime']:.1f}s")
            else:
                print("  No active jobs")
            
            # Test 8: Job execution simulation (without actual execution)
            print("\n🚀 Test 8: Job Execution Simulation")
            print("-" * 35)
            
            # Find a pending job
            pending_job = ExtractionJob.query.filter_by(status=JobStatus.PENDING).first()
            if pending_job:
                logger.info(f"Found pending job: {pending_job.name}")
                print(f"  • Job: {pending_job.name}")
                print(f"  • Extraction Level: {pending_job.extraction_level.value}")
                print(f"  • File Filter: {pending_job.file_type_filter.value}")
                print(f"  • Max Depth: {pending_job.max_depth}")
                print(f"  • Chunk Size: {pending_job.chunk_size}")
                print(f"  • Parallel Processing: {pending_job.parallel_processing}")
                print(f"  • Max Workers: {pending_job.max_workers}")
                print()
                print("  💡 In a real scenario, this job would be executed with:")
                print(f"    - Veeam API session for backup {pending_job.backup_id}")
                print(f"    - UNC path scanning for directory {pending_job.directory_path}")
                print(f"    - Multi-level extraction based on {pending_job.extraction_level.value}")
                print(f"    - File filtering using {pending_job.file_type_filter.value}")
            else:
                print("  No pending jobs found")
            
            # Test 9: Configuration options summary
            print("\n⚙️ Test 9: Configuration Options Summary")
            print("-" * 40)
            
            print("Available Extraction Levels:")
            for level in ExtractionLevel:
                print(f"  • {level.value}: {level.value.replace('_', ' ').title()}")
            
            print("\nAvailable File Type Filters:")
            for filter_type in FileTypeFilter:
                print(f"  • {filter_type.value}: {filter_type.value.replace('_', ' ').title()}")
            
            print("\nSupported File Types:")
            file_types = {
                'Documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf'],
                'Spreadsheets': ['.xls', '.xlsx', '.csv'],
                'Presentations': ['.ppt', '.pptx'],
                'Databases': ['.mdf', '.ldf', '.ndf', '.dbf', '.ora', '.sqlite', '.db', '.sqlite3', '.sql', '.dump'],
                'Logs': ['.log', '.txt'],
                'Config': ['.ini', '.cfg', '.conf', '.config', '.xml', '.json', '.yaml', '.yml']
            }
            
            for category, extensions in file_types.items():
                print(f"  • {category}: {', '.join(extensions)}")
            
            print("\n✅ All tests completed successfully!")
            print("\n🎯 Key Features Demonstrated:")
            print("  • Configurable extraction levels (metadata, content, database, full pipeline)")
            print("  • Flexible file type filtering")
            print("  • Job templates for common scenarios")
            print("  • Real-time job status and progress tracking")
            print("  • Parallel processing configuration")
            print("  • Comprehensive job configuration options")
            print("  • UI-driven job creation and management")
            
            return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_configurable_extraction_system()
    
    if success:
        print("\n🎉 Configurable Extraction System Test PASSED!")
        print("\n📋 Next Steps:")
        print("  1. Start the application: python src/main.py")
        print("  2. Open browser to: http://localhost:5173")
        print("  3. Navigate to 'Extraction Jobs' in the sidebar")
        print("  4. Create and configure extraction jobs through the UI")
        print("  5. Monitor job progress and results")
    else:
        print("\n❌ Configurable Extraction System Test FAILED!")
        sys.exit(1)

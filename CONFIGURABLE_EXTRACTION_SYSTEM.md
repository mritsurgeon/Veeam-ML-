# Configurable Multi-Level Data Extraction System

## Overview

This document describes the implementation of a comprehensive, configurable multi-level data extraction system for the Veeam ML Integration Platform. The system provides three distinct extraction levels with full UI configurability and job management capabilities.

## 🎯 Key Features Implemented

### 1. **Configurable Extraction Levels**
- **Metadata Only**: File system census with paths, sizes, timestamps, and extended attributes
- **Content Parsing**: Document, spreadsheet, presentation, log, and config file content extraction
- **Database Extraction**: SQLite, SQL Server, Oracle, PostgreSQL, MySQL database content extraction
- **Full Pipeline**: Complete multi-level extraction combining all approaches

### 2. **Flexible File Type Filtering**
- **All Files**: Process all file types
- **Documents Only**: PDF, DOCX, TXT, RTF files
- **Databases Only**: SQLite, SQL Server, Oracle database files
- **Logs Only**: Log files for security analysis
- **Config Only**: Configuration files
- **Custom**: User-defined file extensions

### 3. **Job Templates System**
- **File System Census**: Metadata extraction for analytics
- **Document Analysis**: Content parsing for NLP analysis
- **Database Forensics**: Database extraction for forensic analysis
- **Compliance Audit**: Full pipeline for compliance auditing
- **Log Analysis**: Log file parsing for security analysis

### 4. **Real-Time Job Management**
- Job creation and configuration through UI
- Real-time progress tracking
- Active job monitoring
- Job cancellation and status updates
- Execution history and results

### 5. **Advanced Configuration Options**
- Parallel processing with configurable worker count
- Chunk size configuration for text processing
- File size limits and depth controls
- Output format selection (JSON, CSV, Parquet)
- Content inclusion options (raw content, chunks, embeddings)

## 🏗️ Architecture

### Backend Components

#### 1. **Database Models** (`src/models/extraction_job.py`)
```python
class ExtractionJob(db.Model):
    # Job configuration and status
    extraction_level = db.Column(db.Enum(ExtractionLevel))
    file_type_filter = db.Column(db.Enum(FileTypeFilter))
    # Processing options
    parallel_processing = db.Column(db.Boolean)
    max_workers = db.Column(db.Integer)
    # Content parsing options
    enable_document_parsing = db.Column(db.Boolean)
    enable_spreadsheet_parsing = db.Column(db.Boolean)
    # Database extraction options
    enable_sqlite_extraction = db.Column(db.Boolean)
    enable_enterprise_db_extraction = db.Column(db.Boolean)
```

#### 2. **Extraction Service** (`src/services/extraction_job_service.py`)
- Job creation and management
- Template-based job creation
- Background job execution
- Progress tracking and status updates
- Multi-level extraction orchestration

#### 3. **Multi-Level Extractor** (`src/services/multi_level_extractor.py`)
- File type classification
- Content parsing with specialized libraries
- Database extraction capabilities
- Text chunking for ML processing
- Error handling and recovery

#### 4. **API Routes** (`src/routes/extraction_routes.py`)
- RESTful API for job management
- Template management endpoints
- Configuration options API
- Job execution and monitoring endpoints

### Frontend Components

#### 1. **ExtractionJobManager** (`veeam-ml-frontend/src/components/ExtractionJobManager.jsx`)
- Comprehensive job creation form with tabs
- Template selection and customization
- Real-time job monitoring dashboard
- Active job progress tracking
- Job status management

#### 2. **UI Features**
- **Basic Configuration**: Job name, description, extraction level, file filters
- **Scope Configuration**: Directory path, max depth, file size limits
- **Processing Configuration**: Chunk size, parallel processing, worker count
- **Output Configuration**: Format selection, content inclusion options

## 🔧 Configuration Options

### Extraction Levels

| Level | Description | Use Cases |
|-------|-------------|-----------|
| `metadata_only` | File system metadata only | File system census, inventory reports |
| `content_parsing` | Document content extraction | NLP analysis, document classification |
| `database_extraction` | Database content extraction | Forensic analysis, data migration |
| `full_pipeline` | Complete multi-level extraction | Compliance auditing, comprehensive analysis |

### File Type Filters

| Filter | Description | File Types |
|--------|-------------|------------|
| `all_files` | Process all file types | All supported file types |
| `documents_only` | Document files only | PDF, DOCX, TXT, RTF |
| `databases_only` | Database files only | SQLite, SQL Server, Oracle, MySQL |
| `logs_only` | Log files only | .log, .txt files |
| `config_only` | Configuration files only | .ini, .cfg, .conf, .xml, .json |
| `custom` | User-defined extensions | Custom file extension list |

### Processing Options

- **Parallel Processing**: Enable/disable parallel file processing
- **Max Workers**: Number of parallel workers (1-16)
- **Chunk Size**: Text chunk size for ML processing (default: 2000)
- **Max File Size**: Maximum file size to process (default: 50MB)
- **Max Depth**: Maximum directory depth to scan (default: 3)

### Content Parsing Options

- **Document Parsing**: PDF, DOCX, TXT files
- **Spreadsheet Parsing**: XLSX, CSV files
- **Presentation Parsing**: PPTX files
- **Log Parsing**: Log file content extraction
- **Config Parsing**: Configuration file parsing

### Database Extraction Options

- **SQLite Extraction**: SQLite database content extraction
- **SQL Dump Parsing**: SQL dump file parsing
- **Enterprise DB Extraction**: SQL Server, Oracle, PostgreSQL extraction
- **Max DB Rows**: Maximum rows per table to extract (default: 1000)

## 🚀 Usage Examples

### 1. **Create Document Analysis Job**
```javascript
const jobConfig = {
  name: 'Document Analysis Job',
  description: 'Extract and parse document content for NLP analysis',
  extraction_level: 'content_parsing',
  file_type_filter: 'documents_only',
  backup_id: 'backup-123',
  directory_path: '/documents',
  max_depth: 3,
  chunk_size: 2000,
  enable_document_parsing: true,
  enable_spreadsheet_parsing: true,
  include_chunks: true,
  include_embeddings: true
}
```

### 2. **Create Database Forensics Job**
```javascript
const jobConfig = {
  name: 'Database Forensics Job',
  description: 'Extract database content for forensic analysis',
  extraction_level: 'database_extraction',
  file_type_filter: 'databases_only',
  backup_id: 'backup-456',
  enable_sqlite_extraction: true,
  enable_enterprise_db_extraction: true,
  max_db_rows_per_table: 5000
}
```

### 3. **Create Compliance Audit Job**
```javascript
const jobConfig = {
  name: 'Compliance Audit Job',
  description: 'Full pipeline extraction for compliance auditing',
  extraction_level: 'full_pipeline',
  file_type_filter: 'all_files',
  backup_id: 'backup-789',
  max_depth: 4,
  include_attributes: true,
  enable_document_parsing: true,
  enable_log_parsing: true,
  enable_config_parsing: true,
  include_raw_content: true,
  include_chunks: true
}
```

## 📊 Job Templates

### 1. **File System Census**
- **Purpose**: Extract metadata only for file system analysis
- **Extraction Level**: Metadata Only
- **File Filter**: All Files
- **Max Depth**: 5
- **Include Attributes**: Yes

### 2. **Document Analysis**
- **Purpose**: Extract and parse document content for NLP analysis
- **Extraction Level**: Content Parsing
- **File Filter**: Documents Only
- **Chunk Size**: 2000
- **Include Embeddings**: Yes

### 3. **Database Forensics**
- **Purpose**: Extract database content for forensic analysis
- **Extraction Level**: Database Extraction
- **File Filter**: Databases Only
- **Max DB Rows**: 5000

### 4. **Compliance Audit**
- **Purpose**: Full pipeline extraction for compliance auditing
- **Extraction Level**: Full Pipeline
- **File Filter**: All Files
- **Max File Size**: 100MB
- **Include All Content**: Yes

### 5. **Log Analysis**
- **Purpose**: Extract and parse log files for security analysis
- **Extraction Level**: Content Parsing
- **File Filter**: Logs Only
- **Chunk Size**: 1000

## 🔄 Job Execution Flow

1. **Job Creation**: User creates job through UI or API
2. **Configuration Validation**: System validates job configuration
3. **Job Queuing**: Job is queued for execution
4. **Mount Session**: Veeam FLR session is created for backup
5. **File Discovery**: Files are discovered based on job configuration
6. **Extraction Processing**: Files are processed according to extraction level
7. **Progress Tracking**: Real-time progress updates
8. **Result Storage**: Results are stored and indexed
9. **Job Completion**: Job status updated to completed

## 📈 Monitoring and Analytics

### Job Status Tracking
- **Pending**: Job created, waiting for execution
- **Running**: Job currently executing
- **Completed**: Job completed successfully
- **Failed**: Job failed with error
- **Cancelled**: Job cancelled by user

### Progress Metrics
- **Total Files**: Number of files to process
- **Processed Files**: Number of files processed
- **Failed Files**: Number of files that failed processing
- **Progress Percentage**: Overall completion percentage
- **Runtime**: Job execution time

### Active Job Monitoring
- Real-time job status updates
- Progress bar visualization
- Runtime tracking
- Error logging and reporting

## 🛠️ Technical Implementation

### Database Schema
```sql
-- Extraction Jobs Table
CREATE TABLE extraction_jobs (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    extraction_level ENUM('metadata_only', 'content_parsing', 'database_extraction', 'full_pipeline'),
    file_type_filter ENUM('all_files', 'documents_only', 'databases_only', 'logs_only', 'config_only', 'custom'),
    backup_id VARCHAR(255) NOT NULL,
    directory_path VARCHAR(500),
    max_depth INTEGER DEFAULT 3,
    max_file_size BIGINT DEFAULT 52428800,
    chunk_size INTEGER DEFAULT 2000,
    parallel_processing BOOLEAN DEFAULT TRUE,
    max_workers INTEGER DEFAULT 4,
    status ENUM('pending', 'running', 'completed', 'failed', 'cancelled'),
    progress_percentage FLOAT DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Job Templates Table
CREATE TABLE extraction_job_templates (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    configuration TEXT NOT NULL,
    is_public BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0
);
```

### API Endpoints
```
GET    /api/extraction/templates              # List job templates
POST   /api/extraction/templates             # Create new template
GET    /api/extraction/templates/{id}        # Get template details
GET    /api/extraction/jobs                   # List extraction jobs
POST   /api/extraction/jobs                  # Create new job
POST   /api/extraction/jobs/from-template    # Create job from template
GET    /api/extraction/jobs/{id}             # Get job details
POST   /api/extraction/jobs/{id}/execute     # Execute job
POST   /api/extraction/jobs/{id}/cancel      # Cancel job
GET    /api/extraction/active-jobs           # Get active jobs
GET    /api/extraction/config/levels         # Get extraction levels
GET    /api/extraction/config/file-filters   # Get file type filters
GET    /api/extraction/config/file-types     # Get supported file types
```

## 🎯 Benefits

### 1. **Flexibility**
- Configurable extraction levels for different use cases
- Flexible file type filtering
- Customizable processing options
- Template-based job creation

### 2. **Scalability**
- Parallel processing support
- Configurable worker count
- Efficient resource utilization
- Background job execution

### 3. **Usability**
- Intuitive UI for job creation
- Real-time progress tracking
- Template system for common scenarios
- Comprehensive configuration options

### 4. **Extensibility**
- Modular architecture
- Easy addition of new file types
- Pluggable extraction processors
- Custom template support

## 🚀 Getting Started

### 1. **Start the Application**
```bash
# Start backend
cd /Users/ian/Downloads/veeam_ml_integration
source venv/bin/activate
python src/main.py

# Start frontend (in another terminal)
cd veeam-ml-frontend
npm run dev
```

### 2. **Access the UI**
- Open browser to: http://localhost:5173
- Navigate to 'Extraction Jobs' in the sidebar
- Create and configure extraction jobs through the UI

### 3. **Create Your First Job**
- Click "Create Job" button
- Configure job settings in the form tabs
- Select extraction level and file filters
- Set processing options
- Execute the job and monitor progress

## 🔮 Future Enhancements

### 1. **Advanced ML Integration**
- Vector database indexing for semantic search
- RAG (Retrieval-Augmented Generation) support
- Automated content classification
- Anomaly detection in extracted data

### 2. **Enhanced Parsing**
- Apache Tika integration for universal document parsing
- OCR support for scanned documents
- Image and video metadata extraction
- Email and PST file parsing

### 3. **Workflow Automation**
- Scheduled job execution
- Job dependency management
- Automated result processing
- Integration with external ML pipelines

### 4. **Performance Optimization**
- Distributed processing support
- Caching mechanisms
- Incremental extraction
- Resource usage optimization

## 📝 Conclusion

The Configurable Multi-Level Data Extraction System provides a comprehensive, flexible, and user-friendly solution for extracting data from Veeam backups at different levels of detail. With its configurable extraction levels, flexible file type filtering, job templates, and real-time monitoring capabilities, it enables users to efficiently extract and process data for various ML and analytics use cases.

The system's modular architecture and extensive configuration options make it suitable for a wide range of scenarios, from simple file system census to complex compliance auditing workflows. The intuitive UI and template system ensure that users can quickly create and manage extraction jobs without requiring deep technical knowledge.

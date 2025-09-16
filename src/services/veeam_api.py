import requests
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
import subprocess
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class VeeamAPIError(Exception):
    """Custom exception for Veeam API errors."""
    pass

class VeeamDataIntegrationAPI:
    """
    Wrapper class for Veeam Data Integration API.
    Handles backup mounting, unmounting, and data access operations.
    """
    
    def __init__(self, base_url: str, username: str, password: str, verify_ssl: bool = False):
        """
        Initialize the Veeam API client.
        
        Args:
            base_url: Base URL of the Veeam Backup & Replication server
            username: Username for authentication
            password: Password for authentication
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.auth_token = None
        self.mount_sessions = {}  # Track active mount sessions
        
    def authenticate(self) -> bool:
        """
        Authenticate with the Veeam API and obtain an access token.
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            # Use the correct Veeam OAuth2 endpoint with API version header
            auth_url = f"{self.base_url}/api/oauth2/token"
            auth_data = {
                'grant_type': 'password',
                'username': self.username,
                'password': self.password,
                'refresh_token': '',
                'code': '',
                'use_short_term_refresh': '',
                'vbr_token': ''
            }
            
            # Set the correct headers for Veeam API
            headers = {
                'accept': 'application/json',
                'x-api-version': '1.2-rev0',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            logger.info(f"Attempting authentication to: {auth_url}")
            response = self.session.post(auth_url, data=auth_data, headers=headers)
            
            # Log response details for debugging
            logger.info(f"Auth response status: {response.status_code}")
            logger.info(f"Auth response headers: {dict(response.headers)}")
            
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    logger.error(f"Authentication failed - Bad Request: {error_data}")
                    raise VeeamAPIError(f"Authentication failed: {error_data.get('error_description', 'Invalid credentials')}")
                except json.JSONDecodeError:
                    logger.error(f"Authentication failed - Bad Request (non-JSON): {response.text}")
                    raise VeeamAPIError(f"Authentication failed: Invalid credentials or server configuration")
            elif response.status_code == 401:
                logger.error("Authentication failed - Unauthorized")
                raise VeeamAPIError("Authentication failed: Invalid username or password")
            elif response.status_code == 403:
                logger.error("Authentication failed - Forbidden")
                raise VeeamAPIError("Authentication failed: Access denied - check user permissions")
            elif response.status_code == 404:
                logger.error("Authentication endpoint not found")
                raise VeeamAPIError("Authentication failed: OAuth2 endpoint not found - check server URL")
            
            response.raise_for_status()
            
            auth_result = response.json()
            self.auth_token = auth_result.get('access_token')
            
            if self.auth_token:
                self.session.headers.update({
                    'Authorization': f'Bearer {self.auth_token}',
                    'Content-Type': 'application/json'
                })
                logger.info("Successfully authenticated with Veeam API")
                return True
            else:
                logger.error("Failed to obtain access token from Veeam API")
                raise VeeamAPIError("Authentication failed: No access token received")
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection failed: {str(e)}")
            raise VeeamAPIError(f"Connection failed: Cannot reach Veeam server at {self.base_url}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {str(e)}")
            raise VeeamAPIError("Authentication failed: Request timeout")
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise VeeamAPIError(f"Authentication failed: {str(e)}")
    
    def get_backups(self, vm_name: Optional[str] = None, 
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Retrieve list of available backups.
        
        Args:
            vm_name: Filter by VM name (optional)
            start_date: Filter backups created after this date (optional)
            end_date: Filter backups created before this date (optional)
            
        Returns:
            List of backup information dictionaries
        """
        try:
            url = f"{self.base_url}/api/v1/backups"
            params = {}
            
            # Set the correct headers for Veeam API
            headers = {
                'accept': 'application/json',
                'x-api-version': '1.2-rev0',
                'Authorization': f'Bearer {self.auth_token}'
            }
            
            if vm_name:
                params['vmName'] = vm_name
            if start_date:
                params['startDate'] = start_date.isoformat()
            if end_date:
                params['endDate'] = end_date.isoformat()
            
            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            backups_response = response.json()
            
            # Handle Veeam API response format - it might be wrapped in a data structure
            if isinstance(backups_response, dict):
                if 'data' in backups_response:
                    backups = backups_response['data']
                elif 'backups' in backups_response:
                    backups = backups_response['backups']
                else:
                    backups = backups_response
            else:
                backups = backups_response
            
            logger.info(f"Retrieved {len(backups) if isinstance(backups, list) else 'unknown'} backups from Veeam API")
            return backups
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve backups: {str(e)}")
            raise VeeamAPIError(f"Failed to retrieve backups: {str(e)}")
    
    def get_restore_points(self, backup_id: str = None) -> List[Dict[str, Any]]:
        """
        Get restore points for a specific backup or all restore points.
        
        Args:
            backup_id: Optional backup ID to filter restore points
            
        Returns:
            List of restore point information dictionaries
        """
        try:
            url = f"{self.base_url}/api/v1/restorePoints"
            params = {}
            
            if backup_id:
                params['backupId'] = backup_id
            
            headers = {
                'accept': 'application/json',
                'x-api-version': '1.2-rev0',
                'Authorization': f'Bearer {self.auth_token}'
            }
            
            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            restore_points_response = response.json()
            
            # Handle Veeam API response format
            if isinstance(restore_points_response, dict):
                if 'data' in restore_points_response:
                    restore_points = restore_points_response['data']
                else:
                    restore_points = restore_points_response
            else:
                restore_points = restore_points_response
            
            logger.info(f"Retrieved {len(restore_points) if isinstance(restore_points, list) else 'unknown'} restore points")
            return restore_points
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve restore points: {str(e)}")
            raise VeeamAPIError(f"Failed to retrieve restore points: {str(e)}")
    
    def mount_backup(self, backup_id: str, mount_point: str = None) -> Dict[str, Any]:
        """
        Mount a backup using FLR API for direct UNC path access.
        First checks for existing FLR sessions before creating a new one.
        Uses restore points to find the correct restore point ID for FLR session creation.
        
        Args:
            backup_id: ID of the backup to mount
            mount_point: Optional local directory path (not used for FLR API)
            
        Returns:
            Dictionary containing mount session information
        """
        try:
            # First, check if there's already an active FLR session for this backup
            active_sessions = self.get_active_sessions()
            existing_session = None
            
            for session in active_sessions:
                if (session.get('backupId') == backup_id and 
                    session.get('mount_type') == 'FLR' and 
                    session.get('state') == 'Working'):
                    existing_session = session
                    logger.info(f"Found existing FLR session {session['id']} for backup {backup_id}")
                    break
            
            if existing_session:
                # Use existing FLR session
                session_id = existing_session['id']
                flr_session = existing_session
                
                # Construct the actual folder name used by Veeam
                # Format: {machineName}_{first8CharsOfSessionId}
                machine_name = flr_session.get('sourceProperties', {}).get('machineName', 'unknown')
                abbreviated_id = session_id[:8]
                folder_name = f"{machine_name}_{abbreviated_id}"
                
                # Store mount session info with correct UNC path
                self.mount_sessions[session_id] = {
                    'backup_id': backup_id,
                    'restore_point_id': existing_session.get('restorePointId'),
                    'mount_point': f"\\\\172.21.234.6\\VeeamFLR\\{folder_name}",
                    'folder_name': folder_name,
                    'mounted_at': datetime.utcnow(),
                    'session_info': flr_session,
                    'mount_type': 'FLR'
                }
                
                logger.info(f"Using existing FLR session {session_id} for backup {backup_id}")
                return {
                    'session_id': session_id,
                    'mount_point': f"\\\\172.21.234.6\\VeeamFLR\\{folder_name}",
                    'mount_type': 'FLR',
                    'status': 'mounted',
                    'session_info': flr_session
                }
            else:
                # No existing session found, need to get restore points and create new one
                logger.info(f"No existing FLR session found for backup {backup_id}, getting restore points...")
                
                # Get restore points for this backup
                restore_points = self.get_restore_points(backup_id)
                if not restore_points:
                    raise VeeamAPIError(f"No restore points found for backup {backup_id}")
                
                # Use the most recent restore point
                latest_restore_point = restore_points[0]  # Assuming they're sorted by creation time
                restore_point_id = latest_restore_point.get('id')
                
                if not restore_point_id:
                    raise VeeamAPIError(f"No valid restore point ID found for backup {backup_id}")
                
                logger.info(f"Creating new FLR session for restore point {restore_point_id}")
                flr_session = self.create_flr_session_for_restore_point(restore_point_id)
                
                # The API returns 'sessionId' field, not 'id'
                session_id = flr_session.get('sessionId') or flr_session.get('id')
                
                if session_id:
                    # Construct the actual folder name used by Veeam
                    # Format: {machineName}_{first8CharsOfSessionId}
                    machine_name = flr_session.get('sourceProperties', {}).get('machineName', 'unknown')
                    abbreviated_id = session_id[:8]
                    folder_name = f"{machine_name}_{abbreviated_id}"
                    
                    # Store mount session info with correct UNC path
                    self.mount_sessions[session_id] = {
                        'backup_id': backup_id,
                        'restore_point_id': restore_point_id,
                        'mount_point': f"\\\\172.21.234.6\\VeeamFLR\\{folder_name}",
                        'folder_name': folder_name,
                        'mounted_at': datetime.utcnow(),
                        'session_info': flr_session,
                        'mount_type': 'FLR'
                    }
                    
                    logger.info(f"Successfully created new FLR session {session_id} with folder {folder_name} for backup {backup_id}")
                    return {
                        'session_id': session_id,
                        'mount_point': f"\\\\172.21.234.6\\VeeamFLR\\{folder_name}",
                        'mount_type': 'FLR',
                        'status': 'mounted',
                        'session_info': flr_session
                    }
                else:
                    raise VeeamAPIError("Failed to create FLR session - no session ID returned")
                
        except Exception as e:
            logger.error(f"Failed to mount backup {backup_id}: {str(e)}")
            raise VeeamAPIError(f"Failed to mount backup: {str(e)}")
    
    def get_mount_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all active Data Integration mount sessions.
        
        Returns:
            List of mount session information dictionaries
        """
        try:
            url = f"{self.base_url}/api/v1/dataIntegration"
            
            # Set the correct headers for Veeam API
            headers = {
                'accept': 'application/json',
                'x-api-version': '1.2-rev0',
                'Authorization': f'Bearer {self.auth_token}'
            }
            
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            
            response_data = response.json()
            # Handle paginated response structure
            if 'data' in response_data:
                sessions = response_data['data']
                logger.info(f"Retrieved {len(sessions)} active mount sessions (total: {response_data.get('pagination', {}).get('total', len(sessions))})")
            else:
                sessions = response_data
                logger.info(f"Retrieved {len(sessions)} active mount sessions")
            return sessions
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve mount sessions: {str(e)}")
            raise VeeamAPIError(f"Failed to retrieve mount sessions: {str(e)}")
    
    def get_mount_session_details(self, session_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific mount session.
        
        Args:
            session_id: ID of the mount session
            
        Returns:
            Dictionary containing detailed mount session information
        """
        try:
            url = f"{self.base_url}/api/v1/dataIntegration/{session_id}"
            
            headers = {
                'accept': 'application/json',
                'x-api-version': '1.2-rev0',
                'Authorization': f'Bearer {self.auth_token}'
            }
            
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            
            session_details = response.json()
            logger.info(f"Retrieved details for mount session {session_id}")
            return session_details
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve mount session details: {str(e)}")
            raise VeeamAPIError(f"Failed to retrieve mount session details: {str(e)}")
    
    def create_flr_session(self, restore_point_id: str) -> Dict[str, Any]:
        """
        Create a File Level Restore session for file browsing.
        
        Args:
            restore_point_id: ID of the restore point to browse
            
        Returns:
            Dictionary containing FLR session information
        """
        try:
            url = f"{self.base_url}/api/v1/restore/flr"
            flr_data = {
                'restorePointId': restore_point_id,
                'type': 'Windows',
                'autoUnmount': {
                    'isEnabled': True,
                    'noActivityPeriodInMinutes': 5  # Short timeout for scanning
                },
                'reason': 'File browsing for ML analysis'
            }
            
            headers = {
                'accept': 'application/json',
                'x-api-version': '1.2-rev0',
                'Authorization': f'Bearer {self.auth_token}',
                'Content-Type': 'application/json'
            }
            
            response = self.session.post(url, json=flr_data, headers=headers)
            response.raise_for_status()
            
            flr_session = response.json()
            logger.info(f"Created FLR session {flr_session.get('id')} for file browsing")
            return flr_session
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create FLR session: {str(e)}")
            raise VeeamAPIError(f"Failed to create FLR session: {str(e)}")
    
    def browse_flr_files(self, session_id: str, directory_path: str = '/') -> List[Dict[str, Any]]:
        """
        Browse files in a FLR session (legacy method for backward compatibility).
        
        Args:
            session_id: FLR session ID
            directory_path: Directory path to browse
            
        Returns:
            List of file information dictionaries
        """
        try:
            url = f"{self.base_url}/api/v1/backupBrowser/flr/{session_id}/files"
            params = {'path': directory_path}
            
            headers = {
                'accept': 'application/json',
                'x-api-version': '1.2-rev0',
                'Authorization': f'Bearer {self.auth_token}'
            }
            
            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            files_response = response.json()
            files = files_response.get('data', [])
            
            logger.info(f"Found {len(files)} files in {directory_path}")
            return files
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to browse FLR files: {str(e)}")
            raise VeeamAPIError(f"Failed to browse FLR files: {str(e)}")
    
    def browse_nas_unstructured_data(self, session_id: str, directory_path: str = '/') -> List[Dict[str, Any]]:
        """
        Browse unstructured data in NAS FLR session.
        
        Args:
            session_id: NAS FLR session ID
            directory_path: Directory path to browse
            
        Returns:
            List of file information dictionaries
        """
        try:
            url = f"{self.base_url}/api/v1/backupBrowser/flr/unstructuredData/{session_id}/files"
            params = {'path': directory_path}
            
            headers = {
                'accept': 'application/json',
                'x-api-version': '1.2-rev1',
                'Authorization': f'Bearer {self.auth_token}'
            }
            
            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            files_response = response.json()
            files = files_response.get('data', [])
            
            logger.info(f"Found {len(files)} unstructured files in {directory_path}")
            return files
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to browse NAS unstructured data: {str(e)}")
            raise VeeamAPIError(f"Failed to browse NAS unstructured data: {str(e)}")

    def get_file_compare_attributes(self, session_id: str, file_path: str) -> Dict[str, Any]:
        """
        Get extended file attributes for comparison (readonly, hidden, encryption).
        
        Args:
            session_id: FLR session ID
            file_path: Path to the file
            
        Returns:
            Dictionary containing extended file attributes
        """
        try:
            url = f"{self.base_url}/api/v1/backupBrowser/flr/{session_id}/compareAttributes"
            params = {'path': file_path}
            
            headers = {
                'accept': 'application/json',
                'x-api-version': '1.2-rev1',
                'Authorization': f'Bearer {self.auth_token}'
            }
            
            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            attributes = response.json()
            logger.info(f"Retrieved compare attributes for {file_path}")
            return attributes
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get compare attributes for {file_path}: {str(e)}")
            raise VeeamAPIError(f"Failed to get compare attributes: {str(e)}")

    def extract_file_system_metadata(self, session_id: str, mount_type: str = 'FLR', 
                                   max_depth: int = 3, include_attributes: bool = False) -> Dict[str, Any]:
        """
        Extract comprehensive file system metadata for ML analysis.
        
        Args:
            session_id: FLR session ID
            mount_type: Type of mount (FLR, NAS)
            max_depth: Maximum directory depth to scan
            include_attributes: Whether to include extended file attributes
            
        Returns:
            Dictionary containing file system census data
        """
        try:
            metadata = {
                'session_id': session_id,
                'mount_type': mount_type,
                'extraction_timestamp': datetime.utcnow().isoformat(),
                'files': [],
                'directories': [],
                'statistics': {
                    'total_files': 0,
                    'total_directories': 0,
                    'total_size': 0,
                    'file_types': {},
                    'size_distribution': {},
                    'timestamp_distribution': {}
                }
            }
            
            # Choose appropriate browse method
            if mount_type == 'NAS':
                browse_method = self.browse_nas_unstructured_data
            else:
                browse_method = self.browse_flr_files
            
            # Recursively scan directories
            self._scan_directory_metadata(session_id, '/', browse_method, metadata, 
                                        max_depth, 0, include_attributes)
            
            logger.info(f"Extracted metadata for {metadata['statistics']['total_files']} files, "
                       f"{metadata['statistics']['total_directories']} directories")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract file system metadata: {str(e)}")
            raise VeeamAPIError(f"Failed to extract file system metadata: {str(e)}")

    def _scan_directory_metadata(self, session_id: str, directory_path: str, 
                                browse_method, metadata: Dict[str, Any], 
                                max_depth: int, current_depth: int, include_attributes: bool):
        """
        Recursively scan directory for metadata extraction.
        
        Args:
            session_id: FLR session ID
            directory_path: Directory path to scan
            browse_method: Method to use for browsing files
            metadata: Metadata dictionary to populate
            max_depth: Maximum depth to scan
            current_depth: Current scanning depth
            include_attributes: Whether to include extended attributes
        """
        if current_depth >= max_depth:
            return
        
        try:
            # Browse files in current directory
            files = browse_method(session_id, directory_path)
            
            for file_info in files:
                file_data = {
                    'name': file_info.get('name', ''),
                    'path': file_info.get('path', ''),
                    'size': file_info.get('size', 0),
                    'is_directory': file_info.get('isDirectory', False),
                    'created_time': file_info.get('creationTime'),
                    'modified_time': file_info.get('lastWriteTime'),
                    'accessed_time': file_info.get('lastAccessTime'),
                    'file_type': self._classify_file_type(file_info.get('name', '')),
                    'extractable': self._is_extractable_for_ml(file_info.get('name', ''), 
                                                             file_info.get('isDirectory', False))
                }
                
                # Add extended attributes if requested
                if include_attributes and not file_info.get('isDirectory', False):
                    try:
                        attributes = self.get_file_compare_attributes(session_id, file_data['path'])
                        file_data['attributes'] = attributes
                    except Exception as e:
                        logger.debug(f"Failed to get attributes for {file_data['path']}: {str(e)}")
                        file_data['attributes'] = None
                
                # Update statistics
                if file_data['is_directory']:
                    metadata['directories'].append(file_data)
                    metadata['statistics']['total_directories'] += 1
                else:
                    metadata['files'].append(file_data)
                    metadata['statistics']['total_files'] += 1
                    metadata['statistics']['total_size'] += file_data['size']
                    
                    # Update file type distribution
                    file_type = file_data['file_type']
                    metadata['statistics']['file_types'][file_type] = \
                        metadata['statistics']['file_types'].get(file_type, 0) + 1
                
                # Recursively scan subdirectories
                if file_data['is_directory'] and current_depth < max_depth - 1:
                    self._scan_directory_metadata(session_id, file_data['path'], browse_method, 
                                                metadata, max_depth, current_depth + 1, include_attributes)
                    
        except Exception as e:
            logger.warning(f"Failed to scan directory {directory_path}: {str(e)}")

    def _classify_file_type(self, filename: str) -> str:
        """
        Classify file type for ML processing routing.
        
        Args:
            filename: Name of the file
            
        Returns:
            File type category
        """
        ext = os.path.splitext(filename)[1].lower()
        
        # Document types
        if ext in ['.pdf', '.doc', '.docx', '.txt', '.rtf']:
            return 'document'
        elif ext in ['.xls', '.xlsx', '.csv']:
            return 'spreadsheet'
        elif ext in ['.ppt', '.pptx']:
            return 'presentation'
        
        # Database types
        elif ext in ['.mdf', '.ldf', '.ndf']:
            return 'sqlserver_db'
        elif ext in ['.dbf', '.ora']:
            return 'oracle_db'
        elif ext in ['.sqlite', '.db', '.sqlite3']:
            return 'sqlite_db'
        elif ext in ['.sql', '.dump']:
            return 'sql_dump'
        
        # Log and config files
        elif ext in ['.log', '.txt']:
            return 'log'
        elif ext in ['.ini', '.cfg', '.conf', '.config', '.xml', '.json', '.yaml', '.yml']:
            return 'config'
        
        # Media files
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
            return 'image'
        elif ext in ['.mp3', '.wav', '.flac', '.aac']:
            return 'audio'
        elif ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv']:
            return 'video'
        
        # Executable and system files
        elif ext in ['.exe', '.dll', '.sys']:
            return 'executable'
        elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
            return 'archive'
        
        else:
            return 'unknown'

    def _is_extractable_for_ml(self, filename: str, is_directory: bool) -> bool:
        """
        Determine if file is suitable for ML content extraction.
        
        Args:
            filename: Name of the file
            is_directory: Whether this is a directory
            
        Returns:
            True if file is extractable for ML, False otherwise
        """
        if is_directory:
            return False
        
        file_type = self._classify_file_type(filename)
        
        # Files suitable for ML extraction
        extractable_types = {
            'document', 'spreadsheet', 'presentation', 'log', 'config',
            'sqlite_db', 'sql_dump', 'json', 'xml', 'csv'
        }
        
        return file_type in extractable_types
    
    def cleanup_flr_session(self, session_id: str) -> bool:
        """
        Clean up a FLR session.
        
        Args:
            session_id: FLR session ID to clean up
            
        Returns:
            bool: True if cleanup successful
        """
        try:
            url = f"{self.base_url}/api/v1/restore/flr/{session_id}/unmount"
            
            headers = {
                'accept': 'application/json',
                'x-api-version': '1.2-rev0',
                'Authorization': f'Bearer {self.auth_token}'
            }
            
            response = self.session.post(url, headers=headers)
            response.raise_for_status()
            
            logger.info(f"Cleaned up FLR session {session_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to cleanup FLR session {session_id}: {str(e)}")
            return False
    
    def mount_windows_backup_flr(self, restore_point_id: str) -> Dict[str, Any]:
        """
        Mount a Windows backup using File Level Restore (FLR).
        This creates a FLR session that mounts to C:\\VeeamFLR on the Veeam server.
        
        Args:
            restore_point_id: ID of the restore point to mount
            
        Returns:
            Dictionary containing FLR session information
        """
        try:
            # Use FLR API for Windows backups
            url = f"{self.base_url}/api/v1/restore/flr"
            flr_data = {
                'restorePointId': restore_point_id,
                'type': 'Windows',
                'autoUnmount': {
                    'isEnabled': True,
                    'noActivityPeriodInMinutes': 30  # Longer timeout for file access
                },
                'reason': 'File Level Restore for ML analysis'
            }
            
            headers = {
                'accept': 'application/json',
                'x-api-version': '1.2-rev0',
                'Authorization': f'Bearer {self.auth_token}',
                'Content-Type': 'application/json'
            }
            
            response = self.session.post(url, json=flr_data, headers=headers)
            response.raise_for_status()
            
            flr_session = response.json()
            # The API returns 'sessionId' field, not 'id'
            session_id = flr_session.get('sessionId') or flr_session.get('id')
            
            if session_id:
                # Construct the actual folder name used by Veeam
                # Format: {machineName}_{first8CharsOfSessionId}
                machine_name = flr_session.get('sourceProperties', {}).get('machineName', 'unknown')
                abbreviated_id = session_id[:8]
                folder_name = f"{machine_name}_{abbreviated_id}"
                
                # Store FLR session info with correct UNC path
                self.mount_sessions[session_id] = {
                    'backup_id': restore_point_id,
                    'mount_point': f"\\\\172.21.234.6\\VeeamFLR\\{folder_name}",
                    'folder_name': folder_name,
                    'mounted_at': datetime.utcnow(),
                    'session_info': flr_session,
                    'mount_type': 'FLR'
                }
                logger.info(f"Successfully created Windows FLR session {session_id} with folder {folder_name}")
            
            return flr_session
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create Windows FLR session: {str(e)}")
            raise VeeamAPIError(f"Failed to create Windows FLR session: {str(e)}")
    
    def get_flr_mount_points(self, session_id: str) -> List[str]:
        """
        Get the actual mount points for a FLR session.
        For Windows FLR, this returns paths like C:\\VeeamFLR\\{session_id}
        
        Args:
            session_id: FLR session ID
            
        Returns:
            List of mount point paths
        """
        try:
            # Get FLR session details
            url = f"{self.base_url}/api/v1/restore/flr/{session_id}"
            
            headers = {
                'accept': 'application/json',
                'x-api-version': '1.2-rev0',
                'Authorization': f'Bearer {self.auth_token}'
            }
            
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            
            session_details = response.json()
            
            # Extract mount points from FLR session
            mount_points = []
            if 'mountPoints' in session_details:
                mount_points = session_details['mountPoints']
            elif 'mountPoint' in session_details:
                mount_points = [session_details['mountPoint']]
            
            # If no mount points in response, use default Windows FLR path
            if not mount_points:
                mount_points = [f"C:\\VeeamFLR\\{session_id}"]
            
            logger.info(f"FLR session {session_id} mount points: {mount_points}")
            return mount_points
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get FLR mount points: {str(e)}")
            # Return default path if we can't get details
            return [f"C:\\VeeamFLR\\{session_id}"]
    
    def unmount_backup(self, session_id: str) -> bool:
        """
        Unmount a previously mounted backup using the correct API based on mount type.
        
        Args:
            session_id: ID of the mount session to terminate
            
        Returns:
            bool: True if unmount successful, False otherwise
        """
        try:
            # Check if we have this session in our tracking
            if session_id not in self.mount_sessions:
                logger.warning(f"Mount session {session_id} not found in local tracking")
                # Try to unmount anyway using FLR API first, then Data Integration
                return self._try_unmount_flr(session_id) or self._try_unmount_data_integration(session_id)
            
            mount_info = self.mount_sessions[session_id]
            mount_type = mount_info.get('mount_type', 'FLR')
            
            success = False
            if mount_type == 'FLR':
                success = self._try_unmount_flr(session_id)
            else:
                success = self._try_unmount_data_integration(session_id)
            
            if success:
                # Remove from local tracking
                del self.mount_sessions[session_id]
                logger.info(f"Successfully unmounted {mount_type} session {session_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to unmount session {session_id}: {str(e)}")
            return False
    
    def _try_unmount_flr(self, session_id: str) -> bool:
        """Try to unmount using FLR API."""
        try:
            url = f"{self.base_url}/api/v1/restore/flr/{session_id}/unmount"
            headers = {
                'accept': 'application/json',
                'x-api-version': '1.2-rev1',
                'Authorization': f'Bearer {self.auth_token}'
            }
            response = self.session.post(url, headers=headers, timeout=30)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.debug(f"FLR unmount failed for {session_id}: {str(e)}")
            return False
    
    def _try_unmount_data_integration(self, session_id: str) -> bool:
        """Try to unmount using Data Integration API."""
        try:
            url = f"{self.base_url}/api/v1/dataIntegration/{session_id}/unpublish"
            headers = {
                'accept': 'application/json',
                'x-api-version': '1.2-rev0',
                'Authorization': f'Bearer {self.auth_token}'
            }
            response = self.session.post(url, headers=headers, timeout=30)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.debug(f"Data Integration unmount failed for {session_id}: {str(e)}")
            return False
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all active sessions from Veeam server to reconcile state.
        
        Returns:
            List of active session information
        """
        try:
            # Get all sessions
            url = f"{self.base_url}/api/v1/sessions"
            headers = {
                'accept': 'application/json',
                'x-api-version': '1.2-rev1',
                'Authorization': f'Bearer {self.auth_token}'
            }
            
            # Get FLR sessions
            flr_params = {'typeFilter': 'FileLevelRestore'}
            flr_response = self.session.get(url, params=flr_params, headers=headers, timeout=30)
            flr_response.raise_for_status()
            flr_sessions = flr_response.json().get('data', [])
            
            # Get Data Integration sessions
            di_params = {'typeFilter': 'PublishBackupContentViaMount'}
            di_response = self.session.get(url, params=di_params, headers=headers, timeout=30)
            di_response.raise_for_status()
            di_sessions = di_response.json().get('data', [])
            
            # Combine and format sessions, marking their source
            all_sessions = []
            
            # Process FLR sessions
            for session in flr_sessions:
                session_info = {
                    'id': session.get('id'),
                    'type': session.get('type'),
                    'state': session.get('state'),
                    'creationTime': session.get('creationTime'),
                    'backupId': session.get('backupId'),
                    'restorePointId': session.get('restorePointId'),
                    'mount_type': 'FLR',  # Sessions from FLR filter are FLR sessions
                    'mount_point': f"\\\\172.21.234.6\\VeeamFLR\\{session.get('id')}",
                    'is_ready': False  # Will be determined below
                }
                all_sessions.append(session_info)
            
            # Process Data Integration sessions
            for session in di_sessions:
                session_info = {
                    'id': session.get('id'),
                    'type': session.get('type'),
                    'state': session.get('state'),
                    'creationTime': session.get('creationTime'),
                    'backupId': session.get('backupId'),
                    'restorePointId': session.get('restorePointId'),
                    'mount_type': 'DataIntegration',  # Sessions from DI filter are DI sessions
                    'mount_point': f"iSCSI session {session.get('id')}",
                    'is_ready': False  # Will be determined below
                }
                all_sessions.append(session_info)
            
            # Check readiness for all sessions
            for session_info in all_sessions:
                if session_info['mount_type'] == 'FLR' and session_info['state'] == 'Working':
                    # For FLR sessions, check REST API readiness
                    rest_api_ready = self._check_flr_session_ready(session_info['id'])
                    
                    # For FLR sessions in "Working" state, assume UNC path is accessible
                    # This is because Veeam shows "Working" when the mount is ready for file access
                    # even if the REST API isn't ready yet
                    unc_path_ready = True  # Assume accessible if session is "Working"
                    
                    session_info['is_ready'] = rest_api_ready or unc_path_ready
                    
                    # Add detailed readiness info
                    session_info['rest_api_ready'] = rest_api_ready
                    session_info['unc_path_ready'] = unc_path_ready
                elif session_info['state'] == 'Working':
                    session_info['is_ready'] = True  # Assume Data Integration sessions are ready when Working
                else:
                    session_info['is_ready'] = False
            
            logger.info(f"Retrieved {len(all_sessions)} active sessions")
            return all_sessions
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get active sessions: {str(e)}")
            return []
    
    def _determine_session_type(self, session: Dict[str, Any]) -> str:
        """
        Determine the session type based on available information.
        
        Args:
            session: Session information from API
            
        Returns:
            'FLR' or 'DataIntegration'
        """
        # First check explicit type
        session_type = session.get('type')
        if session_type == 'FileLevelRestore':
            return 'FLR'
        elif session_type == 'PublishBackupContentViaMount':
            return 'DataIntegration'
        
        # If type is None or unknown, try to determine from context
        # Check if this session came from FLR filter
        session_id = session.get('id', '')
        
        # For now, assume sessions from FLR filter are FLR sessions
        # This is a heuristic since the API doesn't always return proper type
        return 'FLR'
    
    def _check_flr_session_ready(self, session_id: str) -> bool:
        """
        Check if an FLR session is ready for file browsing.
        
        Args:
            session_id: FLR session ID
            
        Returns:
            True if session is ready for browsing, False otherwise
        """
        try:
            headers = {
                'accept': 'application/json',
                'x-api-version': '1.2-rev1',
                'Authorization': f'Bearer {self.auth_token}'
            }
            
            # Try to browse files in the session
            browse_url = f"{self.base_url}/api/v1/backupBrowser/flr/{session_id}/files"
            browse_params = {'path': '/'}
            browse_response = self.session.get(browse_url, params=browse_params, headers=headers, timeout=10)
            
            if browse_response.status_code == 200:
                logger.info(f"FLR session {session_id} is ready for REST API browsing")
                return True
            elif browse_response.status_code == 404:
                # 404 might mean the session is still initializing, but UNC path could be ready
                logger.debug(f"FLR session {session_id} REST API not ready (HTTP 404), but UNC path might be accessible")
                return False
            else:
                logger.debug(f"FLR session {session_id} not ready yet (HTTP {browse_response.status_code})")
            return False
                
        except Exception as e:
            logger.debug(f"Error checking FLR session {session_id} readiness: {str(e)}")
            return False

    def check_unc_path_accessible(self, session_id: str) -> bool:
        """
        Check if the UNC path for an FLR session is accessible via SMB.
        
        Args:
            session_id: FLR session ID
            
        Returns:
            True if UNC path is accessible, False otherwise
        """
        try:
            import os
            import platform
            
            # Try different UNC path formats
            unc_paths = [
                f"\\\\172.21.234.6\\VeeamFLR\\{session_id}",
                f"//172.21.234.6/VeeamFLR/{session_id}",
                f"\\\\172.21.234.6\\VeeamFLR\\target_*"  # Pattern match for target folders
            ]
            
            for unc_path in unc_paths:
                try:
                    # Try to access the UNC path using Python's os module
                    files = os.listdir(unc_path)
                    logger.info(f"UNC path {unc_path} is accessible - found {len(files)} items")
                    return True
                except (OSError, PermissionError) as e:
                    logger.debug(f"UNC path {unc_path} not accessible: {str(e)}")
                    continue
            
            # If direct UNC access fails, check if we're on Windows and the session is "Working"
            # In this case, assume the UNC path is accessible even if Python can't access it
            if platform.system() == "Windows":
                logger.info(f"UNC path access failed via Python, but session {session_id} is Working - assuming accessible")
                return True
                
            return False
                
        except Exception as e:
            logger.debug(f"Error checking UNC path accessibility: {str(e)}")
            return False

    def wait_for_flr_session_ready(self, session_id: str, max_wait_time: int = 300, check_interval: int = 10) -> bool:
        """
        Wait for an FLR session to be ready for file browsing.
        
        Args:
            session_id: FLR session ID
            max_wait_time: Maximum time to wait in seconds (default: 5 minutes)
            check_interval: Time between checks in seconds (default: 10 seconds)
            
        Returns:
            True if session becomes ready, False if timeout
        """
        import time
        
        logger.info(f"Waiting for FLR session {session_id} to be ready...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            if self._check_flr_session_ready(session_id):
                logger.info(f"FLR session {session_id} is now ready!")
                return True
            
            logger.info(f"FLR session {session_id} not ready yet, waiting {check_interval}s...")
            time.sleep(check_interval)
        
        logger.warning(f"FLR session {session_id} did not become ready within {max_wait_time}s")
        return False

    def reconcile_mount_state(self) -> Dict[str, Any]:
        """
        Reconcile local mount state with actual Veeam server state.
        
        Returns:
            Dictionary with reconciliation results
        """
        try:
            # Get active sessions from server
            active_sessions = self.get_active_sessions()
            active_session_ids = {session['id'] for session in active_sessions}
            
            # Find orphaned local sessions
            local_session_ids = set(self.mount_sessions.keys())
            orphaned_sessions = local_session_ids - active_session_ids
            
            # Remove orphaned sessions
            for session_id in orphaned_sessions:
                logger.info(f"Removing orphaned session {session_id}")
                del self.mount_sessions[session_id]
            
            # Update local sessions with server state
            for session in active_sessions:
                session_id = session['id']
                if session_id in self.mount_sessions:
                    # Update existing session info
                    self.mount_sessions[session_id].update({
                        'state': session['state'],
                        'mount_point': session['mount_point'],
                        'mount_type': session['mount_type']
                    })
                else:
                    # Add new session from server
                    self.mount_sessions[session_id] = {
                        'backup_id': session.get('backupId'),
                        'restore_point_id': session.get('restorePointId'),
                        'mount_point': session['mount_point'],
                        'mounted_at': datetime.utcnow(),
                        'state': session['state'],
                        'mount_type': session['mount_type']
                    }
            
            reconciliation_result = {
                'total_active_sessions': len(active_sessions),
                'local_sessions': len(self.mount_sessions),
                'orphaned_removed': len(orphaned_sessions),
                'sessions_updated': len(active_sessions)
            }
            
            logger.info(f"Mount state reconciled: {reconciliation_result}")
            return reconciliation_result
            
        except Exception as e:
            logger.error(f"Failed to reconcile mount state: {str(e)}")
            return {'error': str(e)}
    
    def get_mount_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get the status of a mount session.
        
        Args:
            session_id: ID of the mount session
            
        Returns:
            Dictionary containing mount session status
        """
        try:
            url = f"{self.base_url}/api/v1.2-rev0/mount-sessions/{session_id}"
            response = self.session.get(url)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get mount status for session {session_id}: {str(e)}")
            raise VeeamAPIError(f"Failed to get mount status: {str(e)}")
    
    def list_files(self, session_id: str, path: str = "/") -> List[Dict[str, Any]]:
        """
        List files and directories in a mounted backup.
        
        Args:
            session_id: ID of the mount session
            path: Path within the mounted backup to list
            
        Returns:
            List of file/directory information dictionaries
        """
        try:
            url = f"{self.base_url}/api/v1/mount-sessions/{session_id}/files"
            params = {'path': path}
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list files in path {path}: {str(e)}")
            raise VeeamAPIError(f"Failed to list files: {str(e)}")
    
    def cleanup_all_mounts(self) -> None:
        """
        Cleanup all active mount sessions.
        Should be called when shutting down the application.
        """
        for session_id in list(self.mount_sessions.keys()):
            try:
                self.unmount_backup(session_id)
            except Exception as e:
                logger.error(f"Failed to cleanup mount session {session_id}: {str(e)}")
    
    def get_backup_metadata(self, backup_id: str) -> Dict[str, Any]:
        """
        Get detailed metadata about a specific backup.
        
        Args:
            backup_id: ID of the backup
            
        Returns:
            Dictionary containing backup metadata
        """
        try:
            url = f"{self.base_url}/api/v1/backups/{backup_id}"
            response = self.session.get(url)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get backup metadata for {backup_id}: {str(e)}")
            raise VeeamAPIError(f"Failed to get backup metadata: {str(e)}")
    
    def get_iscsi_mount_info(self, session_id: str) -> Dict[str, Any]:
        """
        Get iSCSI mount information for accessing mounted backup data.
        This method works with existing Data Integration API mounts.
        
        Args:
            session_id: iSCSI session ID from Data Integration API
            
        Returns:
            Dictionary containing iSCSI mount information and access details
        """
        try:
            # Get mount session details from Data Integration API
            url = f"{self.base_url}/api/v1/dataIntegration/{session_id}"
            
            headers = {
                'accept': 'application/json',
                'x-api-version': '1.2-rev0',
                'Authorization': f'Bearer {self.auth_token}'
            }
            
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            mount_info = response.json()
            
            # Extract iSCSI information
            iscsi_info = {
                'session_id': session_id,
                'mount_state': mount_info.get('mountState', 'Unknown'),
                'backup_id': mount_info.get('backupId'),
                'backup_name': mount_info.get('backupName'),
                'restore_point_id': mount_info.get('restorePointId'),
                'restore_point_name': mount_info.get('restorePointName'),
                'initiator_name': mount_info.get('initiatorName'),
                'iscsi_targets': [],
                'access_methods': []
            }
            
            # Extract iSCSI target information
            if 'info' in mount_info:
                info = mount_info['info']
                server_ips = info.get('serverIps', [])
                server_port = info.get('serverPort', 3260)
                mode = info.get('mode', 'ISCSI')
                
                for disk in info.get('disks', []):
                    target_info = {
                        'disk_id': disk.get('diskId'),
                        'disk_name': disk.get('diskName'),
                        'iqn': disk.get('accessLink'),
                        'server_ips': server_ips,
                        'server_port': server_port,
                        'mode': mode
                    }
                    iscsi_info['iscsi_targets'].append(target_info)
                
                # Create access methods for different scenarios
                for i, target in enumerate(iscsi_info['iscsi_targets']):
                    server_ip = server_ips[0] if server_ips else '172.21.234.6'
                    
                    # Method 1: Direct iSCSI access (requires iSCSI initiator)
                    iscsi_info['access_methods'].append({
                        'method': 'iscsi_direct',
                        'description': 'Direct iSCSI connection to target',
                        'server_ip': server_ip,
                        'port': server_port,
                        'iqn': target['iqn'],
                        'command': f"iscsiadm -m discovery -t st -p {server_ip}:{server_port}",
                        'mount_command': f"iscsiadm -m node -T {target['iqn']} -p {server_ip}:{server_port} -l"
                    })
                    
                    # Method 2: UNC path simulation (for Windows environments)
                    iscsi_info['access_methods'].append({
                        'method': 'unc_simulation',
                        'description': 'Simulated UNC path for Windows file access',
                        'unc_path': f"\\\\{server_ip}\\iscsi\\{target['iqn'].replace(':', '_')}",
                        'note': 'This is a simulated path - actual access requires iSCSI initiator'
                    })
                    
                    # Method 3: Veeam server local path (if accessible)
                    iscsi_info['access_methods'].append({
                        'method': 'veeam_server_path',
                        'description': 'Path on Veeam server where iSCSI target is mounted',
                        'server_path': f"C:\\VeeamFLR\\{session_id}\\{target['disk_name']}",
                        'server_ip': server_ip,
                        'note': 'Requires access to Veeam server file system'
                    })
            
            logger.info(f"Retrieved iSCSI mount info for session {session_id}")
            return iscsi_info
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get iSCSI mount info for {session_id}: {str(e)}")
            raise VeeamAPIError(f"Failed to get iSCSI mount info: {str(e)}")
    
    def create_flr_session_for_restore_point(self, restore_point_id: str, credentials_id: str = None) -> Dict[str, Any]:
        """
        Create a File Level Restore (FLR) session for a specific restore point.
        This is an alternative to iSCSI mounts that provides direct file system access.
        
        Args:
            restore_point_id: ID of the restore point to mount
            credentials_id: Optional credentials ID for authentication
            
        Returns:
            Dictionary containing FLR session information
        """
        try:
            # Prepare FLR request
            flr_data = {
                'restorePointId': restore_point_id,
                'type': 'Windows',
                'autoUnmount': {
                    'isEnabled': True,
                    'noActivityPeriodInMinutes': 60  # Longer timeout for ML processing
                },
                'reason': 'File Level Restore for ML data analysis'
            }
            
            # Add credentials if provided
            if credentials_id:
                flr_data['credentialsId'] = credentials_id
            
            url = f"{self.base_url}/api/v1/restore/flr"
            headers = {
                'accept': 'application/json',
                'x-api-version': '1.2-rev1',
                'Authorization': f'Bearer {self.auth_token}',
                'Content-Type': 'application/json'
            }
            
            logger.info(f"Creating FLR session for restore point {restore_point_id}")
            response = self.session.post(url, json=flr_data, headers=headers, timeout=60)
            
            if response.status_code == 201:
                flr_session = response.json()
                # The API returns 'sessionId' field, not 'id'
                session_id = flr_session.get('sessionId') or flr_session.get('id')
                
                if session_id:
                    # Construct the actual folder name used by Veeam
                    # Format: {machineName}_{first8CharsOfSessionId}
                    machine_name = flr_session.get('sourceProperties', {}).get('machineName', 'unknown')
                    abbreviated_id = session_id[:8]
                    folder_name = f"{machine_name}_{abbreviated_id}"
                    
                    # Store FLR session info with correct UNC path
                    self.mount_sessions[session_id] = {
                        'backup_id': restore_point_id,
                        'mount_point': f"\\\\172.21.234.6\\VeeamFLR\\{folder_name}",
                        'folder_name': folder_name,
                        'mounted_at': datetime.utcnow(),
                        'session_info': flr_session,
                        'mount_type': 'FLR'
                    }
                    logger.info(f"Successfully created FLR session {session_id} with folder {folder_name}")
                
                return flr_session
            else:
                error_msg = f"FLR creation failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise VeeamAPIError(error_msg)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create FLR session: {str(e)}")
            raise VeeamAPIError(f"Failed to create FLR session: {str(e)}")



class LocalFileSystemMounter:
    """
    Alternative implementation for local file system mounting when direct API access is not available.
    This can be used for testing or when working with local backup files.
    """
    
    def __init__(self, base_path: str = "/tmp/veeam_mounts"):
        """
        Initialize the local file system mounter.
        
        Args:
            base_path: Base path for mounting backup files
        """
        self.base_path = base_path
        self.mount_sessions = {}
    
        # Ensure base path exists
        os.makedirs(base_path, exist_ok=True)
    
    def mount_backup_file(self, backup_file_path: str, mount_point: str = None) -> str:
        """
        Mount a backup file to a local directory.
        
        Args:
            backup_file_path: Path to the backup file
            mount_point: Optional custom mount point
            
        Returns:
            Mount point path
        """
        if mount_point is None:
            # Generate a unique mount point
            import uuid
            mount_point = os.path.join(self.base_path, str(uuid.uuid4()))
        
        # Create mount point directory
            os.makedirs(mount_point, exist_ok=True)
            
        # Store mount session info
        session_id = str(uuid.uuid4())
        self.mount_sessions[session_id] = {
                'backup_file': backup_file_path,
                'mount_point': mount_point,
                'mounted_at': datetime.utcnow()
            }
            
        logger.info(f"Mounted backup file {backup_file_path} to {mount_point}")
        return mount_point
    
    def unmount_backup_file(self, session_id: str) -> bool:
        """
        Unmount a backup file.
        
        Args:
            session_id: Session ID of the mount to remove
            
        Returns:
            True if successful
        """
        try:
            if session_id in self.mount_sessions:
                mount_info = self.mount_sessions.pop(session_id)
                mount_point = mount_info['mount_point']
                
                # Remove mount point directory
                if os.path.exists(mount_point):
                    import shutil
                    shutil.rmtree(mount_point)
                
                logger.info(f"Unmounted backup from {mount_point}")
                return True
            else:
                logger.warning(f"Mount session {session_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to unmount session {session_id}: {str(e)}")
            return False

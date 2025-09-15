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
    
    def mount_backup(self, backup_id: str, mount_point: str = None) -> Dict[str, Any]:
        """
        Mount a backup using Veeam Data Integration API (Disk Publishing).
        
        Args:
            backup_id: ID of the backup to mount (this is actually a restore point ID)
            mount_point: Optional local directory path (not used for Data Integration API)
            
        Returns:
            Dictionary containing mount session information
        """
        try:
            # The backup_id we receive is actually a restore point ID from our database
            restore_point_id = backup_id
            
            # Use Veeam Data Integration API for disk publishing
            url = f"{self.base_url}/api/v1/dataIntegration/publish"
            mount_data = {
                'restorePointId': restore_point_id,
                'type': 'ISCSITarget',  # Use iSCSI target (simpler, no credentials needed)
                'allowedIps': ['127.0.0.1']  # Allow localhost access
            }
            
            # Set the correct headers for Veeam API
            headers = {
                'accept': 'application/json',
                'x-api-version': '1.2-rev0',
                'Authorization': f'Bearer {self.auth_token}',
                'Content-Type': 'application/json'
            }
            
            response = self.session.post(url, json=mount_data, headers=headers)
            response.raise_for_status()
            
            mount_session = response.json()
            session_id = mount_session.get('id')  # Data Integration API uses 'id' not 'sessionId'
            
            if session_id:
                self.mount_sessions[session_id] = {
                    'backup_id': backup_id,
                    'mount_point': mount_point,
                    'mounted_at': datetime.utcnow(),
                    'session_info': mount_session
                }
                logger.info(f"Successfully mounted backup {backup_id} with session {session_id}")
            
            return mount_session
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to mount backup {backup_id}: {str(e)}")
            raise VeeamAPIError(f"Failed to mount backup {backup_id}: {str(e)}")
    
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
        Browse files in a FLR session.
        
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
            session_id = flr_session.get('id')
            
            if session_id:
                # Store FLR session info
                self.mount_sessions[session_id] = {
                    'backup_id': restore_point_id,
                    'mount_point': f"C:\\VeeamFLR\\{restore_point_id}",  # Default Windows FLR path
                    'mounted_at': datetime.utcnow(),
                    'session_info': flr_session,
                    'mount_type': 'FLR'
                }
                logger.info(f"Successfully created Windows FLR session {session_id}")
            
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
        Unmount a previously mounted backup.
        
        Args:
            session_id: ID of the mount session to terminate
            
        Returns:
            bool: True if unmount successful, False otherwise
        """
        try:
            # Use Veeam Data Integration API unpublish endpoint
            url = f"{self.base_url}/api/v1/dataIntegration/{session_id}/unpublish"
            
            # Set the correct headers for Veeam API
            headers = {
                'accept': 'application/json',
                'x-api-version': '1.2-rev0',
                'Authorization': f'Bearer {self.auth_token}'
            }
            
            response = self.session.post(url, headers=headers)
            response.raise_for_status()
            
            if session_id in self.mount_sessions:
                mount_info = self.mount_sessions.pop(session_id)
                logger.info(f"Successfully unmounted backup from {mount_info['mount_point']}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to unmount session {session_id}: {str(e)}")
            return False
    
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

class LocalFileSystemMounter:
    """
    Alternative implementation for local file system mounting when direct API access is not available.
    This can be used for testing or when working with local backup files.
    """
    
    def __init__(self):
        self.mount_sessions = {}
    
    def mount_backup_file(self, backup_file_path: str, mount_point: str) -> str:
        """
        Mount a local backup file using system tools.
        
        Args:
            backup_file_path: Path to the backup file
            mount_point: Directory where to mount the backup
            
        Returns:
            Session ID for the mount
        """
        try:
            os.makedirs(mount_point, exist_ok=True)
            
            # Generate a session ID
            session_id = f"local_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            # For demonstration, we'll simulate mounting by copying/linking
            # In a real implementation, this would use appropriate mounting tools
            # based on the backup file format (e.g., loop mount for disk images)
            
            self.mount_sessions[session_id] = {
                'backup_file': backup_file_path,
                'mount_point': mount_point,
                'mounted_at': datetime.utcnow()
            }
            
            logger.info(f"Simulated mount of {backup_file_path} at {mount_point}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to mount backup file: {str(e)}")
            raise VeeamAPIError(f"Failed to mount backup file: {str(e)}")
    
    def unmount_backup_file(self, session_id: str) -> bool:
        """
        Unmount a locally mounted backup file.
        
        Args:
            session_id: Session ID of the mount to remove
            
        Returns:
            bool: True if successful
        """
        try:
            if session_id in self.mount_sessions:
                mount_info = self.mount_sessions.pop(session_id)
                logger.info(f"Unmounted backup from {mount_info['mount_point']}")
                return True
            else:
                logger.warning(f"Mount session {session_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to unmount session {session_id}: {str(e)}")
            return False


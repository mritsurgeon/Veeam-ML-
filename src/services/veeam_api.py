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
            auth_url = f"{self.base_url}/api/oauth2/token"
            auth_data = {
                'grant_type': 'password',
                'username': self.username,
                'password': self.password
            }
            
            response = self.session.post(auth_url, data=auth_data)
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
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False
    
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
            
            if vm_name:
                params['vmName'] = vm_name
            if start_date:
                params['startDate'] = start_date.isoformat()
            if end_date:
                params['endDate'] = end_date.isoformat()
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            backups = response.json()
            logger.info(f"Retrieved {len(backups)} backups from Veeam API")
            return backups
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve backups: {str(e)}")
            raise VeeamAPIError(f"Failed to retrieve backups: {str(e)}")
    
    def mount_backup(self, backup_id: str, mount_point: str) -> Dict[str, Any]:
        """
        Mount a backup as a file system.
        
        Args:
            backup_id: ID of the backup to mount
            mount_point: Local directory path where backup will be mounted
            
        Returns:
            Dictionary containing mount session information
        """
        try:
            # Ensure mount point directory exists
            os.makedirs(mount_point, exist_ok=True)
            
            url = f"{self.base_url}/api/v1/backups/{backup_id}/mount"
            mount_data = {
                'mountPoint': mount_point,
                'readOnly': True  # Mount as read-only for safety
            }
            
            response = self.session.post(url, json=mount_data)
            response.raise_for_status()
            
            mount_session = response.json()
            session_id = mount_session.get('sessionId')
            
            if session_id:
                self.mount_sessions[session_id] = {
                    'backup_id': backup_id,
                    'mount_point': mount_point,
                    'mounted_at': datetime.utcnow(),
                    'session_info': mount_session
                }
                logger.info(f"Successfully mounted backup {backup_id} at {mount_point}")
            
            return mount_session
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to mount backup {backup_id}: {str(e)}")
            raise VeeamAPIError(f"Failed to mount backup {backup_id}: {str(e)}")
    
    def unmount_backup(self, session_id: str) -> bool:
        """
        Unmount a previously mounted backup.
        
        Args:
            session_id: ID of the mount session to terminate
            
        Returns:
            bool: True if unmount successful, False otherwise
        """
        try:
            url = f"{self.base_url}/api/v1/mount-sessions/{session_id}"
            response = self.session.delete(url)
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
            url = f"{self.base_url}/api/v1/mount-sessions/{session_id}"
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


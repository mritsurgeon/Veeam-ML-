"""
UNC File Scanner Service

This service handles file enumeration from Windows UNC paths (\\\\server\\share\\path)
using SMB protocol to access files on remote Windows shares.
"""

import os
import logging
from typing import List, Dict, Optional, Tuple
from smb.SMBConnection import SMBConnection
from smb.smb_structs import OperationFailure

logger = logging.getLogger(__name__)


class UNCFileScanner:
    """Service for scanning files from UNC paths using SMB protocol"""
    
    def __init__(self, username: str = "Administrator", password: str = "Veeam123"):
        """
        Initialize UNC file scanner
        
        Args:
            username: Username for SMB authentication
            password: Password for SMB authentication
        """
        self.username = username
        self.password = password
        self.conn = None
    
    def parse_unc_path(self, unc_path: str) -> Tuple[str, str, str]:
        """
        Parse UNC path into server, share, and path components
        
        Args:
            unc_path: UNC path like \\\\172.21.234.6\\C$\\VeeamFLR\\session_id
            
        Returns:
            Tuple of (server, share, path)
        """
        # Remove leading \\ and split
        path_parts = unc_path[2:].split('\\', 2)
        server = path_parts[0]
        share = path_parts[1] if len(path_parts) > 1 else ""
        path = path_parts[2] if len(path_parts) > 2 else ""
        
        return server, share, path
    
    def connect_to_server(self, server: str) -> bool:
        """
        Connect to SMB server
        
        Args:
            server: Server IP or hostname
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.conn = SMBConnection(
                self.username, 
                self.password, 
                "veeam-ml-client", 
                server, 
                use_ntlm_v2=True
            )
            connected = self.conn.connect(server, 445)
            if connected:
                logger.info(f"Successfully connected to SMB server {server}")
                return True
            else:
                logger.error(f"Failed to connect to SMB server {server}")
                return False
        except Exception as e:
            logger.error(f"SMB connection error to {server}: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from SMB server"""
        if self.conn:
            try:
                self.conn.close()
                logger.info("Disconnected from SMB server")
            except Exception as e:
                logger.error(f"Error disconnecting from SMB server: {str(e)}")
            finally:
                self.conn = None
    
    def list_files(self, unc_path: str, max_depth: int = 3) -> List[Dict]:
        """
        List files from UNC path
        
        Args:
            unc_path: UNC path to scan
            max_depth: Maximum directory depth to scan
            
        Returns:
            List of file dictionaries with metadata
        """
        try:
            server, share, path = self.parse_unc_path(unc_path)
            
            # Connect to server if not already connected
            if not self.conn or not self.connect_to_server(server):
                logger.error(f"Failed to connect to server {server}")
                return []
            
            files = []
            self._scan_directory(share, path, files, max_depth, 0)
            
            return files
            
        except Exception as e:
            logger.error(f"Error scanning UNC path {unc_path}: {str(e)}")
            return []
    
    def _scan_directory(self, share: str, path: str, files: List[Dict], 
                        max_depth: int, current_depth: int):
        """
        Recursively scan directory for files
        
        Args:
            share: SMB share name
            path: Directory path within share
            files: List to append found files
            max_depth: Maximum depth to scan
            current_depth: Current scanning depth
        """
        if current_depth >= max_depth:
            return
        
        try:
            # List files and directories in current path
            file_list = self.conn.listPath(share, path)
            
            for file_info in file_list:
                # Skip . and .. entries
                if file_info.filename in ['.', '..']:
                    continue
                
                file_path = f"{path}\\{file_info.filename}" if path else file_info.filename
                
                file_data = {
                    'name': file_info.filename,
                    'path': file_path,
                    'size': file_info.file_size,
                    'is_directory': file_info.isDirectory,
                    'created_time': str(file_info.create_time) if hasattr(file_info, 'create_time') else None,
                    'modified_time': str(file_info.last_write_time) if hasattr(file_info, 'last_write_time') else None,
                    'file_type': self._get_file_type(file_info.filename),
                    'extractable': self._is_extractable(file_info.filename, file_info.isDirectory)
                }
                
                files.append(file_data)
                
                # Recursively scan subdirectories
                if file_info.isDirectory and current_depth < max_depth - 1:
                    self._scan_directory(share, file_path, files, max_depth, current_depth + 1)
                    
        except OperationFailure as e:
            logger.warning(f"Cannot access directory {path} on share {share}: {str(e)}")
        except Exception as e:
            logger.error(f"Error scanning directory {path}: {str(e)}")
    
    def _get_file_type(self, filename: str) -> str:
        """
        Determine file type based on extension
        
        Args:
            filename: Name of the file
            
        Returns:
            File type category
        """
        ext = os.path.splitext(filename)[1].lower()
        
        type_mapping = {
            '.txt': 'text',
            '.log': 'log',
            '.csv': 'data',
            '.json': 'data',
            '.xml': 'data',
            '.db': 'database',
            '.sqlite': 'database',
            '.sql': 'database',
            '.doc': 'document',
            '.docx': 'document',
            '.pdf': 'document',
            '.xls': 'spreadsheet',
            '.xlsx': 'spreadsheet',
            '.ini': 'config',
            '.cfg': 'config',
            '.conf': 'config',
            '.exe': 'executable',
            '.dll': 'executable',
            '.sys': 'system',
            '.reg': 'registry'
        }
        
        return type_mapping.get(ext, 'unknown')
    
    def _is_extractable(self, filename: str, is_directory: bool) -> bool:
        """
        Determine if file is suitable for ML extraction
        
        Args:
            filename: Name of the file
            is_directory: Whether this is a directory
            
        Returns:
            True if file is extractable for ML, False otherwise
        """
        if is_directory:
            return False
        
        # Files suitable for ML extraction
        extractable_extensions = {
            '.txt', '.log', '.csv', '.json', '.xml', '.db', '.sqlite', 
            '.sql', '.doc', '.docx', '.pdf', '.xls', '.xlsx', '.ini', 
            '.cfg', '.conf'
        }
        
        ext = os.path.splitext(filename)[1].lower()
        return ext in extractable_extensions


def scan_unc_path(unc_path: str, username: str = "Administrator", 
                 password: str = "Veeam123", max_depth: int = 3) -> List[Dict]:
    """
    Convenience function to scan UNC path for files
    
    Args:
        unc_path: UNC path to scan
        username: SMB username
        password: SMB password
        max_depth: Maximum directory depth
        
    Returns:
        List of file dictionaries
    """
    scanner = UNCFileScanner(username, password)
    try:
        files = scanner.list_files(unc_path, max_depth)
        return files
    finally:
        scanner.disconnect()

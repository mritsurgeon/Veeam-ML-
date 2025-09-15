import os
import re
import json
import csv
import logging
import pandas as pd
from typing import Dict, List, Any, Optional, Generator
from datetime import datetime
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

logger = logging.getLogger(__name__)

class DataExtractionError(Exception):
    """Custom exception for data extraction errors."""
    pass

class BaseDataExtractor:
    """Base class for data extractors."""
    
    def __init__(self, mount_point: str):
        self.mount_point = mount_point
        
    def extract(self, file_path: str, **kwargs) -> pd.DataFrame:
        """Extract data from a file. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement extract method")
    
    def get_full_path(self, relative_path: str) -> str:
        """Get full path by combining mount point with relative path."""
        return os.path.join(self.mount_point, relative_path.lstrip('/'))

class LogFileExtractor(BaseDataExtractor):
    """Extractor for various log file formats."""
    
    def __init__(self, mount_point: str):
        super().__init__(mount_point)
        self.log_patterns = {
            'apache_access': r'(?P<ip>\S+) \S+ \S+ \[(?P<timestamp>[^\]]+)\] "(?P<method>\S+) (?P<url>\S+) (?P<protocol>\S+)" (?P<status>\d+) (?P<size>\S+)',
            'apache_error': r'\[(?P<timestamp>[^\]]+)\] \[(?P<level>\w+)\] (?P<message>.*)',
            'iis': r'(?P<date>\S+) (?P<time>\S+) (?P<s_ip>\S+) (?P<method>\S+) (?P<uri_stem>\S+) (?P<uri_query>\S+) (?P<port>\S+) (?P<username>\S+) (?P<c_ip>\S+) (?P<user_agent>[^"]*) (?P<referer>[^"]*) (?P<status>\S+) (?P<substatus>\S+) (?P<sc_status>\S+) (?P<time_taken>\S+)',
            'windows_event': r'(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (?P<level>\w+) (?P<source>\S+) (?P<event_id>\d+) (?P<message>.*)',
            'syslog': r'(?P<timestamp>\w{3} \d{1,2} \d{2}:\d{2}:\d{2}) (?P<hostname>\S+) (?P<process>\S+): (?P<message>.*)',
            'generic': r'(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[^\s]*)\s+(?P<level>\w+)\s+(?P<message>.*)'
        }
    
    def extract(self, file_path: str, log_format: str = 'auto', **kwargs) -> pd.DataFrame:
        """
        Extract structured data from log files.
        
        Args:
            file_path: Path to the log file relative to mount point
            log_format: Format of the log file ('auto', 'apache_access', 'apache_error', etc.)
            
        Returns:
            DataFrame containing parsed log entries
        """
        full_path = self.get_full_path(file_path)
        
        if not os.path.exists(full_path):
            raise DataExtractionError(f"Log file not found: {full_path}")
        
        try:
            log_entries = []
            
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    parsed_entry = self._parse_log_line(line, log_format)
                    if parsed_entry:
                        parsed_entry['line_number'] = line_num
                        parsed_entry['raw_line'] = line
                        log_entries.append(parsed_entry)
            
            if not log_entries:
                logger.warning(f"No parseable log entries found in {file_path}")
                return pd.DataFrame()
            
            df = pd.DataFrame(log_entries)
            logger.info(f"Extracted {len(df)} log entries from {file_path}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to extract data from log file {file_path}: {str(e)}")
            raise DataExtractionError(f"Log extraction failed: {str(e)}")
    
    def _parse_log_line(self, line: str, log_format: str) -> Optional[Dict[str, Any]]:
        """Parse a single log line based on the specified format."""
        if log_format == 'auto':
            # Try different patterns until one matches
            for format_name, pattern in self.log_patterns.items():
                match = re.match(pattern, line)
                if match:
                    result = match.groupdict()
                    result['detected_format'] = format_name
                    return result
            
            # If no pattern matches, create a generic entry
            return {
                'message': line,
                'detected_format': 'unknown'
            }
        else:
            pattern = self.log_patterns.get(log_format)
            if pattern:
                match = re.match(pattern, line)
                if match:
                    return match.groupdict()
        
        return None

class DatabaseExtractor(BaseDataExtractor):
    """Extractor for database files (SQLite, SQL dumps, etc.)."""
    
    def extract(self, file_path: str, query: Optional[str] = None, **kwargs) -> pd.DataFrame:
        """
        Extract data from database files.
        
        Args:
            file_path: Path to the database file relative to mount point
            query: SQL query to execute (optional, defaults to listing all tables)
            
        Returns:
            DataFrame containing query results
        """
        full_path = self.get_full_path(file_path)
        
        if not os.path.exists(full_path):
            raise DataExtractionError(f"Database file not found: {full_path}")
        
        try:
            # Determine database type by file extension
            file_ext = Path(full_path).suffix.lower()
            
            if file_ext in ['.db', '.sqlite', '.sqlite3']:
                return self._extract_from_sqlite(full_path, query)
            elif file_ext in ['.sql']:
                return self._extract_from_sql_dump(full_path)
            else:
                raise DataExtractionError(f"Unsupported database file type: {file_ext}")
                
        except Exception as e:
            logger.error(f"Failed to extract data from database {file_path}: {str(e)}")
            raise DataExtractionError(f"Database extraction failed: {str(e)}")
    
    def _extract_from_sqlite(self, db_path: str, query: Optional[str] = None) -> pd.DataFrame:
        """Extract data from SQLite database."""
        conn = sqlite3.connect(db_path)
        
        try:
            if query is None:
                # Get list of tables
                tables_query = "SELECT name FROM sqlite_master WHERE type='table';"
                tables_df = pd.read_sql_query(tables_query, conn)
                
                if len(tables_df) == 0:
                    return pd.DataFrame()
                
                # If only one table, select all from it
                if len(tables_df) == 1:
                    table_name = tables_df.iloc[0]['name']
                    query = f"SELECT * FROM {table_name} LIMIT 1000;"
                else:
                    # Return table list
                    return tables_df
            
            df = pd.read_sql_query(query, conn)
            logger.info(f"Extracted {len(df)} records from SQLite database")
            return df
            
        finally:
            conn.close()
    
    def _extract_from_sql_dump(self, sql_path: str) -> pd.DataFrame:
        """Extract metadata from SQL dump files."""
        with open(sql_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Extract table creation statements
        table_pattern = r'CREATE TABLE\s+(\w+)\s*\((.*?)\);'
        tables = re.findall(table_pattern, content, re.IGNORECASE | re.DOTALL)
        
        table_info = []
        for table_name, columns_def in tables:
            # Count INSERT statements for this table
            insert_pattern = rf'INSERT INTO\s+{table_name}'
            insert_count = len(re.findall(insert_pattern, content, re.IGNORECASE))
            
            table_info.append({
                'table_name': table_name,
                'columns_definition': columns_def.strip(),
                'estimated_rows': insert_count
            })
        
        return pd.DataFrame(table_info)

class ConfigFileExtractor(BaseDataExtractor):
    """Extractor for configuration files (JSON, XML, INI, etc.)."""
    
    def extract(self, file_path: str, **kwargs) -> pd.DataFrame:
        """
        Extract data from configuration files.
        
        Args:
            file_path: Path to the config file relative to mount point
            
        Returns:
            DataFrame containing configuration key-value pairs
        """
        full_path = self.get_full_path(file_path)
        
        if not os.path.exists(full_path):
            raise DataExtractionError(f"Config file not found: {full_path}")
        
        try:
            file_ext = Path(full_path).suffix.lower()
            
            if file_ext == '.json':
                return self._extract_from_json(full_path)
            elif file_ext == '.xml':
                return self._extract_from_xml(full_path)
            elif file_ext in ['.ini', '.cfg', '.conf']:
                return self._extract_from_ini(full_path)
            else:
                # Try to parse as key-value pairs
                return self._extract_key_value_pairs(full_path)
                
        except Exception as e:
            logger.error(f"Failed to extract config from {file_path}: {str(e)}")
            raise DataExtractionError(f"Config extraction failed: {str(e)}")
    
    def _extract_from_json(self, json_path: str) -> pd.DataFrame:
        """Extract data from JSON configuration files."""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Flatten nested JSON structure
        flattened = self._flatten_dict(data)
        
        config_items = []
        for key, value in flattened.items():
            config_items.append({
                'key': key,
                'value': str(value),
                'type': type(value).__name__
            })
        
        return pd.DataFrame(config_items)
    
    def _extract_from_xml(self, xml_path: str) -> pd.DataFrame:
        """Extract data from XML configuration files."""
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        config_items = []
        
        def extract_elements(element, prefix=''):
            for child in element:
                key = f"{prefix}.{child.tag}" if prefix else child.tag
                
                if child.text and child.text.strip():
                    config_items.append({
                        'key': key,
                        'value': child.text.strip(),
                        'type': 'text'
                    })
                
                # Extract attributes
                for attr_name, attr_value in child.attrib.items():
                    config_items.append({
                        'key': f"{key}@{attr_name}",
                        'value': attr_value,
                        'type': 'attribute'
                    })
                
                # Recursively process children
                extract_elements(child, key)
        
        extract_elements(root)
        return pd.DataFrame(config_items)
    
    def _extract_from_ini(self, ini_path: str) -> pd.DataFrame:
        """Extract data from INI/CFG configuration files."""
        import configparser
        
        config = configparser.ConfigParser()
        config.read(ini_path)
        
        config_items = []
        for section_name in config.sections():
            for key, value in config.items(section_name):
                config_items.append({
                    'section': section_name,
                    'key': key,
                    'value': value,
                    'type': 'ini_setting'
                })
        
        return pd.DataFrame(config_items)
    
    def _extract_key_value_pairs(self, file_path: str) -> pd.DataFrame:
        """Extract key-value pairs from generic text files."""
        config_items = []
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#') or line.startswith(';'):
                    continue
                
                # Try different separators
                for separator in ['=', ':', ' ']:
                    if separator in line:
                        parts = line.split(separator, 1)
                        if len(parts) == 2:
                            key, value = parts
                            config_items.append({
                                'key': key.strip(),
                                'value': value.strip(),
                                'line_number': line_num,
                                'type': 'key_value'
                            })
                            break
        
        return pd.DataFrame(config_items)
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten a nested dictionary."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

class StructuredDataExtractor(BaseDataExtractor):
    """Extractor for structured data files (CSV, TSV, Excel, etc.)."""
    
    def extract(self, file_path: str, **kwargs) -> pd.DataFrame:
        """
        Extract data from structured data files.
        
        Args:
            file_path: Path to the data file relative to mount point
            
        Returns:
            DataFrame containing the structured data
        """
        full_path = self.get_full_path(file_path)
        
        if not os.path.exists(full_path):
            raise DataExtractionError(f"Data file not found: {full_path}")
        
        try:
            file_ext = Path(full_path).suffix.lower()
            
            if file_ext == '.csv':
                return pd.read_csv(full_path, **kwargs)
            elif file_ext == '.tsv':
                return pd.read_csv(full_path, sep='\t', **kwargs)
            elif file_ext in ['.xlsx', '.xls']:
                return pd.read_excel(full_path, **kwargs)
            elif file_ext == '.json':
                return pd.read_json(full_path, **kwargs)
            else:
                # Try to read as CSV with different separators
                for sep in [',', '\t', ';', '|']:
                    try:
                        df = pd.read_csv(full_path, sep=sep, **kwargs)
                        if len(df.columns) > 1:  # If we got multiple columns, it's probably correct
                            return df
                    except:
                        continue
                
                raise DataExtractionError(f"Unable to parse structured data file: {file_ext}")
                
        except Exception as e:
            logger.error(f"Failed to extract structured data from {file_path}: {str(e)}")
            raise DataExtractionError(f"Structured data extraction failed: {str(e)}")

class DataExtractionService:
    """Main service for coordinating data extraction from mounted backups."""
    
    def __init__(self, mount_point: str):
        self.mount_point = mount_point
        self.extractors = {
            'log': LogFileExtractor(mount_point),
            'database': DatabaseExtractor(mount_point),
            'config': ConfigFileExtractor(mount_point),
            'structured': StructuredDataExtractor(mount_point)
        }
    
    def extract_data(self, file_path: str, extractor_type: str, **kwargs) -> pd.DataFrame:
        """
        Extract data using the specified extractor.
        
        Args:
            file_path: Path to the file relative to mount point
            extractor_type: Type of extractor to use ('log', 'database', 'config', 'structured')
            **kwargs: Additional arguments for the extractor
            
        Returns:
            DataFrame containing extracted data
        """
        if extractor_type not in self.extractors:
            raise DataExtractionError(f"Unknown extractor type: {extractor_type}")
        
        extractor = self.extractors[extractor_type]
        return extractor.extract(file_path, **kwargs)
    
    def auto_detect_and_extract(self, file_path: str) -> pd.DataFrame:
        """
        Automatically detect file type and extract data.
        
        Args:
            file_path: Path to the file relative to mount point
            
        Returns:
            DataFrame containing extracted data
        """
        full_path = os.path.join(self.mount_point, file_path.lstrip('/'))
        
        if not os.path.exists(full_path):
            raise DataExtractionError(f"File not found: {full_path}")
        
        file_ext = Path(full_path).suffix.lower()
        file_name = Path(full_path).name.lower()
        
        # Determine extractor type based on file characteristics
        if any(keyword in file_name for keyword in ['log', 'access', 'error', 'event']):
            return self.extract_data(file_path, 'log')
        elif file_ext in ['.db', '.sqlite', '.sqlite3', '.sql']:
            return self.extract_data(file_path, 'database')
        elif file_ext in ['.json', '.xml', '.ini', '.cfg', '.conf'] or 'config' in file_name:
            return self.extract_data(file_path, 'config')
        elif file_ext in ['.csv', '.tsv', '.xlsx', '.xls']:
            return self.extract_data(file_path, 'structured')
        else:
            # Try log extraction as fallback for text files
            try:
                return self.extract_data(file_path, 'log')
            except:
                raise DataExtractionError(f"Unable to determine appropriate extractor for file: {file_path}")
    
    def scan_directory(self, directory_path: str = "/") -> List[Dict[str, Any]]:
        """
        Scan a directory in the mounted backup and identify extractable files.
        
        Args:
            directory_path: Directory path relative to mount point
            
        Returns:
            List of file information dictionaries
        """
        full_dir_path = os.path.join(self.mount_point, directory_path.lstrip('/'))
        
        if not os.path.exists(full_dir_path):
            raise DataExtractionError(f"Directory not found: {full_dir_path}")
        
        extractable_files = []
        
        for root, dirs, files in os.walk(full_dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, self.mount_point)
                
                file_info = {
                    'path': relative_path,
                    'name': file,
                    'size': os.path.getsize(file_path),
                    'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                    'extractable': self._is_extractable(file),
                    'suggested_extractor': self._suggest_extractor(file)
                }
                
                extractable_files.append(file_info)
        
        return extractable_files
    
    def _is_extractable(self, filename: str) -> bool:
        """Check if a file is likely to be extractable."""
        file_ext = Path(filename).suffix.lower()
        extractable_extensions = [
            '.log', '.txt', '.csv', '.tsv', '.json', '.xml', '.ini', '.cfg', '.conf',
            '.db', '.sqlite', '.sqlite3', '.sql', '.xlsx', '.xls'
        ]
        
        return (file_ext in extractable_extensions or 
                any(keyword in filename.lower() for keyword in ['log', 'config', 'data']))
    
    def _suggest_extractor(self, filename: str) -> str:
        """Suggest the most appropriate extractor for a file."""
        file_ext = Path(filename).suffix.lower()
        file_name = filename.lower()
        
        if any(keyword in file_name for keyword in ['log', 'access', 'error', 'event']):
            return 'log'
        elif file_ext in ['.db', '.sqlite', '.sqlite3', '.sql']:
            return 'database'
        elif file_ext in ['.json', '.xml', '.ini', '.cfg', '.conf'] or 'config' in file_name:
            return 'config'
        elif file_ext in ['.csv', '.tsv', '.xlsx', '.xls']:
            return 'structured'
        else:
            return 'log'  # Default fallback


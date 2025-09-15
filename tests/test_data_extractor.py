"""
Tests for data extraction services.
"""
import pytest
import pandas as pd
from unittest.mock import Mock, patch, mock_open
from src.services.data_extractor import (
    BaseDataExtractor, 
    LogFileExtractor, 
    DatabaseExtractor, 
    ConfigFileExtractor,
    StructuredDataExtractor,
    DataExtractionService,
    DataExtractionError
)


class TestBaseDataExtractor:
    """Test cases for BaseDataExtractor class."""
    
    def test_init(self):
        """Test BaseDataExtractor initialization."""
        extractor = BaseDataExtractor('/tmp/mount')
        assert extractor is not None
        assert extractor.mount_point == '/tmp/mount'
    
    def test_get_full_path(self):
        """Test get_full_path method."""
        extractor = BaseDataExtractor('/tmp/mount')
        
        # Test with relative path
        full_path = extractor.get_full_path('file.txt')
        assert full_path == '/tmp/mount/file.txt'
        
        # Test with absolute path
        full_path = extractor.get_full_path('/file.txt')
        assert full_path == '/tmp/mount/file.txt'
    
    def test_extract_not_implemented(self):
        """Test that extract method raises NotImplementedError."""
        extractor = BaseDataExtractor('/tmp/mount')
        
        with pytest.raises(NotImplementedError):
            extractor.extract('test.txt')


class TestLogFileExtractor:
    """Test cases for LogFileExtractor class."""
    
    def test_init(self):
        """Test LogFileExtractor initialization."""
        extractor = LogFileExtractor('/tmp/mount')
        assert extractor is not None
        assert extractor.mount_point == '/tmp/mount'
        assert hasattr(extractor, 'log_patterns')
    
    def test_log_patterns_exist(self):
        """Test that log patterns are defined."""
        extractor = LogFileExtractor('/tmp/mount')
        
        expected_patterns = [
            'apache_access', 'apache_error', 'iis', 
            'windows_event', 'syslog', 'generic'
        ]
        
        for pattern in expected_patterns:
            assert pattern in extractor.log_patterns
    
    def test_extract_with_mock_file(self):
        """Test log extraction with mocked file."""
        extractor = LogFileExtractor('/tmp/mount')
        
        # Mock log content
        log_content = """192.168.1.1 - - [25/Dec/2023:10:00:00 +0000] "GET /index.html HTTP/1.1" 200 1234
192.168.1.2 - - [25/Dec/2023:10:01:00 +0000] "POST /api/data HTTP/1.1" 201 5678"""
        
        with patch("builtins.open", mock_open(read_data=log_content)):
            with patch('os.path.exists', return_value=True):
                result = extractor.extract('access.log', log_format='apache_access')
                
                assert isinstance(result, pd.DataFrame)
                assert len(result) == 2
                assert 'ip' in result.columns
                assert 'timestamp' in result.columns
                assert 'method' in result.columns


class TestDatabaseExtractor:
    """Test cases for DatabaseExtractor class."""
    
    def test_init(self):
        """Test DatabaseExtractor initialization."""
        extractor = DatabaseExtractor('/tmp/mount')
        assert extractor is not None
        assert extractor.mount_point == '/tmp/mount'
    
    def test_extract_sqlite_with_mock(self):
        """Test SQLite extraction with mocked database."""
        extractor = DatabaseExtractor('/tmp/mount')
        
        # Mock SQLite connection and cursor
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            (1, 'John', 'Doe', 'john@example.com'),
            (2, 'Jane', 'Smith', 'jane@example.com')
        ]
        mock_cursor.description = [
            ('id',), ('first_name',), ('last_name',), ('email',)
        ]
        
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        with patch('sqlite3.connect', return_value=mock_conn):
            result = extractor.extract('test.db', table_name='users')
            
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 2
            assert 'id' in result.columns
            assert 'first_name' in result.columns
            assert 'last_name' in result.columns
            assert 'email' in result.columns


class TestConfigFileExtractor:
    """Test cases for ConfigFileExtractor class."""
    
    def test_init(self):
        """Test ConfigFileExtractor initialization."""
        extractor = ConfigFileExtractor('/tmp/mount')
        assert extractor is not None
        assert extractor.mount_point == '/tmp/mount'
    
    def test_extract_json_config(self):
        """Test JSON config file extraction."""
        extractor = ConfigFileExtractor('/tmp/mount')
        
        json_content = '{"database": {"host": "localhost", "port": 5432}, "api": {"key": "secret"}}'
        
        with patch("builtins.open", mock_open(read_data=json_content)):
            with patch('os.path.exists', return_value=True):
                result = extractor.extract('config.json')
                
                assert isinstance(result, pd.DataFrame)
                assert len(result) > 0
                assert 'key' in result.columns
                assert 'value' in result.columns


class TestStructuredDataExtractor:
    """Test cases for StructuredDataExtractor class."""
    
    def test_init(self):
        """Test StructuredDataExtractor initialization."""
        extractor = StructuredDataExtractor('/tmp/mount')
        assert extractor is not None
        assert extractor.mount_point == '/tmp/mount'
    
    def test_extract_csv_file(self):
        """Test CSV file extraction."""
        extractor = StructuredDataExtractor('/tmp/mount')
        
        csv_content = "name,age,city\nJohn,25,New York\nJane,30,London"
        
        with patch("builtins.open", mock_open(read_data=csv_content)):
            with patch('os.path.exists', return_value=True):
                with patch('pandas.read_csv') as mock_read_csv:
                    mock_df = pd.DataFrame({
                        'name': ['John', 'Jane'],
                        'age': [25, 30],
                        'city': ['New York', 'London']
                    })
                    mock_read_csv.return_value = mock_df
                    
                    result = extractor.extract('data.csv')
                    
                    assert isinstance(result, pd.DataFrame)
                    assert len(result) == 2
                    assert 'name' in result.columns
                    assert 'age' in result.columns
                    assert 'city' in result.columns


class TestDataExtractionService:
    """Test cases for DataExtractionService class."""
    
    def test_init(self):
        """Test DataExtractionService initialization."""
        service = DataExtractionService()
        assert service is not None
        assert hasattr(service, 'extractors')
    
    def test_get_extractor_for_file_type(self):
        """Test getting appropriate extractor for file type."""
        service = DataExtractionService()
        
        # Test log file
        extractor = service.get_extractor_for_file_type('access.log')
        assert isinstance(extractor, LogFileExtractor)
        
        # Test database file
        extractor = service.get_extractor_for_file_type('database.db')
        assert isinstance(extractor, DatabaseExtractor)
        
        # Test config file
        extractor = service.get_extractor_for_file_type('config.json')
        assert isinstance(extractor, ConfigFileExtractor)
        
        # Test structured data file
        extractor = service.get_extractor_for_file_type('data.csv')
        assert isinstance(extractor, StructuredDataExtractor)
    
    def test_extract_from_file(self):
        """Test extracting data from a file."""
        service = DataExtractionService()
        
        with patch.object(service, 'get_extractor_for_file_type') as mock_get_extractor:
            mock_extractor = Mock()
            mock_extractor.extract.return_value = pd.DataFrame({'test': [1, 2, 3]})
            mock_get_extractor.return_value = mock_extractor
            
            result = service.extract_from_file('/tmp/mount/test.log')
            
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 3
            assert 'test' in result.columns
    
    def test_extract_from_directory(self):
        """Test extracting data from a directory."""
        service = DataExtractionService()
        
        # Mock directory structure
        mock_files = [
            '/tmp/mount/file1.log',
            '/tmp/mount/file2.csv',
            '/tmp/mount/file3.json'
        ]
        
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [('/tmp/mount', [], ['file1.log', 'file2.csv', 'file3.json'])]
            
            with patch.object(service, 'extract_from_file') as mock_extract:
                mock_extract.side_effect = [
                    pd.DataFrame({'log_data': [1, 2]}),
                    pd.DataFrame({'csv_data': [3, 4]}),
                    pd.DataFrame({'json_data': [5, 6]})
                ]
                
                results = service.extract_from_directory('/tmp/mount')
                
                assert len(results) == 3
                assert all(isinstance(result, pd.DataFrame) for result in results)
                assert mock_extract.call_count == 3


class TestDataExtractionError:
    """Test cases for DataExtractionError exception."""
    
    def test_exception_creation(self):
        """Test DataExtractionError exception creation."""
        error = DataExtractionError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
"""
Tests for ML processing services.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
from src.services.ml_processor import (
    DataPreprocessor, 
    ClassificationProcessor, 
    RegressionProcessor,
    ClusteringProcessor,
    MLProcessingError
)


class TestDataPreprocessor:
    """Test cases for DataPreprocessor class."""
    
    def test_init(self):
        """Test DataPreprocessor initialization."""
        preprocessor = DataPreprocessor()
        assert preprocessor is not None
    
    def test_extract_features_from_files(self):
        """Test feature extraction from file data."""
        preprocessor = DataPreprocessor()
        
        # Mock file data
        file_data = [
            {'name': 'test1.txt', 'size': 1024, 'extension': '.txt'},
            {'name': 'test2.pdf', 'size': 2048, 'extension': '.pdf'},
            {'name': 'test3.jpg', 'size': 512, 'extension': '.jpg'}
        ]
        
        features = preprocessor.extract_features_from_files(file_data)
        
        assert isinstance(features, pd.DataFrame)
        assert len(features) == 3
        assert 'file_size' in features.columns
        assert 'file_extension' in features.columns
    
    def test_preprocess_data(self):
        """Test data preprocessing."""
        preprocessor = DataPreprocessor()
        
        # Create sample data
        data = pd.DataFrame({
            'file_size': [1024, 2048, 512],
            'file_extension': ['.txt', '.pdf', '.jpg'],
            'numeric_feature': [1, 2, 3]
        })
        
        processed_data = preprocessor.preprocess_data(data)
        
        assert isinstance(processed_data, pd.DataFrame)
        assert len(processed_data) == 3
        # Check that categorical data is encoded
        assert 'file_extension_.txt' in processed_data.columns or 'file_extension_.pdf' in processed_data.columns
    
    def test_preprocess_data_empty(self):
        """Test preprocessing empty data."""
        preprocessor = DataPreprocessor()
        
        empty_data = pd.DataFrame()
        
        with pytest.raises(MLProcessingError):
            preprocessor.preprocess_data(empty_data)


class TestClassificationProcessor:
    """Test cases for ClassificationProcessor class."""
    
    def test_init(self):
        """Test ClassificationProcessor initialization."""
        processor = ClassificationProcessor()
        assert processor is not None
    
    def test_train_model(self):
        """Test model training."""
        processor = ClassificationProcessor()
        
        # Create sample training data
        X = pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5],
            'feature2': [2, 4, 6, 8, 10]
        })
        y = pd.Series([0, 0, 1, 1, 1])
        
        model = processor.train_model(X, y, {'n_estimators': 10, 'random_state': 42})
        
        assert model is not None
        assert hasattr(model, 'predict')
    
    def test_train_model_insufficient_data(self):
        """Test model training with insufficient data."""
        processor = ClassificationProcessor()
        
        # Create insufficient training data
        X = pd.DataFrame({'feature1': [1]})
        y = pd.Series([0])
        
        with pytest.raises(MLProcessingError):
            processor.train_model(X, y, {})
    
    def test_predict(self):
        """Test model prediction."""
        processor = ClassificationProcessor()
        
        # Train a model first
        X_train = pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5],
            'feature2': [2, 4, 6, 8, 10]
        })
        y_train = pd.Series([0, 0, 1, 1, 1])
        
        model = processor.train_model(X_train, y_train, {'n_estimators': 10, 'random_state': 42})
        
        # Test prediction
        X_test = pd.DataFrame({
            'feature1': [6, 7],
            'feature2': [12, 14]
        })
        
        predictions = processor.predict(model, X_test)
        
        assert len(predictions) == 2
        assert all(isinstance(pred, (int, np.integer)) for pred in predictions)
    
    def test_evaluate_model(self):
        """Test model evaluation."""
        processor = ClassificationProcessor()
        
        # Create sample data
        X = pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5, 6],
            'feature2': [2, 4, 6, 8, 10, 12]
        })
        y = pd.Series([0, 0, 1, 1, 1, 0])
        
        model = processor.train_model(X, y, {'n_estimators': 10, 'random_state': 42})
        metrics = processor.evaluate_model(model, X, y)
        
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics
        assert all(isinstance(metric, (int, float)) for metric in metrics.values())


class TestRegressionProcessor:
    """Test cases for RegressionProcessor class."""
    
    def test_init(self):
        """Test RegressionProcessor initialization."""
        processor = RegressionProcessor()
        assert processor is not None
    
    def test_train_model(self):
        """Test regression model training."""
        processor = RegressionProcessor()
        
        # Create sample training data
        X = pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5],
            'feature2': [2, 4, 6, 8, 10]
        })
        y = pd.Series([1.5, 3.0, 4.5, 6.0, 7.5])
        
        model = processor.train_model(X, y, {'n_estimators': 10, 'random_state': 42})
        
        assert model is not None
        assert hasattr(model, 'predict')
    
    def test_evaluate_model(self):
        """Test regression model evaluation."""
        processor = RegressionProcessor()
        
        # Create sample data
        X = pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5],
            'feature2': [2, 4, 6, 8, 10]
        })
        y = pd.Series([1.5, 3.0, 4.5, 6.0, 7.5])
        
        model = processor.train_model(X, y, {'n_estimators': 10, 'random_state': 42})
        metrics = processor.evaluate_model(model, X, y)
        
        assert 'mse' in metrics
        assert 'rmse' in metrics
        assert 'r2_score' in metrics
        assert all(isinstance(metric, (int, float)) for metric in metrics.values())


class TestClusteringProcessor:
    """Test cases for ClusteringProcessor class."""
    
    def test_init(self):
        """Test ClusteringProcessor initialization."""
        processor = ClusteringProcessor()
        assert processor is not None
    
    def test_train_model(self):
        """Test clustering model training."""
        processor = ClusteringProcessor()
        
        # Create sample training data
        X = pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5],
            'feature2': [2, 4, 6, 8, 10]
        })
        
        model = processor.train_model(X, None, {'n_clusters': 2, 'random_state': 42})
        
        assert model is not None
        assert hasattr(model, 'predict')
    
    def test_predict(self):
        """Test clustering prediction."""
        processor = ClusteringProcessor()
        
        # Train a model first
        X_train = pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5],
            'feature2': [2, 4, 6, 8, 10]
        })
        
        model = processor.train_model(X_train, None, {'n_clusters': 2, 'random_state': 42})
        
        # Test prediction
        X_test = pd.DataFrame({
            'feature1': [6, 7],
            'feature2': [12, 14]
        })
        
        predictions = processor.predict(model, X_test)
        
        assert len(predictions) == 2
        assert all(isinstance(pred, (int, np.integer)) for pred in predictions)
        assert all(0 <= pred < 2 for pred in predictions)  # Should be cluster labels 0 or 1

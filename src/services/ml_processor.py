import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, f_classif, f_regression
from sklearn.metrics import classification_report, mean_squared_error, silhouette_score
from sklearn.linear_model import LinearRegression
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import MinMaxScaler
import json
from datetime import datetime
import joblib
import os

logger = logging.getLogger(__name__)

class MLProcessingError(Exception):
    """Custom exception for ML processing errors."""
    pass

class DataPreprocessor:
    """Handles data preprocessing for machine learning."""
    
    def __init__(self):
        self.scalers = {}
        self.encoders = {}
        self.vectorizers = {}
    
    def preprocess_for_classification(self, df: pd.DataFrame, target_column: str, 
                                    text_columns: List[str] = None) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Preprocess data for classification tasks.
        
        Args:
            df: Input DataFrame
            target_column: Name of the target column
            text_columns: List of text columns to vectorize
            
        Returns:
            Tuple of (features DataFrame, target Series)
        """
        if target_column not in df.columns:
            raise MLProcessingError(f"Target column '{target_column}' not found in data")
        
        # Separate features and target
        X = df.drop(columns=[target_column]).copy()
        y = df[target_column].copy()
        
        # Handle missing values
        X = self._handle_missing_values(X)
        
        # Encode categorical variables
        X = self._encode_categorical_features(X)
        
        # Vectorize text columns if specified
        if text_columns:
            X = self._vectorize_text_features(X, text_columns)
        
        # Scale numerical features
        X = self._scale_numerical_features(X)
        
        # Encode target variable if it's categorical
        if y.dtype == 'object':
            le = LabelEncoder()
            y = pd.Series(le.fit_transform(y), index=y.index)
            self.encoders['target'] = le
        
        return X, y
    
    def preprocess_for_regression(self, df: pd.DataFrame, target_column: str,
                                text_columns: List[str] = None) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Preprocess data for regression tasks.
        
        Args:
            df: Input DataFrame
            target_column: Name of the target column
            text_columns: List of text columns to vectorize
            
        Returns:
            Tuple of (features DataFrame, target Series)
        """
        if target_column not in df.columns:
            raise MLProcessingError(f"Target column '{target_column}' not found in data")
        
        # Separate features and target
        X = df.drop(columns=[target_column]).copy()
        y = df[target_column].copy()
        
        # Ensure target is numeric
        y = pd.to_numeric(y, errors='coerce')
        
        # Remove rows where target is NaN
        valid_indices = ~y.isna()
        X = X[valid_indices]
        y = y[valid_indices]
        
        # Handle missing values
        X = self._handle_missing_values(X)
        
        # Encode categorical variables
        X = self._encode_categorical_features(X)
        
        # Vectorize text columns if specified
        if text_columns:
            X = self._vectorize_text_features(X, text_columns)
        
        # Scale numerical features
        X = self._scale_numerical_features(X)
        
        return X, y
    
    def preprocess_for_clustering(self, df: pd.DataFrame, 
                                text_columns: List[str] = None) -> pd.DataFrame:
        """
        Preprocess data for clustering tasks.
        
        Args:
            df: Input DataFrame
            text_columns: List of text columns to vectorize
            
        Returns:
            Preprocessed DataFrame
        """
        X = df.copy()
        
        # Handle missing values
        X = self._handle_missing_values(X)
        
        # Encode categorical variables
        X = self._encode_categorical_features(X)
        
        # Vectorize text columns if specified
        if text_columns:
            X = self._vectorize_text_features(X, text_columns)
        
        # Scale all features for clustering
        X = self._scale_numerical_features(X)
        
        return X
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values in the dataset."""
        df = df.copy()
        
        for column in df.columns:
            if df[column].dtype in ['object', 'string']:
                # Fill categorical/text columns with 'unknown'
                df[column] = df[column].fillna('unknown')
            else:
                # Fill numerical columns with median
                df[column] = df[column].fillna(df[column].median())
        
        return df
    
    def _encode_categorical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encode categorical features."""
        df = df.copy()
        categorical_columns = df.select_dtypes(include=['object', 'string']).columns
        
        for column in categorical_columns:
            if df[column].nunique() <= 10:  # Use one-hot encoding for low cardinality
                encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
                encoded = encoder.fit_transform(df[[column]])
                encoded_df = pd.DataFrame(
                    encoded, 
                    columns=[f"{column}_{cat}" for cat in encoder.categories_[0]],
                    index=df.index
                )
                df = pd.concat([df.drop(columns=[column]), encoded_df], axis=1)
                self.encoders[column] = encoder
            else:  # Use label encoding for high cardinality
                encoder = LabelEncoder()
                df[column] = encoder.fit_transform(df[column].astype(str))
                self.encoders[column] = encoder
        
        return df
    
    def _vectorize_text_features(self, df: pd.DataFrame, text_columns: List[str]) -> pd.DataFrame:
        """Vectorize text features using TF-IDF."""
        df = df.copy()
        
        for column in text_columns:
            if column in df.columns:
                vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
                text_vectors = vectorizer.fit_transform(df[column].astype(str))
                
                # Create DataFrame with vectorized features
                vector_df = pd.DataFrame(
                    text_vectors.toarray(),
                    columns=[f"{column}_tfidf_{i}" for i in range(text_vectors.shape[1])],
                    index=df.index
                )
                
                df = pd.concat([df.drop(columns=[column]), vector_df], axis=1)
                self.vectorizers[column] = vectorizer
        
        return df
    
    def _scale_numerical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Scale numerical features."""
        df = df.copy()
        numerical_columns = df.select_dtypes(include=[np.number]).columns
        
        if len(numerical_columns) > 0:
            scaler = StandardScaler()
            df[numerical_columns] = scaler.fit_transform(df[numerical_columns])
            self.scalers['numerical'] = scaler
        
        return df

class ClassificationProcessor:
    """Handles classification ML tasks."""
    
    def __init__(self):
        self.model = None
        self.feature_importance = None
    
    def train_and_predict(self, X: pd.DataFrame, y: pd.Series, 
                         test_size: float = 0.2) -> Dict[str, Any]:
        """
        Train a classification model and return predictions and metrics.
        
        Args:
            X: Features DataFrame
            y: Target Series
            test_size: Proportion of data to use for testing
            
        Returns:
            Dictionary containing model results
        """
        try:
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42, stratify=y
            )
            
            # Train model
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
            self.model.fit(X_train, y_train)
            
            # Make predictions
            y_pred = self.model.predict(X_test)
            y_pred_proba = self.model.predict_proba(X_test)
            
            # Calculate feature importance
            self.feature_importance = pd.DataFrame({
                'feature': X.columns,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            # Generate classification report
            report = classification_report(y_test, y_pred, output_dict=True)
            
            results = {
                'model_type': 'classification',
                'accuracy': report['accuracy'],
                'classification_report': report,
                'feature_importance': self.feature_importance.to_dict('records'),
                'predictions': {
                    'y_test': y_test.tolist(),
                    'y_pred': y_pred.tolist(),
                    'y_pred_proba': y_pred_proba.tolist()
                },
                'model_params': self.model.get_params()
            }
            
            logger.info(f"Classification model trained with accuracy: {report['accuracy']:.3f}")
            return results
            
        except Exception as e:
            logger.error(f"Classification training failed: {str(e)}")
            raise MLProcessingError(f"Classification failed: {str(e)}")

class RegressionProcessor:
    """Handles regression ML tasks."""
    
    def __init__(self):
        self.model = None
        self.feature_importance = None
    
    def train_and_predict(self, X: pd.DataFrame, y: pd.Series, 
                         test_size: float = 0.2) -> Dict[str, Any]:
        """
        Train a regression model and return predictions and metrics.
        
        Args:
            X: Features DataFrame
            y: Target Series
            test_size: Proportion of data to use for testing
            
        Returns:
            Dictionary containing model results
        """
        try:
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42
            )
            
            # Train model
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
            self.model.fit(X_train, y_train)
            
            # Make predictions
            y_pred = self.model.predict(X_test)
            
            # Calculate metrics
            mse = mean_squared_error(y_test, y_pred)
            rmse = np.sqrt(mse)
            
            # Calculate feature importance
            self.feature_importance = pd.DataFrame({
                'feature': X.columns,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            results = {
                'model_type': 'regression',
                'mse': mse,
                'rmse': rmse,
                'r2_score': self.model.score(X_test, y_test),
                'feature_importance': self.feature_importance.to_dict('records'),
                'predictions': {
                    'y_test': y_test.tolist(),
                    'y_pred': y_pred.tolist()
                },
                'model_params': self.model.get_params()
            }
            
            logger.info(f"Regression model trained with RMSE: {rmse:.3f}")
            return results
            
        except Exception as e:
            logger.error(f"Regression training failed: {str(e)}")
            raise MLProcessingError(f"Regression failed: {str(e)}")

class ClusteringProcessor:
    """Handles clustering ML tasks."""
    
    def __init__(self):
        self.model = None
        self.cluster_centers = None
    
    def perform_clustering(self, X: pd.DataFrame, n_clusters: Optional[int] = None,
                          algorithm: str = 'kmeans') -> Dict[str, Any]:
        """
        Perform clustering analysis.
        
        Args:
            X: Features DataFrame
            n_clusters: Number of clusters (auto-determined if None)
            algorithm: Clustering algorithm ('kmeans' or 'dbscan')
            
        Returns:
            Dictionary containing clustering results
        """
        try:
            if algorithm == 'kmeans':
                if n_clusters is None:
                    # Determine optimal number of clusters using elbow method
                    n_clusters = self._find_optimal_clusters(X)
                
                self.model = KMeans(n_clusters=n_clusters, random_state=42)
                cluster_labels = self.model.fit_predict(X)
                self.cluster_centers = self.model.cluster_centers_
                
            elif algorithm == 'dbscan':
                self.model = DBSCAN(eps=0.5, min_samples=5)
                cluster_labels = self.model.fit_predict(X)
                n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
                
            else:
                raise MLProcessingError(f"Unsupported clustering algorithm: {algorithm}")
            
            # Calculate silhouette score
            if len(set(cluster_labels)) > 1:
                silhouette_avg = silhouette_score(X, cluster_labels)
            else:
                silhouette_avg = 0
            
            # Analyze clusters
            cluster_analysis = self._analyze_clusters(X, cluster_labels)
            
            results = {
                'model_type': 'clustering',
                'algorithm': algorithm,
                'n_clusters': n_clusters,
                'silhouette_score': silhouette_avg,
                'cluster_labels': cluster_labels.tolist(),
                'cluster_analysis': cluster_analysis,
                'model_params': self.model.get_params() if hasattr(self.model, 'get_params') else {}
            }
            
            if hasattr(self, 'cluster_centers') and self.cluster_centers is not None:
                results['cluster_centers'] = self.cluster_centers.tolist()
            
            logger.info(f"Clustering completed with {n_clusters} clusters, silhouette score: {silhouette_avg:.3f}")
            return results
            
        except Exception as e:
            logger.error(f"Clustering failed: {str(e)}")
            raise MLProcessingError(f"Clustering failed: {str(e)}")
    
    def _find_optimal_clusters(self, X: pd.DataFrame, max_clusters: int = 10) -> int:
        """Find optimal number of clusters using elbow method."""
        inertias = []
        K_range = range(2, min(max_clusters + 1, len(X)))
        
        for k in K_range:
            kmeans = KMeans(n_clusters=k, random_state=42)
            kmeans.fit(X)
            inertias.append(kmeans.inertia_)
        
        # Simple elbow detection (find the point with maximum curvature)
        if len(inertias) >= 2:
            diffs = np.diff(inertias)
            diff2 = np.diff(diffs)
            if len(diff2) > 0:
                elbow_idx = np.argmax(diff2) + 2  # +2 because we start from k=2 and take second derivative
                return min(K_range[elbow_idx], max_clusters)
        
        return 3  # Default fallback
    
    def _analyze_clusters(self, X: pd.DataFrame, cluster_labels: np.ndarray) -> List[Dict[str, Any]]:
        """Analyze characteristics of each cluster."""
        cluster_analysis = []
        
        for cluster_id in set(cluster_labels):
            if cluster_id == -1:  # Noise points in DBSCAN
                continue
            
            cluster_mask = cluster_labels == cluster_id
            cluster_data = X[cluster_mask]
            
            analysis = {
                'cluster_id': int(cluster_id),
                'size': int(cluster_mask.sum()),
                'percentage': float(cluster_mask.sum() / len(X) * 100),
                'feature_means': cluster_data.mean().to_dict(),
                'feature_stds': cluster_data.std().to_dict()
            }
            
            cluster_analysis.append(analysis)
        
        return cluster_analysis

class AnomalyDetectionProcessor:
    """Handles anomaly detection ML tasks."""
    
    def __init__(self):
        self.model = None
    
    def detect_anomalies(self, X: pd.DataFrame, contamination: float = 0.1) -> Dict[str, Any]:
        """
        Detect anomalies in the data.
        
        Args:
            X: Features DataFrame
            contamination: Expected proportion of anomalies
            
        Returns:
            Dictionary containing anomaly detection results
        """
        try:
            # Use One-Class SVM for anomaly detection
            self.model = OneClassSVM(contamination=contamination, random_state=42)
            anomaly_labels = self.model.fit_predict(X)
            
            # Convert to binary labels (1 = normal, 0 = anomaly)
            is_anomaly = (anomaly_labels == -1)
            
            # Calculate anomaly scores
            anomaly_scores = self.model.score_samples(X)
            
            # Identify most anomalous features for each anomaly
            anomalous_indices = np.where(is_anomaly)[0]
            anomaly_details = []
            
            for idx in anomalous_indices:
                feature_values = X.iloc[idx].to_dict()
                anomaly_details.append({
                    'index': int(idx),
                    'anomaly_score': float(anomaly_scores[idx]),
                    'feature_values': feature_values
                })
            
            results = {
                'model_type': 'anomaly_detection',
                'total_samples': len(X),
                'anomalies_detected': int(is_anomaly.sum()),
                'anomaly_percentage': float(is_anomaly.sum() / len(X) * 100),
                'anomaly_labels': is_anomaly.tolist(),
                'anomaly_scores': anomaly_scores.tolist(),
                'anomaly_details': anomaly_details,
                'model_params': self.model.get_params()
            }
            
            logger.info(f"Anomaly detection completed: {is_anomaly.sum()} anomalies detected ({is_anomaly.sum()/len(X)*100:.1f}%)")
            return results
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {str(e)}")
            raise MLProcessingError(f"Anomaly detection failed: {str(e)}")

class FeatureExtractionProcessor:
    """Handles feature extraction and dimensionality reduction."""
    
    def __init__(self):
        self.pca_model = None
        self.feature_selector = None
    
    def extract_features(self, X: pd.DataFrame, y: pd.Series = None, 
                        method: str = 'pca', n_components: int = 10) -> Dict[str, Any]:
        """
        Extract or select important features.
        
        Args:
            X: Features DataFrame
            y: Target Series (required for supervised feature selection)
            method: Feature extraction method ('pca', 'select_k_best')
            n_components: Number of components/features to extract
            
        Returns:
            Dictionary containing feature extraction results
        """
        try:
            if method == 'pca':
                return self._perform_pca(X, n_components)
            elif method == 'select_k_best':
                if y is None:
                    raise MLProcessingError("Target variable required for supervised feature selection")
                return self._select_k_best_features(X, y, n_components)
            else:
                raise MLProcessingError(f"Unsupported feature extraction method: {method}")
                
        except Exception as e:
            logger.error(f"Feature extraction failed: {str(e)}")
            raise MLProcessingError(f"Feature extraction failed: {str(e)}")
    
    def _perform_pca(self, X: pd.DataFrame, n_components: int) -> Dict[str, Any]:
        """Perform Principal Component Analysis."""
        self.pca_model = PCA(n_components=min(n_components, X.shape[1]))
        X_pca = self.pca_model.fit_transform(X)
        
        # Create DataFrame with PCA components
        pca_df = pd.DataFrame(
            X_pca,
            columns=[f'PC{i+1}' for i in range(X_pca.shape[1])],
            index=X.index
        )
        
        # Calculate feature loadings
        loadings = pd.DataFrame(
            self.pca_model.components_.T,
            columns=[f'PC{i+1}' for i in range(X_pca.shape[1])],
            index=X.columns
        )
        
        results = {
            'model_type': 'feature_extraction',
            'method': 'pca',
            'n_components': X_pca.shape[1],
            'explained_variance_ratio': self.pca_model.explained_variance_ratio_.tolist(),
            'cumulative_variance_ratio': np.cumsum(self.pca_model.explained_variance_ratio_).tolist(),
            'transformed_features': pca_df.to_dict('records'),
            'feature_loadings': loadings.to_dict('records'),
            'original_features': X.columns.tolist()
        }
        
        logger.info(f"PCA completed: {X_pca.shape[1]} components explaining {np.sum(self.pca_model.explained_variance_ratio_):.3f} of variance")
        return results
    
    def _select_k_best_features(self, X: pd.DataFrame, y: pd.Series, k: int) -> Dict[str, Any]:
        """Select k best features using statistical tests."""
        # Determine if it's classification or regression
        if y.dtype == 'object' or y.nunique() < 20:
            score_func = f_classif
            task_type = 'classification'
        else:
            score_func = f_regression
            task_type = 'regression'
        
        self.feature_selector = SelectKBest(score_func=score_func, k=min(k, X.shape[1]))
        X_selected = self.feature_selector.fit_transform(X, y)
        
        # Get selected feature names
        selected_features = X.columns[self.feature_selector.get_support()].tolist()
        feature_scores = self.feature_selector.scores_
        
        # Create feature importance DataFrame
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'score': feature_scores,
            'selected': self.feature_selector.get_support()
        }).sort_values('score', ascending=False)
        
        results = {
            'model_type': 'feature_extraction',
            'method': 'select_k_best',
            'task_type': task_type,
            'n_features_selected': len(selected_features),
            'selected_features': selected_features,
            'feature_scores': feature_importance.to_dict('records'),
            'transformed_data_shape': X_selected.shape
        }
        
        logger.info(f"Feature selection completed: {len(selected_features)} features selected")
        return results

class MLProcessingService:
    """Main service for coordinating ML processing tasks."""
    
    def __init__(self):
        self.preprocessor = DataPreprocessor()
        self.processors = {
            'classification': ClassificationProcessor(),
            'regression': RegressionProcessor(),
            'clustering': ClusteringProcessor(),
            'anomaly_detection': AnomalyDetectionProcessor(),
            'feature_extraction': FeatureExtractionProcessor()
        }
    
    def process_ml_task(self, data: pd.DataFrame, task_type: str, 
                       target_column: str = None, **kwargs) -> Dict[str, Any]:
        """
        Process a machine learning task on the provided data.
        
        Args:
            data: Input DataFrame
            task_type: Type of ML task to perform
            target_column: Name of target column (required for supervised tasks)
            **kwargs: Additional parameters for the specific ML task
            
        Returns:
            Dictionary containing ML processing results
        """
        if task_type not in self.processors:
            raise MLProcessingError(f"Unsupported ML task type: {task_type}")
        
        try:
            processor = self.processors[task_type]
            
            if task_type == 'classification':
                if target_column is None:
                    raise MLProcessingError("Target column required for classification")
                X, y = self.preprocessor.preprocess_for_classification(
                    data, target_column, kwargs.get('text_columns', [])
                )
                return processor.train_and_predict(X, y, kwargs.get('test_size', 0.2))
            
            elif task_type == 'regression':
                if target_column is None:
                    raise MLProcessingError("Target column required for regression")
                X, y = self.preprocessor.preprocess_for_regression(
                    data, target_column, kwargs.get('text_columns', [])
                )
                return processor.train_and_predict(X, y, kwargs.get('test_size', 0.2))
            
            elif task_type == 'clustering':
                X = self.preprocessor.preprocess_for_clustering(
                    data, kwargs.get('text_columns', [])
                )
                return processor.perform_clustering(
                    X, kwargs.get('n_clusters'), kwargs.get('algorithm', 'kmeans')
                )
            
            elif task_type == 'anomaly_detection':
                X = self.preprocessor.preprocess_for_clustering(data)
                return processor.detect_anomalies(X, kwargs.get('contamination', 0.1))
            
            elif task_type == 'feature_extraction':
                X = self.preprocessor.preprocess_for_clustering(data)
                y = data[target_column] if target_column else None
                return processor.extract_features(
                    X, y, kwargs.get('method', 'pca'), kwargs.get('n_components', 10)
                )
            
        except Exception as e:
            logger.error(f"ML processing failed for task {task_type}: {str(e)}")
            raise MLProcessingError(f"ML processing failed: {str(e)}")
    
    def save_model(self, task_type: str, model_path: str) -> bool:
        """
        Save a trained model to disk.
        
        Args:
            task_type: Type of ML task
            model_path: Path where to save the model
            
        Returns:
            True if successful
        """
        try:
            if task_type not in self.processors:
                raise MLProcessingError(f"No processor found for task type: {task_type}")
            
            processor = self.processors[task_type]
            if hasattr(processor, 'model') and processor.model is not None:
                joblib.dump(processor.model, model_path)
                logger.info(f"Model saved to {model_path}")
                return True
            else:
                raise MLProcessingError(f"No trained model found for task type: {task_type}")
                
        except Exception as e:
            logger.error(f"Failed to save model: {str(e)}")
            return False
    
    def load_model(self, task_type: str, model_path: str) -> bool:
        """
        Load a trained model from disk.
        
        Args:
            task_type: Type of ML task
            model_path: Path to the saved model
            
        Returns:
            True if successful
        """
        try:
            if not os.path.exists(model_path):
                raise MLProcessingError(f"Model file not found: {model_path}")
            
            if task_type not in self.processors:
                raise MLProcessingError(f"No processor found for task type: {task_type}")
            
            model = joblib.load(model_path)
            self.processors[task_type].model = model
            logger.info(f"Model loaded from {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            return False


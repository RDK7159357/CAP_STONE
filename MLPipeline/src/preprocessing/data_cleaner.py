"""
Data preprocessing and feature engineering for health monitoring data
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.impute import SimpleImputer
import joblib


class HealthDataPreprocessor:
    """
    Preprocessor for health monitoring data
    """
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.imputer = SimpleImputer(strategy='mean')
        self.feature_columns = None
        
    def preprocess(self, df, fit=False):
        """
        Preprocess health metrics data
        
        Args:
            df: DataFrame with health metrics
            fit: Whether to fit the transformers (True for training, False for inference)
            
        Returns:
            Preprocessed DataFrame
        """
        df = df.copy()
        
        # Convert timestamp to datetime if needed
        if 'timestamp' in df.columns and df['timestamp'].dtype != 'datetime64[ns]':
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Extract time-based features
        if 'datetime' in df.columns:
            df['hour'] = df['datetime'].dt.hour
            df['day_of_week'] = df['datetime'].dt.dayofweek
            df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
            
            # Cyclical encoding for hour
            df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
            df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        
        # Feature engineering
        df = self._engineer_features(df)
        
        # Select numeric features
        numeric_features = ['heartRate', 'steps', 'calories', 'distance',
                          'hour_sin', 'hour_cos', 'is_weekend']
        
        # Add engineered features if they exist
        if 'hr_diff' in df.columns:
            numeric_features.extend(['hr_diff', 'hr_rolling_mean', 'hr_rolling_std'])
        
        # Filter to available columns
        numeric_features = [f for f in numeric_features if f in df.columns]
        
        if fit:
            self.feature_columns = numeric_features
        
        # Handle missing values
        if fit:
            df[numeric_features] = self.imputer.fit_transform(df[numeric_features])
        else:
            df[numeric_features] = self.imputer.transform(df[numeric_features])
        
        # Normalize features
        if fit:
            df[numeric_features] = self.scaler.fit_transform(df[numeric_features])
        else:
            df[numeric_features] = self.scaler.transform(df[numeric_features])
        
        return df
    
    def _engineer_features(self, df):
        """
        Engineer additional features from raw data
        """
        df = df.copy()
        
        # Heart rate variability features
        if 'heartRate' in df.columns:
            # Difference from previous reading
            df['hr_diff'] = df['heartRate'].diff().fillna(0)
            
            # Rolling statistics
            df['hr_rolling_mean'] = df['heartRate'].rolling(window=12, min_periods=1).mean()
            df['hr_rolling_std'] = df['heartRate'].rolling(window=12, min_periods=1).std().fillna(0)
            
            # Rate of change
            df['hr_roc'] = df['heartRate'].pct_change().fillna(0)
        
        return df
    
    def create_sequences(self, df, sequence_length=60):
        """
        Create sequences for LSTM model
        
        Args:
            df: Preprocessed DataFrame
            sequence_length: Number of time steps in each sequence
            
        Returns:
            X: Array of sequences (samples, time_steps, features)
            y: Array of labels (if available)
        """
        if self.feature_columns is None:
            raise ValueError("Preprocessor must be fitted first")
        
        features = df[self.feature_columns].values
        
        sequences = []
        labels = []
        
        for i in range(len(features) - sequence_length):
            sequences.append(features[i:i + sequence_length])
            
            if 'label' in df.columns:
                # Label is 1 if any point in sequence is anomalous
                labels.append(df['label'].iloc[i:i + sequence_length].max())
        
        X = np.array(sequences)
        y = np.array(labels) if labels else None
        
        return X, y
    
    def save(self, path):
        """Save preprocessor state"""
        joblib.dump({
            'scaler': self.scaler,
            'imputer': self.imputer,
            'feature_columns': self.feature_columns
        }, path)
        
    def load(self, path):
        """Load preprocessor state"""
        state = joblib.load(path)
        self.scaler = state['scaler']
        self.imputer = state['imputer']
        self.feature_columns = state['feature_columns']


def main():
    """
    Example usage
    """
    # Load data
    df = pd.read_csv('data/processed/health_metrics.csv')
    
    # Initialize preprocessor
    preprocessor = HealthDataPreprocessor()
    
    # Preprocess
    df_processed = preprocessor.preprocess(df, fit=True)
    
    # Create sequences
    X, y = preprocessor.create_sequences(df_processed, sequence_length=60)
    
    print(f"Created {len(X)} sequences")
    print(f"Sequence shape: {X.shape}")
    print(f"Labels shape: {y.shape if y is not None else 'N/A'}")
    
    # Save preprocessor
    preprocessor.save('models/preprocessor.pkl')
    print("Preprocessor saved")


if __name__ == "__main__":
    main()

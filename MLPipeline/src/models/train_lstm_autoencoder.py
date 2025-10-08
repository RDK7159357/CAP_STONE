"""
Train LSTM Autoencoder for anomaly detection in health monitoring data
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from preprocessing.data_cleaner import HealthDataPreprocessor


class LSTMAutoencoder:
    """
    LSTM Autoencoder for time-series anomaly detection
    """
    
    def __init__(self, sequence_length, n_features, encoding_dim=32):
        self.sequence_length = sequence_length
        self.n_features = n_features
        self.encoding_dim = encoding_dim
        self.model = None
        self.threshold = None
        
    def build_model(self):
        """
        Build LSTM Autoencoder architecture
        """
        # Encoder
        encoder_inputs = layers.Input(shape=(self.sequence_length, self.n_features))
        
        # LSTM layers for encoder
        encoder_lstm1 = layers.LSTM(128, activation='relu', return_sequences=True)(encoder_inputs)
        encoder_dropout1 = layers.Dropout(0.2)(encoder_lstm1)
        
        encoder_lstm2 = layers.LSTM(64, activation='relu', return_sequences=True)(encoder_dropout1)
        encoder_dropout2 = layers.Dropout(0.2)(encoder_lstm2)
        
        encoder_lstm3 = layers.LSTM(self.encoding_dim, activation='relu', return_sequences=False)(encoder_dropout2)
        
        # Repeat vector to match decoder input shape
        decoder_repeat = layers.RepeatVector(self.sequence_length)(encoder_lstm3)
        
        # Decoder
        decoder_lstm1 = layers.LSTM(self.encoding_dim, activation='relu', return_sequences=True)(decoder_repeat)
        decoder_dropout1 = layers.Dropout(0.2)(decoder_lstm1)
        
        decoder_lstm2 = layers.LSTM(64, activation='relu', return_sequences=True)(decoder_dropout1)
        decoder_dropout2 = layers.Dropout(0.2)(decoder_lstm2)
        
        decoder_lstm3 = layers.LSTM(128, activation='relu', return_sequences=True)(decoder_dropout2)
        
        # Output layer
        decoder_outputs = layers.TimeDistributed(layers.Dense(self.n_features))(decoder_lstm3)
        
        # Create model
        self.model = keras.Model(encoder_inputs, decoder_outputs, name='lstm_autoencoder')
        
        # Compile model
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        return self.model
    
    def train(self, X_train, X_val, epochs=100, batch_size=32):
        """
        Train the autoencoder
        """
        if self.model is None:
            self.build_model()
        
        # Callbacks
        early_stopping = keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        )
        
        reduce_lr = keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=1e-6
        )
        
        model_checkpoint = keras.callbacks.ModelCheckpoint(
            'models/checkpoints/lstm_autoencoder_best.h5',
            monitor='val_loss',
            save_best_only=True
        )
        
        # Train model
        history = self.model.fit(
            X_train, X_train,
            validation_data=(X_val, X_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[early_stopping, reduce_lr, model_checkpoint],
            verbose=1
        )
        
        return history
    
    def calculate_threshold(self, X_normal, percentile=95):
        """
        Calculate anomaly threshold based on normal data reconstruction error
        """
        predictions = self.model.predict(X_normal)
        mse = np.mean(np.power(X_normal - predictions, 2), axis=(1, 2))
        self.threshold = np.percentile(mse, percentile)
        return self.threshold
    
    def predict(self, X):
        """
        Predict anomalies based on reconstruction error
        """
        predictions = self.model.predict(X)
        mse = np.mean(np.power(X - predictions, 2), axis=(1, 2))
        anomalies = mse > self.threshold
        return anomalies, mse
    
    def save(self, model_path, threshold_path=None):
        """Save model and threshold"""
        self.model.save(model_path)
        if threshold_path and self.threshold is not None:
            np.save(threshold_path, self.threshold)
    
    def load(self, model_path, threshold_path=None):
        """Load model and threshold"""
        self.model = keras.models.load_model(model_path)
        if threshold_path and os.path.exists(threshold_path):
            self.threshold = np.load(threshold_path)


def plot_training_history(history):
    """
    Plot training history
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
    
    # Loss
    ax1.plot(history.history['loss'], label='Training Loss')
    ax1.plot(history.history['val_loss'], label='Validation Loss')
    ax1.set_title('Model Loss')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss')
    ax1.legend()
    ax1.grid(True)
    
    # MAE
    ax2.plot(history.history['mae'], label='Training MAE')
    ax2.plot(history.history['val_mae'], label='Validation MAE')
    ax2.set_title('Model MAE')
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('MAE')
    ax2.legend()
    ax2.grid(True)
    
    plt.tight_layout()
    plt.savefig('models/training_history.png')
    print("Training history plot saved to models/training_history.png")


def main(args):
    """
    Main training function
    """
    print("🚀 Training LSTM Autoencoder for Health Anomaly Detection\n")
    
    # Create directories
    os.makedirs('models/saved_models', exist_ok=True)
    os.makedirs('models/checkpoints', exist_ok=True)
    
    # Load data
    print("1. Loading data...")
    df = pd.read_csv(args.data)
    print(f"   Loaded {len(df)} samples")
    
    # Preprocessing
    print("\n2. Preprocessing data...")
    preprocessor = HealthDataPreprocessor()
    df_processed = preprocessor.preprocess(df, fit=True)
    preprocessor.save('models/preprocessor.pkl')
    
    # Create sequences
    print(f"\n3. Creating sequences (length={args.sequence_length})...")
    X, y = preprocessor.create_sequences(df_processed, sequence_length=args.sequence_length)
    print(f"   Created {len(X)} sequences with shape {X.shape}")
    
    # Split data - use only normal data for training
    if y is not None:
        # Separate normal and anomalous data
        normal_indices = np.where(y == 0)[0]
        anomaly_indices = np.where(y == 1)[0]
        
        X_normal = X[normal_indices]
        X_anomaly = X[anomaly_indices]
        
        print(f"\n   Normal sequences: {len(X_normal)}")
        print(f"   Anomalous sequences: {len(X_anomaly)}")
        
        # Split normal data into train/val
        X_train, X_val = train_test_split(X_normal, test_size=0.2, random_state=42)
    else:
        X_train, X_val = train_test_split(X, test_size=0.2, random_state=42)
    
    print(f"\n   Training samples: {len(X_train)}")
    print(f"   Validation samples: {len(X_val)}")
    
    # Build and train model
    print(f"\n4. Building LSTM Autoencoder...")
    autoencoder = LSTMAutoencoder(
        sequence_length=args.sequence_length,
        n_features=X.shape[2],
        encoding_dim=args.encoding_dim
    )
    autoencoder.build_model()
    autoencoder.model.summary()
    
    print(f"\n5. Training model (epochs={args.epochs}, batch_size={args.batch_size})...")
    history = autoencoder.train(
        X_train, X_val,
        epochs=args.epochs,
        batch_size=args.batch_size
    )
    
    # Calculate threshold
    print("\n6. Calculating anomaly threshold...")
    threshold = autoencoder.calculate_threshold(X_val, percentile=95)
    print(f"   Threshold (95th percentile): {threshold:.6f}")
    
    # Evaluate on test data (if anomalies available)
    if y is not None and len(X_anomaly) > 0:
        print("\n7. Evaluating on test data...")
        
        # Predict on validation set
        val_anomalies, val_errors = autoencoder.predict(X_val)
        print(f"   Validation - Detected anomalies: {np.sum(val_anomalies)} / {len(X_val)}")
        
        # Predict on anomalous data
        anomaly_predictions, anomaly_errors = autoencoder.predict(X_anomaly)
        detected_anomalies = np.sum(anomaly_predictions)
        print(f"   Test - Detected anomalies: {detected_anomalies} / {len(X_anomaly)}")
        print(f"   Detection rate: {detected_anomalies / len(X_anomaly) * 100:.2f}%")
    
    # Save model
    print("\n8. Saving model...")
    autoencoder.save(
        args.output,
        threshold_path=args.output.replace('.h5', '_threshold.npy')
    )
    print(f"   Model saved to {args.output}")
    
    # Plot training history
    plot_training_history(history)
    
    print("\n✅ Training complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Train LSTM Autoencoder for health anomaly detection')
    parser.add_argument('--data', type=str, default='data/processed/health_metrics.csv',
                       help='Path to training data CSV')
    parser.add_argument('--output', type=str, default='models/saved_models/lstm_autoencoder.h5',
                       help='Path to save trained model')
    parser.add_argument('--sequence-length', type=int, default=60,
                       help='Length of input sequences')
    parser.add_argument('--encoding-dim', type=int, default=32,
                       help='Dimension of encoding layer')
    parser.add_argument('--epochs', type=int, default=100,
                       help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=32,
                       help='Batch size for training')
    
    args = parser.parse_args()
    main(args)

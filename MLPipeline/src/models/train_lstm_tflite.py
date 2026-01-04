"""
Train a minimal LSTM autoencoder on synthetic heart/steps/calories/distance data
and export to TensorFlow Lite for on-device anomaly scoring.

Usage:
  python train_lstm_tflite.py \
    --epochs 5 \
    --seq-len 10 \
    --out-dir models/tflite

Outputs:
  models/tflite/anomaly_lstm.tflite
  models/tflite/anomaly_lstm.h5 (Keras)
  models/tflite/anomaly_lstm_signature.json (input/output metadata)

This is a lightweight reference; tune architecture/hyperparams as needed.
"""
import argparse
import json
import os
import numpy as np
import tensorflow as tf


def make_synthetic(seq_len: int, n_normal: int = 5000, n_anom: int = 500):
    rng = np.random.default_rng(42)
    # Normal patterns
    hr = rng.normal(75, 10, size=(n_normal, seq_len, 1)).clip(45, 140)
    steps = rng.normal(120, 50, size=(n_normal, seq_len, 1)).clip(0, 400)
    calories = rng.normal(30, 10, size=(n_normal, seq_len, 1)).clip(5, 80)
    distance = rng.normal(0.2, 0.1, size=(n_normal, seq_len, 1)).clip(0, 0.8)
    normal = np.concatenate([hr, steps, calories, distance], axis=-1)

    # Anomalies: high HR spikes, zero steps, odd calories
    hr_a = rng.normal(160, 15, size=(n_anom, seq_len, 1)).clip(120, 200)
    steps_a = rng.normal(10, 10, size=(n_anom, seq_len, 1)).clip(0, 80)
    calories_a = rng.normal(10, 5, size=(n_anom, seq_len, 1)).clip(0, 40)
    distance_a = rng.normal(0.05, 0.05, size=(n_anom, seq_len, 1)).clip(0, 0.2)
    anom = np.concatenate([hr_a, steps_a, calories_a, distance_a], axis=-1)

    x = np.concatenate([normal, anom], axis=0)
    rng.shuffle(x)
    return x.astype(np.float32)


def build_model(seq_len: int, feat_dim: int = 4, latent: int = 32):
    # Use a Conv1D-based sequence autoencoder to avoid TensorList/TensorArray ops
    inputs = tf.keras.Input(shape=(seq_len, feat_dim))
    x = tf.keras.layers.Conv1D(32, 3, padding='same', activation='relu')(inputs)
    x = tf.keras.layers.Conv1D(16, 3, padding='same', activation='relu')(x)
    x = tf.keras.layers.Conv1D(16, 3, padding='same', activation='relu')(x)
    x = tf.keras.layers.Conv1D(32, 3, padding='same', activation='relu')(x)
    outputs = tf.keras.layers.Conv1D(feat_dim, 3, padding='same')(x)
    model = tf.keras.Model(inputs, outputs)
    model.compile(optimizer='adam', loss='mse')
    return model


def export_tflite(model: tf.keras.Model, out_path: str, seq_len: int, feat_dim: int):
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    # Allow Select TF ops to handle TensorList/TensorArray lowering failures
    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS,
        tf.lite.OpsSet.SELECT_TF_OPS,
    ]
    # Disable experimental lowering of tensor list ops which can fail for dynamic shapes
    try:
        converter._experimental_lower_tensor_list_ops = False
    except Exception:
        # Older/newer TF builds may not expose this attribute; ignore if unavailable
        pass
    tflite_model = converter.convert()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(tflite_model)
    meta = {
        "input": {"shape": [1, seq_len, feat_dim], "dtype": "float32"},
        "output": {"shape": [1, seq_len, feat_dim], "dtype": "float32"},
        "note": "Reconstruction error should be computed on-device; higher error => anomaly"
    }
    with open(out_path.replace('.tflite', '_signature.json'), 'w') as f:
        json.dump(meta, f, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seq-len', type=int, default=10)
    parser.add_argument('--epochs', type=int, default=5)
    parser.add_argument('--batch-size', type=int, default=64)
    parser.add_argument('--out-dir', type=str, default='models/tflite')
    args = parser.parse_args()

    x = make_synthetic(args.seq_len)
    model = build_model(args.seq_len)
    model.fit(x, x, epochs=args.epochs, batch_size=args.batch_size, validation_split=0.1, verbose=2)

    os.makedirs(args.out_dir, exist_ok=True)
    keras_path = os.path.join(args.out_dir, 'anomaly_lstm.h5')
    tflite_path = os.path.join(args.out_dir, 'anomaly_lstm.tflite')
    model.save(keras_path)
    export_tflite(model, tflite_path, args.seq_len, feat_dim=4)
    print(f"Saved: {keras_path}, {tflite_path}")


if __name__ == '__main__':
    main()

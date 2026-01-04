"""
Train a small activity classifier on synthetic features and export to TFLite.
Input: single vector [heartRate, steps, calories, distance]
Output: 6-way softmax [sleep, rest, walk, run, exercise, other]

Usage (Python 3.11 with TensorFlow installed):
  python train_activity_tflite.py --epochs 5 --out-dir models/tflite

Outputs:
  models/tflite/activity_classifier.tflite
  models/tflite/activity_classifier.h5
  models/tflite/activity_classifier_labels.json
"""
import argparse
import json
import os
import numpy as np
import tensorflow as tf

LABELS = ["sleep", "rest", "walk", "run", "exercise", "other"]


def make_synthetic(n: int = 6000):
    rng = np.random.default_rng(123)
    xs = []
    ys = []
    # sleep
    hr = rng.normal(50, 8, size=n // 6)
    steps = rng.normal(5, 5, size=n // 6)
    calories = rng.normal(10, 4, size=n // 6)
    distance = rng.normal(0.05, 0.05, size=n // 6)
    xs.append(np.stack([hr, steps, calories, distance], axis=1))
    ys.append(np.full((n // 6,), 0))
    # rest
    hr = rng.normal(65, 10, size=n // 6)
    steps = rng.normal(20, 15, size=n // 6)
    calories = rng.normal(15, 5, size=n // 6)
    distance = rng.normal(0.1, 0.05, size=n // 6)
    xs.append(np.stack([hr, steps, calories, distance], axis=1))
    ys.append(np.full((n // 6,), 1))
    # walk
    hr = rng.normal(85, 12, size=n // 6)
    steps = rng.normal(120, 50, size=n // 6)
    calories = rng.normal(35, 8, size=n // 6)
    distance = rng.normal(0.4, 0.1, size=n // 6)
    xs.append(np.stack([hr, steps, calories, distance], axis=1))
    ys.append(np.full((n // 6,), 2))
    # run
    hr = rng.normal(130, 15, size=n // 6)
    steps = rng.normal(250, 80, size=n // 6)
    calories = rng.normal(60, 12, size=n // 6)
    distance = rng.normal(0.8, 0.15, size=n // 6)
    xs.append(np.stack([hr, steps, calories, distance], axis=1))
    ys.append(np.full((n // 6,), 3))
    # exercise
    hr = rng.normal(145, 18, size=n // 6)
    steps = rng.normal(200, 70, size=n // 6)
    calories = rng.normal(70, 15, size=n // 6)
    distance = rng.normal(0.6, 0.2, size=n // 6)
    xs.append(np.stack([hr, steps, calories, distance], axis=1))
    ys.append(np.full((n // 6,), 4))
    # other (noisy)
    hr = rng.normal(90, 25, size=n // 6)
    steps = rng.normal(80, 120, size=n // 6)
    calories = rng.normal(30, 20, size=n // 6)
    distance = rng.normal(0.3, 0.3, size=n // 6)
    xs.append(np.stack([hr, steps, calories, distance], axis=1))
    ys.append(np.full((n // 6,), 5))

    x = np.concatenate(xs, axis=0).astype(np.float32)
    y = np.concatenate(ys, axis=0).astype(np.int32)
    idx = rng.permutation(len(x))
    return x[idx], y[idx]


def build_model(input_dim: int = 4, num_classes: int = 6):
    inputs = tf.keras.Input(shape=(input_dim,))
    x = tf.keras.layers.Normalization()(inputs)
    x = tf.keras.layers.Dense(32, activation="relu")(x)
    x = tf.keras.layers.Dense(32, activation="relu")(x)
    outputs = tf.keras.layers.Dense(num_classes, activation="softmax")(x)
    model = tf.keras.Model(inputs, outputs)
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    return model


def export_tflite(model: tf.keras.Model, out_path: str):
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(tflite_model)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--out-dir", type=str, default="models/tflite")
    args = parser.parse_args()

    x, y = make_synthetic()
    model = build_model()
    model.fit(x, y, epochs=args.epochs, batch_size=args.batch_size, validation_split=0.1, verbose=2)

    os.makedirs(args.out_dir, exist_ok=True)
    h5_path = os.path.join(args.out_dir, "activity_classifier.h5")
    tflite_path = os.path.join(args.out_dir, "activity_classifier.tflite")
    model.save(h5_path)
    export_tflite(model, tflite_path)

    with open(os.path.join(args.out_dir, "activity_classifier_labels.json"), "w") as f:
        json.dump({"labels": LABELS}, f, indent=2)

    print(f"Saved: {h5_path}, {tflite_path}")


if __name__ == "__main__":
    main()

import argparse
import json
import os
import numpy as np
import tensorflow as tf


def load_interpreter(model_path: str) -> tf.lite.Interpreter:
    interpreter = tf.lite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    return interpreter


def run_activity_test(model_path: str):
    interpreter = load_interpreter(model_path)
    input_details = interpreter.get_input_details()[0]
    output_details = interpreter.get_output_details()[0]

    # Use a plausible feature vector near training distribution
    sample = np.array([[75.0, 120.0, 35.0, 0.4]], dtype=np.float32)
    interpreter.set_tensor(input_details["index"], sample)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details["index"])[0]
    top_idx = int(np.argmax(output))
    return {
        "input_shape": input_details["shape"].tolist(),
        "output_shape": output_details["shape"].tolist(),
        "softmax_sum": float(np.sum(output)),
        "top_class": top_idx,
        "top_score": float(output[top_idx]),
        "probs": output.tolist(),
    }


def run_anomaly_test(model_path: str, seq_len: int):
    interpreter = load_interpreter(model_path)
    input_details = interpreter.get_input_details()[0]
    output_details = interpreter.get_output_details()[0]

    # Respect dynamic shapes if present
    input_shape = input_details["shape"]
    if -1 in input_shape or input_shape[1] == 0:
        interpreter.resize_tensor_input(input_details["index"], [1, seq_len, 4])
        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()[0]
        output_details = interpreter.get_output_details()[0]
        input_shape = input_details["shape"]

    # Generate a mild-normal sequence close to training distribution
    rng = np.random.default_rng(7)
    hr = rng.normal(80, 10, size=(seq_len, 1))
    steps = rng.normal(100, 40, size=(seq_len, 1)).clip(0)
    calories = rng.normal(30, 10, size=(seq_len, 1)).clip(1)
    distance = rng.normal(0.3, 0.1, size=(seq_len, 1)).clip(0)
    sample = np.concatenate([hr, steps, calories, distance], axis=-1).astype(np.float32)
    sample = sample[np.newaxis, ...]  # add batch dim

    interpreter.set_tensor(input_details["index"], sample)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details["index"])

    # Reconstruction error per time-step, then mean
    mse = np.mean((output - sample) ** 2, axis=(1, 2))
    return {
        "input_shape": input_shape.tolist(),
        "output_shape": output_details["shape"].tolist(),
        "mse_mean": float(np.mean(mse)),
        "mse_per_batch": mse.tolist(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--activity", default="models/tflite/activity_classifier.tflite")
    parser.add_argument("--anomaly", default="models/tflite/anomaly_lstm.tflite")
    parser.add_argument("--seq-len", type=int, default=10)
    args = parser.parse_args()

    results = {
        "activity": run_activity_test(args.activity),
        "anomaly": run_anomaly_test(args.anomaly, args.seq_len),
    }
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

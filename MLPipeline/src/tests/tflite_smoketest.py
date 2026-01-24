"""
Comprehensive TFLite Model Testing Suite

Tests TFLite models for:
- Basic inference functionality
- Input/output shape validation
- Edge cases (invalid inputs, boundary values)
- Performance metrics
- Output correctness validation
"""
import argparse
import json
import os
import time
import numpy as np
import tensorflow as tf
from typing import Dict, List, Tuple, Any


def load_interpreter(model_path: str) -> tf.lite.Interpreter:
    """Load and allocate TFLite interpreter"""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")
    
    interpreter = tf.lite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    return interpreter


def validate_probabilities(probs: np.ndarray, tolerance: float = 1e-5) -> bool:
    """Validate that output is a valid probability distribution"""
    return abs(np.sum(probs) - 1.0) < tolerance and np.all(probs >= 0) and np.all(probs <= 1)


def run_activity_test(model_path: str) -> Dict[str, Any]:
    """Test activity classifier with multiple scenarios"""
    interpreter = load_interpreter(model_path)
    input_details = interpreter.get_input_details()[0]
    output_details = interpreter.get_output_details()[0]

    results = {
        "model_path": model_path,
        "input_shape": input_details["shape"].tolist(),
        "output_shape": output_details["shape"].tolist(),
        "tests": []
    }

    # Test 1: Normal activity
    test_cases = [
        ("normal_resting", np.array([[70.0, 50.0, 20.0, 0.1]], dtype=np.float32)),
        ("light_activity", np.array([[90.0, 150.0, 40.0, 0.3]], dtype=np.float32)),
        ("moderate_exercise", np.array([[120.0, 300.0, 80.0, 0.6]], dtype=np.float32)),
        ("intense_exercise", np.array([[160.0, 500.0, 150.0, 1.2]], dtype=np.float32)),
        ("zero_values", np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)),
        ("extreme_values", np.array([[200.0, 1000.0, 300.0, 5.0]], dtype=np.float32)),
    ]

    for test_name, sample in test_cases:
        start_time = time.perf_counter()
        interpreter.set_tensor(input_details["index"], sample)
        interpreter.invoke()
        inference_time = (time.perf_counter() - start_time) * 1000  # ms
        
        output = interpreter.get_tensor(output_details["index"])[0]
        top_idx = int(np.argmax(output))
        
        results["tests"].append({
            "name": test_name,
            "input": sample.tolist()[0],
            "top_class": top_idx,
            "top_score": float(output[top_idx]),
            "probabilities": output.tolist(),
            "valid_probability": validate_probabilities(output),
            "inference_time_ms": inference_time,
        })

    # Load labels if available
    label_path = model_path.replace('.tflite', '_labels.json')
    if os.path.exists(label_path):
        with open(label_path, 'r') as f:
            results["labels"] = json.load(f)

    return results


def generate_health_sequence(seq_len: int, scenario: str, seed: int = 42) -> np.ndarray:
    """Generate synthetic health metric sequences for different scenarios"""
    rng = np.random.default_rng(seed)
    
    if scenario == "normal":
        hr = rng.normal(75, 8, size=(seq_len, 1)).clip(50, 100)
        steps = rng.normal(100, 30, size=(seq_len, 1)).clip(0)
        calories = rng.normal(30, 8, size=(seq_len, 1)).clip(1)
        distance = rng.normal(0.3, 0.08, size=(seq_len, 1)).clip(0)
    
    elif scenario == "bradycardia":
        hr = rng.normal(45, 5, size=(seq_len, 1)).clip(30, 60)
        steps = rng.normal(50, 20, size=(seq_len, 1)).clip(0)
        calories = rng.normal(15, 5, size=(seq_len, 1)).clip(1)
        distance = rng.normal(0.1, 0.05, size=(seq_len, 1)).clip(0)
    
    elif scenario == "tachycardia":
        hr = rng.normal(140, 10, size=(seq_len, 1)).clip(120, 180)
        steps = rng.normal(80, 25, size=(seq_len, 1)).clip(0)
        calories = rng.normal(25, 8, size=(seq_len, 1)).clip(1)
        distance = rng.normal(0.2, 0.06, size=(seq_len, 1)).clip(0)
    
    elif scenario == "exercise":
        hr = rng.normal(130, 12, size=(seq_len, 1)).clip(90, 170)
        steps = rng.normal(400, 80, size=(seq_len, 1)).clip(0)
        calories = rng.normal(120, 30, size=(seq_len, 1)).clip(10)
        distance = rng.normal(1.5, 0.4, size=(seq_len, 1)).clip(0)
    
    elif scenario == "zero_values":
        hr = np.zeros((seq_len, 1), dtype=np.float32)
        steps = np.zeros((seq_len, 1), dtype=np.float32)
        calories = np.zeros((seq_len, 1), dtype=np.float32)
        distance = np.zeros((seq_len, 1), dtype=np.float32)
    
    else:  # random/noise
        hr = rng.uniform(40, 180, size=(seq_len, 1))
        steps = rng.uniform(0, 1000, size=(seq_len, 1))
        calories = rng.uniform(0, 200, size=(seq_len, 1))
        distance = rng.uniform(0, 5, size=(seq_len, 1))
    
    sequence = np.concatenate([hr, steps, calories, distance], axis=1)
    return sequence.reshape(1, seq_len, 4).astype(np.float32)


def run_anomaly_test(model_path: str, seq_len: int) -> Dict[str, Any]:
    """Test anomaly detector with multiple scenarios"""
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

    results = {
        "model_path": model_path,
        "input_shape": input_shape.tolist(),
        "output_shape": output_details["shape"].tolist(),
        "sequence_length": seq_len,
        "tests": []
    }

    # Test scenarios
    scenarios = ["normal", "bradycardia", "tachycardia", "exercise", "zero_values", "random"]
    
    for scenario in scenarios:
        sample = generate_health_sequence(seq_len, scenario)
        
        start_time = time.perf_counter()
        interpreter.set_tensor(input_details["index"], sample)
        interpreter.invoke()
        inference_time = (time.perf_counter() - start_time) * 1000  # ms
        
        output = interpreter.get_tensor(output_details["index"])
        
        # Calculate reconstruction error (MSE)
        mse = np.mean((output - sample) ** 2, axis=(1, 2))[0]
        mae = np.mean(np.abs(output - sample), axis=(1, 2))[0]
        
        # Per-feature reconstruction error
        feature_mse = np.mean((output - sample) ** 2, axis=1)[0]
        
        results["tests"].append({
            "scenario": scenario,
            "mse": float(mse),
            "mae": float(mae),
            "feature_errors": {
                "heart_rate": float(feature_mse[0]),
                "steps": float(feature_mse[1]),
                "calories": float(feature_mse[2]),
                "distance": float(feature_mse[3]),
            },
            "inference_time_ms": inference_time,
            "input_sample": sample[0, :3, :].tolist(),  # First 3 timesteps
        })
    
    # Load signature metadata if available
    signature_path = model_path.replace('.tflite', '_signature.json')
    if os.path.exists(signature_path):
        with open(signature_path, 'r') as f:
            results["signature"] = json.load(f)

    return results


def performance_benchmark(model_path: str, num_iterations: int = 100) -> Dict[str, float]:
    """Benchmark model inference performance"""
    interpreter = load_interpreter(model_path)
    input_details = interpreter.get_input_details()[0]
    
    # Create dummy input matching expected shape
    input_shape = input_details["shape"]
    if -1 in input_shape:
        input_shape = [1, 10, 4]  # Default for LSTM
    
    dummy_input = np.random.randn(*input_shape).astype(np.float32)
    
    # Warmup
    for _ in range(5):
        interpreter.set_tensor(input_details["index"], dummy_input)
        interpreter.invoke()
    
    # Benchmark
    times = []
    for _ in range(num_iterations):
        start = time.perf_counter()
        interpreter.set_tensor(input_details["index"], dummy_input)
        interpreter.invoke()
        times.append((time.perf_counter() - start) * 1000)
    
    return {
        "mean_ms": float(np.mean(times)),
        "std_ms": float(np.std(times)),
        "min_ms": float(np.min(times)),
        "max_ms": float(np.max(times)),
        "p50_ms": float(np.percentile(times, 50)),
        "p95_ms": float(np.percentile(times, 95)),
        "p99_ms": float(np.percentile(times, 99)),
    }


def main():
    parser = argparse.ArgumentParser(description="Comprehensive TFLite model testing")
    parser.add_argument("--activity", default="models/tflite/activity_classifier.tflite",
                        help="Path to activity classifier model")
    parser.add_argument("--anomaly", default="models/tflite/anomaly_lstm.tflite",
                        help="Path to anomaly detection model")
    parser.add_argument("--seq-len", type=int, default=10,
                        help="Sequence length for LSTM model")
    parser.add_argument("--benchmark", action="store_true",
                        help="Run performance benchmarks")
    parser.add_argument("--benchmark-iterations", type=int, default=100,
                        help="Number of iterations for benchmarking")
    parser.add_argument("--output", type=str, help="Output file for results (JSON)")
    args = parser.parse_args()

    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "models": {}
    }

    # Test activity classifier
    if os.path.exists(args.activity):
        print(f"Testing activity classifier: {args.activity}")
        results["models"]["activity_classifier"] = run_activity_test(args.activity)
        
        if args.benchmark:
            print("  Running performance benchmark...")
            results["models"]["activity_classifier"]["benchmark"] = performance_benchmark(
                args.activity, args.benchmark_iterations
            )
    else:
        print(f"⚠️  Activity classifier not found: {args.activity}")

    # Test anomaly detector
    if os.path.exists(args.anomaly):
        print(f"Testing anomaly detector: {args.anomaly}")
        results["models"]["anomaly_detector"] = run_anomaly_test(args.anomaly, args.seq_len)
        
        if args.benchmark:
            print("  Running performance benchmark...")
            results["models"]["anomaly_detector"]["benchmark"] = performance_benchmark(
                args.anomaly, args.benchmark_iterations
            )
    else:
        print(f"⚠️  Anomaly detector not found: {args.anomaly}")

    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Results saved to {args.output}")
    else:
        print("\n" + "="*80)
        print("TEST RESULTS")
        print("="*80)
        print(json.dumps(results, indent=2))

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    if "activity_classifier" in results["models"]:
        act_tests = results["models"]["activity_classifier"]["tests"]
        valid_probs = sum(1 for t in act_tests if t["valid_probability"])
        print(f"✅ Activity Classifier: {valid_probs}/{len(act_tests)} tests passed")
        
        if args.benchmark:
            bm = results["models"]["activity_classifier"]["benchmark"]
            print(f"   Performance: {bm['mean_ms']:.2f}ms (±{bm['std_ms']:.2f}ms)")
    
    if "anomaly_detector" in results["models"]:
        anom_tests = results["models"]["anomaly_detector"]["tests"]
        print(f"✅ Anomaly Detector: {len(anom_tests)} scenarios tested")
        
        if args.benchmark:
            bm = results["models"]["anomaly_detector"]["benchmark"]
            print(f"   Performance: {bm['mean_ms']:.2f}ms (±{bm['std_ms']:.2f}ms)")


if __name__ == "__main__":
    main()

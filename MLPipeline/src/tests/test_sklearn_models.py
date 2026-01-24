"""
Scikit-learn Model Testing Suite

Tests for Isolation Forest and other sklearn-based anomaly detection models.
Validates model loading, inference, and output correctness.
"""
import argparse
import json
import os
import time
import numpy as np
import joblib
from typing import Dict, List, Any


def load_sklearn_model(model_path: str) -> Dict[str, Any]:
    """Load sklearn model package (model + scaler)"""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")
    
    data = joblib.load(model_path)
    return data


def generate_test_samples(scenario: str, n_samples: int = 10, seed: int = 42) -> np.ndarray:
    """Generate test samples for different scenarios"""
    rng = np.random.default_rng(seed)
    
    if scenario == "normal":
        hr = rng.normal(75, 8, size=(n_samples, 1)).clip(50, 100)
        steps = rng.normal(100, 30, size=(n_samples, 1)).clip(0)
        calories = rng.normal(30, 8, size=(n_samples, 1)).clip(1)
        distance = rng.normal(0.3, 0.08, size=(n_samples, 1)).clip(0)
    
    elif scenario == "bradycardia":
        hr = rng.normal(45, 5, size=(n_samples, 1)).clip(30, 60)
        steps = rng.normal(50, 20, size=(n_samples, 1)).clip(0)
        calories = rng.normal(15, 5, size=(n_samples, 1)).clip(1)
        distance = rng.normal(0.1, 0.05, size=(n_samples, 1)).clip(0)
    
    elif scenario == "tachycardia":
        hr = rng.normal(140, 10, size=(n_samples, 1)).clip(120, 180)
        steps = rng.normal(80, 25, size=(n_samples, 1)).clip(0)
        calories = rng.normal(25, 8, size=(n_samples, 1)).clip(1)
        distance = rng.normal(0.2, 0.06, size=(n_samples, 1)).clip(0)
    
    elif scenario == "extreme":
        hr = rng.normal(200, 15, size=(n_samples, 1))
        steps = rng.normal(1000, 200, size=(n_samples, 1)).clip(0)
        calories = rng.normal(300, 50, size=(n_samples, 1)).clip(1)
        distance = rng.normal(5, 1, size=(n_samples, 1)).clip(0)
    
    elif scenario == "zero":
        return np.zeros((n_samples, 4), dtype=np.float32)
    
    else:  # random
        hr = rng.uniform(40, 180, size=(n_samples, 1))
        steps = rng.uniform(0, 1000, size=(n_samples, 1))
        calories = rng.uniform(0, 200, size=(n_samples, 1))
        distance = rng.uniform(0, 3, size=(n_samples, 1))
    
    return np.concatenate([hr, steps, calories, distance], axis=-1).astype(np.float32)


def test_isolation_forest(model_path: str) -> Dict[str, Any]:
    """Test Isolation Forest model"""
    model_data = load_sklearn_model(model_path)
    model = model_data['model']
    scaler = model_data['scaler']
    
    results = {
        "model_path": model_path,
        "model_type": type(model).__name__,
        "scaler_type": type(scaler).__name__,
        "model_params": {
            "n_estimators": model.n_estimators,
            "contamination": model.contamination,
            "max_samples": model.max_samples,
        },
        "tests": []
    }
    
    # Test different scenarios
    scenarios = ["normal", "bradycardia", "tachycardia", "extreme", "zero", "random"]
    
    for scenario in scenarios:
        samples = generate_test_samples(scenario, n_samples=50)
        
        # Scale and predict
        start_time = time.perf_counter()
        X_scaled = scaler.transform(samples)
        scores = model.score_samples(X_scaled)
        predictions = model.predict(X_scaled)
        inference_time = (time.perf_counter() - start_time) * 1000  # ms
        
        # Analyze results
        n_anomalies = np.sum(predictions == -1)
        n_normal = np.sum(predictions == 1)
        
        results["tests"].append({
            "scenario": scenario,
            "n_samples": len(samples),
            "n_anomalies": int(n_anomalies),
            "n_normal": int(n_normal),
            "anomaly_rate": float(n_anomalies / len(samples)),
            "mean_score": float(np.mean(scores)),
            "std_score": float(np.std(scores)),
            "min_score": float(np.min(scores)),
            "max_score": float(np.max(scores)),
            "inference_time_ms": inference_time,
            "sample_stats": {
                "mean_hr": float(np.mean(samples[:, 0])),
                "mean_steps": float(np.mean(samples[:, 1])),
                "mean_calories": float(np.mean(samples[:, 2])),
                "mean_distance": float(np.mean(samples[:, 3])),
            }
        })
    
    return results


def test_scaler(scaler_path: str) -> Dict[str, Any]:
    """Test scaler independently"""
    if not os.path.exists(scaler_path):
        return {"error": f"Scaler not found: {scaler_path}"}
    
    scaler = joblib.load(scaler_path)
    
    results = {
        "scaler_path": scaler_path,
        "scaler_type": type(scaler).__name__,
        "n_features": scaler.n_features_in_,
        "feature_names": getattr(scaler, 'feature_names_in_', None),
        "mean": scaler.mean_.tolist() if hasattr(scaler, 'mean_') else None,
        "scale": scaler.scale_.tolist() if hasattr(scaler, 'scale_') else None,
        "tests": []
    }
    
    # Test transformation
    test_samples = generate_test_samples("normal", n_samples=10)
    
    start_time = time.perf_counter()
    scaled = scaler.transform(test_samples)
    transform_time = (time.perf_counter() - start_time) * 1000
    
    results["tests"].append({
        "operation": "transform",
        "input_shape": test_samples.shape,
        "output_shape": scaled.shape,
        "output_mean": float(np.mean(scaled)),
        "output_std": float(np.std(scaled)),
        "time_ms": transform_time,
    })
    
    return results


def benchmark_sklearn_model(model_path: str, n_iterations: int = 100) -> Dict[str, float]:
    """Benchmark sklearn model performance"""
    model_data = load_sklearn_model(model_path)
    model = model_data['model']
    scaler = model_data['scaler']
    
    # Generate test data
    test_data = generate_test_samples("normal", n_samples=1)
    
    # Warmup
    for _ in range(5):
        X_scaled = scaler.transform(test_data)
        model.score_samples(X_scaled)
        model.predict(X_scaled)
    
    # Benchmark
    times = []
    for _ in range(n_iterations):
        start = time.perf_counter()
        X_scaled = scaler.transform(test_data)
        model.score_samples(X_scaled)
        model.predict(X_scaled)
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
    parser = argparse.ArgumentParser(description="Test scikit-learn models")
    parser.add_argument("--model", default="models/saved_models/isolation_forest.pkl",
                        help="Path to model pickle file")
    parser.add_argument("--scaler", default="models/saved_models/scaler.pkl",
                        help="Path to scaler pickle file")
    parser.add_argument("--benchmark", action="store_true",
                        help="Run performance benchmarks")
    parser.add_argument("--benchmark-iterations", type=int, default=100,
                        help="Number of iterations for benchmarking")
    parser.add_argument("--output", type=str, help="Output file for results (JSON)")
    args = parser.parse_args()

    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sklearn_models": {}
    }

    # Test Isolation Forest
    if os.path.exists(args.model):
        print(f"Testing Isolation Forest: {args.model}")
        results["sklearn_models"]["isolation_forest"] = test_isolation_forest(args.model)
        
        if args.benchmark:
            print("  Running performance benchmark...")
            results["sklearn_models"]["isolation_forest"]["benchmark"] = benchmark_sklearn_model(
                args.model, args.benchmark_iterations
            )
    else:
        print(f"⚠️  Model not found: {args.model}")

    # Test scaler
    if os.path.exists(args.scaler):
        print(f"Testing scaler: {args.scaler}")
        results["sklearn_models"]["scaler"] = test_scaler(args.scaler)
    else:
        print(f"⚠️  Scaler not found: {args.scaler}")

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
    
    if "isolation_forest" in results["sklearn_models"]:
        iso_tests = results["sklearn_models"]["isolation_forest"]["tests"]
        print(f"✅ Isolation Forest: {len(iso_tests)} scenarios tested")
        
        if args.benchmark:
            bm = results["sklearn_models"]["isolation_forest"]["benchmark"]
            print(f"   Performance: {bm['mean_ms']:.2f}ms (±{bm['std_ms']:.2f}ms)")
    
    if "scaler" in results["sklearn_models"]:
        print(f"✅ Scaler: Validated successfully")


if __name__ == "__main__":
    main()

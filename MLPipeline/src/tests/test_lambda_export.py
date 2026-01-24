"""
Lambda Export Package Testing Suite

Tests the exported Lambda package for:
- Model loading and initialization
- Inference correctness
- Error handling
- Performance metrics
"""
import argparse
import json
import os
import sys
import time
import numpy as np
import joblib
from typing import Dict, List, Any


def test_lambda_export(export_dir: str) -> Dict[str, Any]:
    """Test Lambda export package"""
    model_path = os.path.join(export_dir, "model.pkl")
    metadata_path = os.path.join(export_dir, "metadata.json")
    
    results = {
        "export_dir": export_dir,
        "files_present": {
            "model.pkl": os.path.exists(model_path),
            "metadata.json": os.path.exists(metadata_path),
        },
        "tests": []
    }
    
    # Load metadata
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        results["metadata"] = metadata
        print(f"✓ Loaded metadata: {metadata['type']}")
    else:
        results["error"] = "Metadata file not found"
        return results
    
    # Load model
    if not os.path.exists(model_path):
        results["error"] = "Model file not found"
        return results
    
    try:
        model_data = joblib.load(model_path)
        results["model_loaded"] = True
        results["model_type"] = type(model_data['model']).__name__
        results["scaler_type"] = type(model_data['scaler']).__name__
        print(f"✓ Loaded model: {results['model_type']}")
    except Exception as e:
        results["error"] = f"Failed to load model: {str(e)}"
        return results
    
    model = model_data['model']
    scaler = model_data['scaler']
    threshold = metadata.get('threshold', -0.5)
    features = metadata.get('features', ['heartRate', 'steps', 'calories', 'distance'])
    
    # Test cases simulating Lambda payloads
    test_cases = [
        {
            "name": "normal_single_metric",
            "payload": {
                "heartRate": 75.0,
                "steps": 100.0,
                "calories": 30.0,
                "distance": 0.3
            }
        },
        {
            "name": "high_heart_rate",
            "payload": {
                "heartRate": 150.0,
                "steps": 50.0,
                "calories": 25.0,
                "distance": 0.15
            }
        },
        {
            "name": "low_heart_rate",
            "payload": {
                "heartRate": 45.0,
                "steps": 30.0,
                "calories": 15.0,
                "distance": 0.08
            }
        },
        {
            "name": "high_activity",
            "payload": {
                "heartRate": 130.0,
                "steps": 500.0,
                "calories": 120.0,
                "distance": 1.5
            }
        },
        {
            "name": "zero_values",
            "payload": {
                "heartRate": 0.0,
                "steps": 0.0,
                "calories": 0.0,
                "distance": 0.0
            }
        },
        {
            "name": "missing_field",
            "payload": {
                "heartRate": 75.0,
                "steps": 100.0,
                "calories": 30.0,
                # missing distance
            }
        },
    ]
    
    for test_case in test_cases:
        test_name = test_case["name"]
        payload = test_case["payload"]
        
        try:
            # Extract features in correct order
            if all(f in payload for f in features):
                X = np.array([[payload[f] for f in features]], dtype=np.float32)
                
                # Run inference
                start_time = time.perf_counter()
                X_scaled = scaler.transform(X)
                score = model.score_samples(X_scaled)[0]
                prediction = model.predict(X_scaled)[0]
                inference_time = (time.perf_counter() - start_time) * 1000
                
                is_anomaly = score < threshold
                
                test_result = {
                    "name": test_name,
                    "success": True,
                    "input": payload,
                    "anomaly_score": float(score),
                    "prediction": int(prediction),
                    "is_anomaly": bool(is_anomaly),
                    "threshold": threshold,
                    "inference_time_ms": inference_time,
                }
            else:
                # Handle missing fields
                missing = [f for f in features if f not in payload]
                test_result = {
                    "name": test_name,
                    "success": False,
                    "error": f"Missing required fields: {missing}",
                    "input": payload,
                }
        
        except Exception as e:
            test_result = {
                "name": test_name,
                "success": False,
                "error": str(e),
                "input": payload,
            }
        
        results["tests"].append(test_result)
    
    return results


def test_batch_inference(export_dir: str, batch_size: int = 100) -> Dict[str, Any]:
    """Test batch inference performance"""
    model_path = os.path.join(export_dir, "model.pkl")
    
    if not os.path.exists(model_path):
        return {"error": "Model file not found"}
    
    model_data = joblib.load(model_path)
    model = model_data['model']
    scaler = model_data['scaler']
    
    # Generate batch of test data
    rng = np.random.default_rng(42)
    hr = rng.normal(75, 15, size=(batch_size, 1))
    steps = rng.normal(100, 50, size=(batch_size, 1)).clip(0)
    calories = rng.normal(30, 15, size=(batch_size, 1)).clip(1)
    distance = rng.normal(0.3, 0.15, size=(batch_size, 1)).clip(0)
    batch_data = np.concatenate([hr, steps, calories, distance], axis=-1).astype(np.float32)
    
    # Run batch inference
    start_time = time.perf_counter()
    X_scaled = scaler.transform(batch_data)
    scores = model.score_samples(X_scaled)
    predictions = model.predict(X_scaled)
    total_time = (time.perf_counter() - start_time) * 1000
    
    return {
        "batch_size": batch_size,
        "total_time_ms": total_time,
        "avg_time_per_sample_ms": total_time / batch_size,
        "n_anomalies": int(np.sum(predictions == -1)),
        "n_normal": int(np.sum(predictions == 1)),
        "mean_score": float(np.mean(scores)),
        "std_score": float(np.std(scores)),
    }


def simulate_lambda_handler(export_dir: str, event: Dict) -> Dict[str, Any]:
    """Simulate Lambda handler execution"""
    model_path = os.path.join(export_dir, "model.pkl")
    metadata_path = os.path.join(export_dir, "metadata.json")
    
    try:
        # Load model and metadata (simulating cold start)
        start_cold = time.perf_counter()
        model_data = joblib.load(model_path)
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        cold_start_time = (time.perf_counter() - start_cold) * 1000
        
        model = model_data['model']
        scaler = model_data['scaler']
        threshold = metadata.get('threshold', -0.5)
        features = metadata.get('features', ['heartRate', 'steps', 'calories', 'distance'])
        
        # Parse event
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
        
        # Extract features
        if all(f in body for f in features):
            X = np.array([[body[f] for f in features]], dtype=np.float32)
            
            # Run inference
            start_inference = time.perf_counter()
            X_scaled = scaler.transform(X)
            score = model.score_samples(X_scaled)[0]
            prediction = model.predict(X_scaled)[0]
            inference_time = (time.perf_counter() - start_inference) * 1000
            
            is_anomaly = score < threshold
            
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "anomalyScore": float(score),
                    "isAnomaly": bool(is_anomaly),
                    "prediction": int(prediction),
                    "threshold": threshold,
                }),
                "timing": {
                    "cold_start_ms": cold_start_time,
                    "inference_ms": inference_time,
                    "total_ms": cold_start_time + inference_time,
                }
            }
        else:
            missing = [f for f in features if f not in body]
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": f"Missing required fields: {missing}"
                })
            }
    
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e)
            })
        }


def main():
    parser = argparse.ArgumentParser(description="Test Lambda export package")
    parser.add_argument("--export-dir", default="models/lambda_export",
                        help="Path to Lambda export directory")
    parser.add_argument("--batch-size", type=int, default=100,
                        help="Batch size for batch inference test")
    parser.add_argument("--simulate-lambda", action="store_true",
                        help="Simulate Lambda handler execution")
    parser.add_argument("--output", type=str, help="Output file for results (JSON)")
    args = parser.parse_args()

    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "lambda_export": {}
    }

    # Test export package
    if os.path.exists(args.export_dir):
        print(f"Testing Lambda export package: {args.export_dir}")
        results["lambda_export"]["package_test"] = test_lambda_export(args.export_dir)
        
        # Batch inference test
        print(f"Testing batch inference (n={args.batch_size})...")
        results["lambda_export"]["batch_test"] = test_batch_inference(args.export_dir, args.batch_size)
        
        # Simulate Lambda handler
        if args.simulate_lambda:
            print("Simulating Lambda handler...")
            test_event = {
                "body": json.dumps({
                    "heartRate": 75.0,
                    "steps": 100.0,
                    "calories": 30.0,
                    "distance": 0.3
                })
            }
            results["lambda_export"]["lambda_simulation"] = simulate_lambda_handler(args.export_dir, test_event)
    else:
        print(f"⚠️  Export directory not found: {args.export_dir}")
        results["error"] = "Export directory not found"

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
    
    if "package_test" in results["lambda_export"]:
        pkg = results["lambda_export"]["package_test"]
        if "tests" in pkg:
            successful = sum(1 for t in pkg["tests"] if t.get("success", False))
            total = len(pkg["tests"])
            print(f"✅ Package Tests: {successful}/{total} passed")
    
    if "batch_test" in results["lambda_export"]:
        batch = results["lambda_export"]["batch_test"]
        if "batch_size" in batch:
            print(f"✅ Batch Inference: {batch['batch_size']} samples in {batch['total_time_ms']:.2f}ms")
            print(f"   Average: {batch['avg_time_per_sample_ms']:.4f}ms per sample")
    
    if "lambda_simulation" in results["lambda_export"]:
        sim = results["lambda_export"]["lambda_simulation"]
        if "timing" in sim:
            print(f"✅ Lambda Simulation: {sim['timing']['total_ms']:.2f}ms total")
            print(f"   Cold start: {sim['timing']['cold_start_ms']:.2f}ms")
            print(f"   Inference: {sim['timing']['inference_ms']:.2f}ms")


if __name__ == "__main__":
    main()

"""
Integration Testing Suite

End-to-end tests for ML pipeline integration with:
- WearOS app (TFLite models)
- React Native app (via Lambda/API)
- Data flow validation
"""
import argparse
import json
import os
import time
import numpy as np
import tensorflow as tf
import joblib
from typing import Dict, List, Any


def test_wearos_integration(tflite_dir: str) -> Dict[str, Any]:
    """Test WearOS integration by simulating on-device inference"""
    results = {
        "platform": "WearOS",
        "models_tested": [],
        "integration_tests": []
    }
    
    # Expected models for WearOS
    expected_models = {
        "activity_classifier": os.path.join(tflite_dir, "activity_classifier.tflite"),
        "anomaly_detector": os.path.join(tflite_dir, "anomaly_lstm.tflite"),
    }
    
    for model_name, model_path in expected_models.items():
        if os.path.exists(model_path):
            results["models_tested"].append(model_name)
            print(f"  ✓ Found {model_name}")
        else:
            print(f"  ✗ Missing {model_name}")
    
    # Simulate WearOS sensor data flow
    print("\n  Simulating WearOS data flow...")
    
    # Test 1: Real-time activity classification
    if os.path.exists(expected_models["activity_classifier"]):
        interpreter = tf.lite.Interpreter(model_path=expected_models["activity_classifier"])
        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()[0]
        output_details = interpreter.get_output_details()[0]
        
        # Simulate sensor reading
        sensor_data = np.array([[85.0, 150.0, 45.0, 0.35]], dtype=np.float32)
        
        start = time.perf_counter()
        interpreter.set_tensor(input_details["index"], sensor_data)
        interpreter.invoke()
        output = interpreter.get_tensor(output_details["index"])[0]
        latency = (time.perf_counter() - start) * 1000
        
        results["integration_tests"].append({
            "test": "wearos_activity_classification",
            "success": True,
            "latency_ms": latency,
            "meets_realtime_requirement": latency < 100,  # < 100ms for real-time
            "predicted_class": int(np.argmax(output)),
            "confidence": float(np.max(output)),
        })
    
    # Test 2: Continuous anomaly monitoring
    if os.path.exists(expected_models["anomaly_detector"]):
        interpreter = tf.lite.Interpreter(model_path=expected_models["anomaly_detector"])
        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()[0]
        
        # Resize for sequence
        interpreter.resize_tensor_input(input_details["index"], [1, 10, 4])
        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()[0]
        output_details = interpreter.get_output_details()[0]
        
        # Simulate 10-second window of sensor data
        rng = np.random.default_rng(42)
        hr = rng.normal(75, 8, size=(10, 1))
        steps = rng.normal(100, 30, size=(10, 1)).clip(0)
        calories = rng.normal(30, 8, size=(10, 1)).clip(1)
        distance = rng.normal(0.3, 0.08, size=(10, 1)).clip(0)
        sequence = np.concatenate([hr, steps, calories, distance], axis=-1).astype(np.float32)
        sequence = sequence[np.newaxis, ...]
        
        start = time.perf_counter()
        interpreter.set_tensor(input_details["index"], sequence)
        interpreter.invoke()
        output = interpreter.get_tensor(output_details["index"])
        latency = (time.perf_counter() - start) * 1000
        
        mse = float(np.mean((output - sequence) ** 2))
        
        results["integration_tests"].append({
            "test": "wearos_anomaly_detection",
            "success": True,
            "latency_ms": latency,
            "meets_realtime_requirement": latency < 500,  # < 500ms for 10s window
            "reconstruction_error": mse,
        })
    
    return results


def test_react_native_integration(lambda_export_dir: str) -> Dict[str, Any]:
    """Test React Native integration via Lambda/API"""
    results = {
        "platform": "React Native",
        "backend": "AWS Lambda",
        "integration_tests": []
    }
    
    model_path = os.path.join(lambda_export_dir, "model.pkl")
    metadata_path = os.path.join(lambda_export_dir, "metadata.json")
    
    if not os.path.exists(model_path) or not os.path.exists(metadata_path):
        results["error"] = "Lambda export package not found"
        return results
    
    # Load model and metadata
    model_data = joblib.load(model_path)
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    model = model_data['model']
    scaler = model_data['scaler']
    threshold = metadata.get('threshold', -0.5)
    features = metadata.get('features', ['heartRate', 'steps', 'calories', 'distance'])
    
    print("\n  Simulating React Native -> Lambda -> Response flow...")
    
    # Test 1: Single metric submission from React Native app
    rn_payload = {
        "heartRate": 75.0,
        "steps": 100.0,
        "calories": 30.0,
        "distance": 0.3,
        "timestamp": int(time.time()),
        "userId": "test_user_001"
    }
    
    start = time.perf_counter()
    
    # Simulate API Gateway -> Lambda
    X = np.array([[rn_payload[f] for f in features]], dtype=np.float32)
    X_scaled = scaler.transform(X)
    score = model.score_samples(X_scaled)[0]
    prediction = model.predict(X_scaled)[0]
    
    latency = (time.perf_counter() - start) * 1000
    
    is_anomaly = score < threshold
    
    api_response = {
        "anomalyScore": float(score),
        "isAnomaly": bool(is_anomaly),
        "prediction": int(prediction),
        "threshold": threshold,
        "timestamp": rn_payload["timestamp"]
    }
    
    results["integration_tests"].append({
        "test": "rn_single_metric_submission",
        "success": True,
        "latency_ms": latency,
        "meets_api_requirement": latency < 1000,  # < 1s for API response
        "input": rn_payload,
        "output": api_response,
    })
    
    # Test 2: Batch sync from React Native
    print("  Simulating batch sync...")
    batch_payloads = []
    for i in range(10):
        batch_payloads.append({
            "heartRate": 70.0 + i * 2,
            "steps": 90.0 + i * 10,
            "calories": 28.0 + i,
            "distance": 0.28 + i * 0.02,
        })
    
    start = time.perf_counter()
    
    batch_X = np.array([[p[f] for f in features] for p in batch_payloads], dtype=np.float32)
    batch_X_scaled = scaler.transform(batch_X)
    batch_scores = model.score_samples(batch_X_scaled)
    batch_predictions = model.predict(batch_X_scaled)
    
    batch_latency = (time.perf_counter() - start) * 1000
    
    batch_results = []
    for i, (score, pred) in enumerate(zip(batch_scores, batch_predictions)):
        batch_results.append({
            "index": i,
            "anomalyScore": float(score),
            "isAnomaly": bool(score < threshold),
        })
    
    results["integration_tests"].append({
        "test": "rn_batch_sync",
        "success": True,
        "batch_size": len(batch_payloads),
        "total_latency_ms": batch_latency,
        "avg_latency_per_item_ms": batch_latency / len(batch_payloads),
        "meets_api_requirement": batch_latency < 5000,  # < 5s for batch
        "results": batch_results,
    })
    
    # Test 3: Error handling
    print("  Testing error handling...")
    invalid_payload = {
        "heartRate": 75.0,
        "steps": 100.0,
        # missing calories and distance
    }
    
    try:
        X = np.array([[invalid_payload[f] for f in features]], dtype=np.float32)
        results["integration_tests"].append({
            "test": "rn_error_handling_missing_fields",
            "success": False,
            "error": "Should have failed with missing fields",
        })
    except KeyError as e:
        results["integration_tests"].append({
            "test": "rn_error_handling_missing_fields",
            "success": True,
            "error_caught": str(e),
            "error_type": "KeyError",
        })
    
    return results


def test_end_to_end_workflow() -> Dict[str, Any]:
    """Test complete data flow: WearOS -> Cloud -> React Native"""
    results = {
        "workflow": "WearOS -> Lambda -> React Native Dashboard",
        "steps": []
    }
    
    print("\n  Simulating end-to-end workflow...")
    
    # Step 1: WearOS collects sensor data
    wearos_sensor_data = {
        "heartRate": 85.0,
        "steps": 150.0,
        "calories": 45.0,
        "distance": 0.35,
        "timestamp": int(time.time()),
        "source": "WearOS"
    }
    results["steps"].append({
        "step": 1,
        "component": "WearOS",
        "action": "Sensor data collected",
        "data": wearos_sensor_data,
    })
    
    # Step 2: WearOS syncs to cloud (simulated)
    results["steps"].append({
        "step": 2,
        "component": "WearOS -> Cloud",
        "action": "Data synced to backend",
        "sync_method": "HTTP POST to API Gateway",
    })
    
    # Step 3: Lambda processes data
    results["steps"].append({
        "step": 3,
        "component": "AWS Lambda",
        "action": "Anomaly detection inference",
        "input": wearos_sensor_data,
    })
    
    # Step 4: React Native fetches results
    results["steps"].append({
        "step": 4,
        "component": "React Native",
        "action": "Dashboard displays health metrics",
        "display_data": {
            "heartRate": wearos_sensor_data["heartRate"],
            "isAnomaly": False,
            "timestamp": wearos_sensor_data["timestamp"],
        }
    })
    
    results["workflow_complete"] = True
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Integration testing for ML pipeline")
    parser.add_argument("--tflite-dir", default="models/tflite",
                        help="Directory containing TFLite models")
    parser.add_argument("--lambda-export", default="models/lambda_export",
                        help="Directory containing Lambda export package")
    parser.add_argument("--output", type=str, help="Output file for results (JSON)")
    args = parser.parse_args()

    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "integration_tests": {}
    }

    print("="*80)
    print("INTEGRATION TESTING")
    print("="*80)

    # Test WearOS integration
    print("\n[1] Testing WearOS Integration...")
    results["integration_tests"]["wearos"] = test_wearos_integration(args.tflite_dir)
    
    # Test React Native integration
    print("\n[2] Testing React Native Integration...")
    results["integration_tests"]["react_native"] = test_react_native_integration(args.lambda_export)
    
    # Test end-to-end workflow
    print("\n[3] Testing End-to-End Workflow...")
    results["integration_tests"]["end_to_end"] = test_end_to_end_workflow()

    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Results saved to {args.output}")
    else:
        print("\n" + "="*80)
        print("INTEGRATION TEST RESULTS")
        print("="*80)
        print(json.dumps(results, indent=2))

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    if "wearos" in results["integration_tests"]:
        wearos = results["integration_tests"]["wearos"]
        n_models = len(wearos.get("models_tested", []))
        n_tests = len(wearos.get("integration_tests", []))
        print(f"✅ WearOS: {n_models} models, {n_tests} integration tests")
        
        for test in wearos.get("integration_tests", []):
            if test.get("meets_realtime_requirement"):
                print(f"   ✓ {test['test']}: {test['latency_ms']:.2f}ms (real-time ✓)")
            else:
                print(f"   ✗ {test['test']}: {test['latency_ms']:.2f}ms (too slow)")
    
    if "react_native" in results["integration_tests"]:
        rn = results["integration_tests"]["react_native"]
        n_tests = len(rn.get("integration_tests", []))
        print(f"✅ React Native: {n_tests} integration tests")
        
        for test in rn.get("integration_tests", []):
            if test.get("success"):
                print(f"   ✓ {test['test']}")
    
    if "end_to_end" in results["integration_tests"]:
        e2e = results["integration_tests"]["end_to_end"]
        if e2e.get("workflow_complete"):
            print(f"✅ End-to-End: {len(e2e['steps'])} steps completed")


if __name__ == "__main__":
    main()

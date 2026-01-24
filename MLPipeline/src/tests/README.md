# ML Pipeline Test Suite

Comprehensive testing suite for all ML models in the pipeline, including TFLite models, scikit-learn models, Lambda export packages, and integration tests.

## Test Files

### 1. `tflite_smoketest.py` - TFLite Model Tests
Tests TFLite models used by WearOS app:
- **Activity Classifier**: Tests classification on various activity levels
- **LSTM Anomaly Detector**: Tests anomaly detection on different health scenarios
- **Performance Benchmarking**: Measures inference latency
- **Edge Cases**: Tests with zero values, extreme values, invalid inputs

**Usage:**
```bash
# Basic test
python src/tests/tflite_smoketest.py

# With benchmarking
python src/tests/tflite_smoketest.py --benchmark --benchmark-iterations 100

# Save results to file
python src/tests/tflite_smoketest.py --output test_results_tflite.json
```

### 2. `test_sklearn_models.py` - Scikit-learn Model Tests
Tests sklearn-based models used by Lambda backend:
- **Isolation Forest**: Tests anomaly detection across scenarios
- **Scaler**: Tests data transformation
- **Performance Metrics**: Latency and throughput measurements

**Usage:**
```bash
# Basic test
python src/tests/test_sklearn_models.py

# With benchmarking
python src/tests/test_sklearn_models.py --benchmark

# Custom model paths
python src/tests/test_sklearn_models.py \
  --model models/saved_models/isolation_forest.pkl \
  --scaler models/saved_models/scaler.pkl
```

### 3. `test_lambda_export.py` - Lambda Export Tests
Tests the exported Lambda package:
- **Package Validation**: Checks model.pkl and metadata.json
- **Inference Correctness**: Validates predictions
- **Batch Processing**: Tests batch inference performance
- **Lambda Simulation**: Simulates AWS Lambda handler execution
- **Error Handling**: Tests missing fields and invalid inputs

**Usage:**
```bash
# Basic test
python src/tests/test_lambda_export.py

# With Lambda simulation
python src/tests/test_lambda_export.py --simulate-lambda

# Custom batch size
python src/tests/test_lambda_export.py --batch-size 200
```

### 4. `test_integration.py` - Integration Tests
End-to-end integration tests:
- **WearOS Integration**: Tests on-device TFLite model inference
- **React Native Integration**: Tests API/Lambda data flow
- **End-to-End Workflow**: Tests complete data pipeline

**Usage:**
```bash
python src/tests/test_integration.py

# Custom paths
python src/tests/test_integration.py \
  --tflite-dir models/tflite \
  --lambda-export models/lambda_export
```

### 5. `run_all_tests.py` - Test Runner
Orchestrates all test suites and generates comprehensive reports.

**Usage:**
```bash
# Run all tests
python src/tests/run_all_tests.py

# With performance benchmarking
python src/tests/run_all_tests.py --benchmark

# Skip integration tests (faster)
python src/tests/run_all_tests.py --skip-integration

# Save results
python src/tests/run_all_tests.py --output test_report.json
```

## Quick Start

### Run All Tests
```bash
cd MLPipeline
python src/tests/run_all_tests.py
```

### Run Individual Test Suites
```bash
# TFLite models only
python src/tests/tflite_smoketest.py --benchmark

# Sklearn models only
python src/tests/test_sklearn_models.py --benchmark

# Lambda export only
python src/tests/test_lambda_export.py --simulate-lambda

# Integration tests only
python src/tests/test_integration.py
```

## Test Coverage

### ✅ TFLite Models
- [x] Activity classifier inference
- [x] LSTM anomaly detector inference
- [x] Multiple test scenarios (normal, bradycardia, tachycardia, exercise, etc.)
- [x] Input/output shape validation
- [x] Probability distribution validation
- [x] Performance benchmarking
- [x] Edge cases (zero values, extreme values)
- [x] Label file loading

### ✅ Sklearn Models
- [x] Isolation Forest loading and inference
- [x] Scaler validation
- [x] Multiple test scenarios
- [x] Anomaly detection accuracy
- [x] Performance benchmarking
- [x] Model parameter validation

### ✅ Lambda Export
- [x] Package structure validation
- [x] Model and metadata loading
- [x] Single metric inference
- [x] Batch processing
- [x] Lambda handler simulation
- [x] Error handling (missing fields)
- [x] Performance metrics (cold start, inference time)

### ✅ Integration Tests
- [x] WearOS on-device inference simulation
- [x] Real-time latency requirements validation
- [x] React Native API flow simulation
- [x] Batch sync testing
- [x] End-to-end workflow validation
- [x] Error handling across components

## Requirements

Install test dependencies:
```bash
pip install numpy tensorflow joblib scikit-learn
```

Or use the main requirements file:
```bash
pip install -r requirements.txt
```

## Expected Models

The tests expect the following models to be present:

```
MLPipeline/
├── models/
│   ├── tflite/
│   │   ├── activity_classifier.tflite
│   │   ├── activity_classifier_labels.json
│   │   ├── anomaly_lstm.tflite
│   │   └── anomaly_lstm_signature.json
│   ├── saved_models/
│   │   ├── isolation_forest.pkl
│   │   └── scaler.pkl
│   └── lambda_export/
│       ├── model.pkl
│       └── metadata.json
```

If models are missing, train them first:
```bash
# Train TFLite models
bash train_pipeline.sh

# Export for Lambda
bash export_for_lambda.sh
```

## Output Format

All tests output results in JSON format with:
- Timestamp
- Test results for each scenario
- Performance metrics (latency, throughput)
- Success/failure status
- Detailed error messages when applicable

Example output structure:
```json
{
  "timestamp": "2026-01-24 12:00:00",
  "models": {
    "activity_classifier": {
      "input_shape": [1, 4],
      "output_shape": [1, 6],
      "tests": [
        {
          "name": "normal_resting",
          "success": true,
          "inference_time_ms": 2.5,
          "top_class": 0,
          "confidence": 0.95
        }
      ]
    }
  }
}
```

## Performance Benchmarks

Target performance metrics:

| Model | Platform | Target Latency | Typical Performance |
|-------|----------|----------------|---------------------|
| Activity Classifier | WearOS | < 100ms | ~2-5ms |
| LSTM Anomaly | WearOS | < 500ms | ~10-20ms |
| Isolation Forest | Lambda | < 1000ms | ~0.5-2ms |
| Batch (100 samples) | Lambda | < 5000ms | ~50-100ms |

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

```bash
# Exit code 0 = all tests passed
# Exit code 1 = one or more tests failed
python src/tests/run_all_tests.py --output ci_results.json
```

## Troubleshooting

### Models Not Found
```bash
# Check if models exist
ls -la models/tflite/
ls -la models/saved_models/
ls -la models/lambda_export/

# Train models if missing
bash train_pipeline.sh
```

### Import Errors
```bash
# Install missing dependencies
pip install -r requirements.txt
```

### Test Failures
Check the detailed error output in:
- Console stderr output
- JSON output file (if using --output flag)

## Support for React Native Migration

These tests ensure compatibility with the React Native migration:

1. **Lambda API Tests**: Validate the backend API that React Native app calls
2. **Data Format Tests**: Ensure JSON payloads match React Native expectations
3. **Performance Tests**: Verify API response times meet mobile app requirements
4. **Integration Tests**: Simulate complete RN -> Lambda -> Response flow

The test suite confirms that the ML pipeline fully supports the React Native dashboard migration.

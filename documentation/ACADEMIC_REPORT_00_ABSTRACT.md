# Abstract and Executive Summary

## Abstract

This capstone project presents a real-time health monitoring system implemented on Wear OS smartwatches, designed to classify user activities and detect health anomalies using edge-first machine learning inference. The system employs two lightweight TensorFlow Lite models—an activity classifier and an LSTM autoencoder for anomaly detection—running directly on the wearable device to minimize latency and preserve user privacy. The activity classifier processes a 10×4 feature window (heart rate, steps, calories, distance) to provide contextual activity labels, while the anomaly autoencoder detects deviations from normal patterns through reconstruction error analysis. Both models are bundled as quantized TFLite assets and execute on CPU, achieving sub-200ms inference latency suitable for continuous monitoring. A rule-based fallback mechanism ensures resilience when model inference fails. The current implementation focuses on edge-only operation without cloud backend, persistent storage, or over-the-air model updates. Testing validates model loading, inference correctness, and alert triggering on synthetic anomalous windows. Future work includes cloud integration for long-term storage and retraining, OTA model delivery, extended sensor inputs (accelerometer/gyroscope/SpO2), and comprehensive performance profiling. This work demonstrates the feasibility of deploying practical anomaly detection on resource-constrained wearables while maintaining acceptable accuracy and responsiveness.

**Keywords:** Wearable computing, edge machine learning, anomaly detection, activity classification, TensorFlow Lite, Wear OS

## Executive Summary

### Objectives
- Implement real-time health monitoring on a Wear OS smartwatch using edge-deployed ML models.
- Classify user activities and detect health anomalies without relying on cloud infrastructure.
- Maintain sub-200ms inference latency suitable for responsive user alerts.
- Preserve user privacy by keeping health data on-device.

### Current Implementation
- **Platform:** Wear OS 3.5 (Samsung Galaxy Watch 4, Snapdragon Wear 4100+)
- **Languages:** Kotlin, TensorFlow Lite, Python (ML pipeline)
- **Models:** Two quantized TFLite models bundled in the app
  - Activity classifier (softmax over 6 activity states)
  - Anomaly detector (LSTM autoencoder with reconstruction error scoring)
- **Inputs:** Heart rate, steps, calories, distance (10-timestep sliding window)
- **Alerting:** Local watch notifications; no cloud notification path

### Key Findings
- Both models successfully load and infer on-device using CPU execution.
- Reconstruction error-based anomaly scoring effectively triggers alerts on synthetic anomalous patterns.
- Rule-based fallback provides robustness when model inference fails.
- No persistent storage or background sync is wired in the current build.
- Latency is acceptable for continuous monitoring; formal battery profiling is pending.

### Future Roadmap
1. **Cloud Backend & Sync:** Implement DynamoDB storage, periodic uploads, and API gateway.
2. **OTA Model Delivery:** Enable automatic model updates via S3 registry.
3. **Extended Sensing:** Add accelerometer/gyroscope/SpO2 inputs and retrain models.
4. **Personalization:** Implement on-device baseline calculation and adaptive thresholds.
5. **Testing & Profiling:** Automated unit/integration tests and battery/latency benchmarks.

### Conclusion
The edge-first health monitoring system demonstrates that practical ML-based anomaly detection is achievable on wearables with minimal computational resources. The current snapshot provides a solid foundation for future enhancements including cloud integration, expanded sensing, and personalized baselines.

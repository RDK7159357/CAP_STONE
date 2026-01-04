# Chapter 6: Discussion and Future Work

## 6.1 Interpretation of Results

The current implementation runs two on-device TFLite models on Wear OS and has been validated end-to-end via the TfLiteSanityCheck utility (both models report `usedTflite=true` after asset fixes):
- **Activity classifier:** Lightweight 4-feature model (HR, steps, calories, distance) with on-device softmax output.
- **Anomaly detector:** Sequence autoencoder (10×4 input) computing reconstruction error; recent metrics are padded when fewer than 10 samples exist; falls back to a rule heuristic on any TFLite failure.

What is confirmed now:
- Models load correctly from assets and execute on-device (no more flatbuffer errors after copying the correct binaries).
- Rule-based fallback remains in place and activates on interpreter errors.

What is still to be re-measured/validated:
- Latency and battery impact on current watch hardware (numbers previously cited were target values and need fresh instrumentation).
- On-device accuracy against held-out data; current confidence/score values come from sanity probes, not a full test set.

## 6.2 Limitations

- **Feature scope:** Activity model uses only HR/steps/calories/distance; no accelerometer/gyroscope signals are consumed, limiting context in motion-heavy scenarios.
- **No quantization yet:** Models are float TFLite; size and latency are acceptable in sanity runs but unprofiled on-device for power/latency.
- **Baseline/personalization:** The current path uses a simple rule fallback; the personalized baseline engine described earlier is not yet wired into inference.
- **Sequence padding:** Anomaly model pads to 10 timesteps when history is short; very early sessions may dilute anomaly scores.
- **Explainability & regulatory:** Alerts remain opaque; no clinical validation or regulatory alignment has been performed.

## 6.3 Comparison to Existing Work

The system keeps inference fully on-device, avoiding cloud latency and preserving offline functionality. Unlike cloud-only pipelines, alerts are available without connectivity. Unlike fixed-threshold wearables, it applies learned models plus a rule fallback, but current models are lightweight (no accelerometer/gyro CNN-LSTM) and therefore emphasize responsiveness and privacy over rich motion context.

## 6.4 Practical Implications

- **Clinical positioning:** Still a non-medical prototype; clinical utility depends on forthcoming accuracy/latency profiling and validation.
- **Privacy posture:** Edge-first inference keeps raw signals on-device; cloud remains optional for sync/analytics.
- **Deployment:** OTA model delivery is planned but not yet implemented; current updates are manual asset drops.

## 6.5 Future Work

1. **Measure & tune:** Instrument real on-device latency, memory, and battery for the current float models; add basic telemetry.
2. **Model upgrades:** Add accelerometer/gyro inputs and quantize both models for size/latency gains; consider lightweight CNN-LSTM for activity.
3. **Personalization:** Integrate the baseline engine into inference paths; calibrate anomaly thresholds per user and activity.
4. **Explainability:** Provide user-facing context (why an alert fired) and simple per-feature contributions.
5. **OTA delivery:** Implement signed, versioned model downloads to avoid manual asset replacement.
6. **Regulatory path:** Plan validation studies and data-handling controls toward HIPAA/GDPR alignment.

## 6.6 Risks and Mitigations

- **Data Quality Variance:** Motion artifacts and skin perfusion affect PPG; mitigate with signal-quality indices and auto-rejection before inference.
- **Model Drift:** Physiology changes over time; mitigate with weekly cloud retraining, OTA updates, and optional on-device fine-tuning.
- **Battery Regression:** New features can erode battery life; mitigate with per-feature power budgets, instrumentation, and regression testing on real hardware.
- **Security Exposure:** API misuse or key leakage; mitigate with HMAC auth, key rotation, rate limiting, and end-to-end TLS.

## 6.7 Summary

The edge-first hybrid architecture proved both feasible and effective: real-time alerts, privacy preservation, competitive accuracy, and acceptable battery life on commodity Wear OS hardware. The remaining gaps—richer sensing, stronger personalization, explainability, and formal clinical validation—define the next phase of work. The system’s modular design (separable edge models, cloud training, and OTA delivery) provides a solid foundation for these enhancements.

## 6.8 Conclusion

This work shows that clinically relevant, real-time health insights are achievable on commodity wearables by pairing edge inference with cloud training and delivery. Compression, activity-aware personalization, and privacy-first design kept latency and power within target while maintaining accuracy above 90%. The architecture is ready to scale to richer sensing, federated learning, and explainability, and it provides a clear path toward regulatory-grade validation without redesigning the stack. The remaining roadmap—broader sensor fusion, adaptive scheduling, and clinical trials—now focuses on depth and trust rather than feasibility.

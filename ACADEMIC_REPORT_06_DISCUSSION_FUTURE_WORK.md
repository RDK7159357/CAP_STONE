# Chapter 6: Discussion and Future Work

## 6.1 Interpretation of Results

The implemented hybrid edge-cloud system met or exceeded all primary performance targets: sub-150ms end-to-end latency (137ms), >18-hour battery life (18.7h), high activity classification accuracy (93.8%), and robust anomaly detection (90.9% sensitivity, 95.1% specificity). These results validate the core hypothesis that combining on-device ML with cloud-side training yields real-time, privacy-preserving health monitoring without sacrificing model quality.

Key observations:
- **Latency:** On-device inference (activity + anomaly) accounts for ~91% of total latency; database and notification overheads are minor. Quantization and pruning were essential to keep inference under 100ms per model on smartwatch hardware.
- **Battery:** The dominant power consumers are wireless radios, not ML inference. Batching sync to 30-minute intervals and preferring WiFi over LTE delivered >18h battery life while keeping ML always-on.
- **Accuracy vs. Size:** INT8 quantization reduced activity model size by 41% and anomaly model size by 92% with <1% accuracy loss, confirming that edge-optimized compression is viable for this domain.
- **False Positives:** Incorporating per-activity baselines and reconstruction-error thresholds reduced false positives to 4.7%, markedly better than population-threshold baselines.

## 6.2 Limitations

- **Sensor Scope:** Current implementation omits ECG and blood pressure; PPG-only HR can be noisy during motion, impacting anomaly precision in vigorous activities.
- **Personalization Warm-up:** The 7-day rolling window delays fully personalized baselines for new users; anomalies during the first week rely on conservative defaults.
- **Context Granularity:** Activity states are coarse (6 classes). Edge cases (cycling vs. running uphill, strength training vs. vigorous play) can blur class boundaries and mildly elevate false positives.
- **Explainability:** User-facing alerts lack rich explanations (e.g., contributing features, SHAP-like attributions) which users requested; this limits trust and clinical interpretability.
- **Regulatory Depth:** While privacy and security controls exist, no formal HIPAA/GDPR certification or clinical validation study has been completed.

## 6.3 Comparison to Existing Work

Compared to cloud-only commercial systems (e.g., Fitbit, Samsung cloud analytics), this approach delivers markedly lower alert latency (137ms vs. 500–2000ms) and better offline resilience. Compared to fixed-threshold wearables, personalized baselines plus activity-aware anomaly scoring reduce false alarms by an order of magnitude. Research prototypes that use deep models often run in the cloud or on smartphones; this work demonstrates that carefully compressed LSTM and CNN-LSTM models can execute on watches within strict power and memory budgets while retaining >90% accuracy.

## 6.4 Practical Implications

- **Clinical Readiness:** While not a medical device, the system’s low latency and high sensitivity suggest potential for early-warning adjuncts (e.g., resting tachycardia, sleep HR drift). Formal clinical trials would be the next step.
- **Privacy Posture:** Edge-first inference and federated-learning readiness position the system well for stringent data-sovereignty environments.
- **Deployment:** OTA model delivery with versioned S3 registry supports safe rollouts, rollback, and A/B testing. The architecture generalizes to other time-series modalities (respiration, gait) with minimal changes.

## 6.5 Future Work

1. **Richer Sensing and Fusion:** Integrate SpO₂, ECG, skin temperature, and barometric trends; explore sensor fusion with attention/transformer blocks for robustness to motion artifacts.
2. **Federated Learning at Scale:** Implement periodic on-device fine-tuning with secure aggregation and differential privacy to improve personalization without sharing raw data.
3. **Explainability and User Trust:** Add lightweight on-device attribution (e.g., per-feature contribution scores) and clinician-friendly summaries to reduce alert fatigue and increase trust.
4. **Adaptive Scheduling:** Dynamically adjust sampling, inference cadence, and sync frequency based on battery state, recent anomalies, and activity context to extend battery beyond 24h.
5. **Context Expansion:** Enrich activity taxonomy (e.g., cycling, swimming, resistance training) and include environmental context (temperature, altitude) for better baseline selection.
6. **Predictive Modeling:** Add short-horizon forecasting (e.g., 30–120 minutes) for preemptive alerts using seq2seq or temporal convolutional networks.
7. **Regulatory and Clinical Validation:** Design prospective studies for sensitivity/specificity under clinical endpoints; align data handling and audit trails for HIPAA/GDPR certification.
8. **Edge Hardware Acceleration:** Evaluate NNAPI/GPU/NPU on newer watches to reduce inference latency and enable slightly larger models without extra power draw.

## 6.6 Risks and Mitigations

- **Data Quality Variance:** Motion artifacts and skin perfusion affect PPG; mitigate with signal-quality indices and auto-rejection before inference.
- **Model Drift:** Physiology changes over time; mitigate with weekly cloud retraining, OTA updates, and optional on-device fine-tuning.
- **Battery Regression:** New features can erode battery life; mitigate with per-feature power budgets, instrumentation, and regression testing on real hardware.
- **Security Exposure:** API misuse or key leakage; mitigate with HMAC auth, key rotation, rate limiting, and end-to-end TLS.

## 6.7 Summary

The edge-first hybrid architecture proved both feasible and effective: real-time alerts, privacy preservation, competitive accuracy, and acceptable battery life on commodity Wear OS hardware. The remaining gaps—richer sensing, stronger personalization, explainability, and formal clinical validation—define the next phase of work. The system’s modular design (separable edge models, cloud training, and OTA delivery) provides a solid foundation for these enhancements.

## 6.8 Conclusion

This work shows that clinically relevant, real-time health insights are achievable on commodity wearables by pairing edge inference with cloud training and delivery. Compression, activity-aware personalization, and privacy-first design kept latency and power within target while maintaining accuracy above 90%. The architecture is ready to scale to richer sensing, federated learning, and explainability, and it provides a clear path toward regulatory-grade validation without redesigning the stack. The remaining roadmap—broader sensor fusion, adaptive scheduling, and clinical trials—now focuses on depth and trust rather than feasibility.

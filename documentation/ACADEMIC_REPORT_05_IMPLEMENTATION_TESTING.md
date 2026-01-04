# Chapter 5: Implementation and Testing (Current Snapshot)

> This reflects what is running today: an edge-only Wear OS app with bundled TFLite models, no cloud backend, and limited manual testing.

## 5.1 Implementation Overview
- **Platform:** Wear OS app (Kotlin/Compose).
- **Models:** Bundled TFLite activity classifier (HR/steps/calories/distance) and 10×4 anomaly autoencoder.
- **Execution:** Models loaded from assets; CPU inference by default; rule-based fallback when inference fails.
- **Data handling:** No Room persistence, no WorkManager sync, no backend API calls; metrics are used transiently for decisions and notifications.
- **Updates:** Models and thresholds are shipped with the app; updates require rebuilding or manual asset swap.

## 5.2 Minimal Configuration (build.gradle excerpts)
- Uses Wear Compose material, Health Services client, and TensorFlow Lite runtime.
- Omits Room, Retrofit, and cloud SDKs in the current build.

## 5.3 Key App Components (As-Built)
- **Health data collection:** Pull HR/steps/calories/distance via Health Services; batch into 10-sample window.
- **Preprocessing:** Normalize and zero-pad to 10×4 tensor; shared across both models.
- **Inference engine:** Runs activity classifier then anomaly autoencoder; uses reconstruction error vs. threshold.
- **Fallback:** If model load/run fails, apply simple HR/steps rules to trigger alerts.
- **Alerting:** Local watch notification only; no mobile/ cloud notification path.

## 5.4 Testing Performed
- **Model sanity check:** Verified both TFLite models load and produce outputs on-device; `usedTflite=true` observed in logs.
- **Functional smoke:** Manual runs exercising activity classification and anomaly scoring; confirmed alert triggers on elevated HR in a synthetic window.
- **UI check:** Compose button padding verified via Text modifiers (contentPadding unsupported on Wear Button).
- **No automated tests:** No unit/UI/integration tests are present for the app.

## 5.5 Performance/Power Status
- Only spot-checked latency during development; expected edge inference in the sub-200 ms range; no formal profiling or battery run-down tests performed.
- NNAPI not required; CPU path is acceptable for current model sizes.

## 5.6 Known Gaps and Future Work
- Add Room persistence and reliable sync when backend exists.
- Wire cloud/OTA path for model updates.
- Add accel/gyro/SpO2 support and retrain models accordingly.
- Introduce automated tests (unit, integration, UI) and instrumented performance/power profiling.
- Add personalization/baseline adaptation once data storage and policy are defined.

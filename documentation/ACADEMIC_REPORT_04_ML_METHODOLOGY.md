# Chapter 4: Machine Learning Methodology (Current Snapshot)

> Reflects the edge-only implementation in the Wear OS app. No cloud training loop, personalization, or accel/gyro/SpO2 inputs are present in the shipped models. Models are bundled manually as TFLite assets.

## 4.1 Scope and Objectives
- Deliver lightweight, on-device inference for activity context and anomaly scoring under watch CPU constraints.
- Keep preprocessing minimal: normalize/pad HR, steps, calories, distance into a fixed 10×4 window.
- Provide rule-based fallback when models fail to load or run.

## 4.2 Models Implemented

### 4.2.1 Activity Classifier
- **Inputs:** 10×4 window (HR, steps, calories, distance).
- **Architecture:** Compact temporal head producing softmax over activities; no accel/gyro CNN used in this build.
- **Output:** Activity label used only as context; probabilities are not persisted.
- **Optimization:** Post-training quantized TFLite; runs on CPU (NNAPI optional).

### 4.2.2 Anomaly Autoencoder
- **Inputs:** Same 10×4 window.
- **Architecture:** LSTM autoencoder; reconstruction MSE is the anomaly score.
- **Decision:** Fixed threshold; if score exceeds threshold → local notification.
- **Fallback:** On any model load/run failure, rule checks on HR/steps trigger alerts.

## 4.3 Data and Preprocessing (As-Built)
- Health Services provides HR, steps, calories, distance snapshots.
- Maintain sliding window of the last 10 samples; zero-pad if short.
- Normalize per-feature to training ranges; no spectral or frequency features.
- Reuse the same tensor for both models.

## 4.4 Training Overview (Pragmatic)
- **Datasets:** Small curated/synthetic sequences reflecting plausible HR/steps/calories/distance patterns; no user-specific baselines.
- **Augmentation:** Light noise and scaling to cover wearable variability.
- **Losses:** Cross-entropy for activity; reconstruction MSE for anomaly.
- **Validation:** Offline sanity checks on held-out synthetic slices; no large-scale field validation yet.
- **Export:** Converted to TFLite (quantized) and bundled in the APK; updates require manual asset replacement or a new build.

## 4.5 What Is Not Implemented Yet
- No accel/gyro/SpO2 inputs in shipped models.
- No personalization/baseline adaptation and no cloud-assisted retraining loop.
- No OTA model delivery; no backend fetch.
- No full latency/battery profiling beyond quick spot checks.


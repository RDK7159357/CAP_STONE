# Chapter 3: System Architecture (Current Snapshot)

> This chapter reflects the **current, edge-only implementation** running on the Wear OS app. Cloud services, OTA delivery, Room persistence, personalization, and accelerometer/gyroscope inputs are **not yet implemented** and are called out as future work.

## 3.1 High-Level View

- **Device:** Wear OS smartwatch; all sensing, inference, and alerting execute on-device.
- **Models:** Two bundled TFLite models (no remote fetch/OTA yet):
  - **Activity classifier:** Softmax over activities using heart rate, steps, calories, distance features.
  - **Anomaly detector:** LSTM autoencoder over a 10×4 sequence (HR, steps, calories, distance) with reconstruction error scoring.
- **Fallback:** Rule-based checks run if model inference fails.
- **Data handling:** No persistent storage or cloud sync in the current build; metrics are used transiently for inference and alerts.
- **Updates:** Models are updated manually via app bundle; no over-the-air pipeline is wired yet.

### 3.1.0 Complete System Overview (Future Vision)

![Complete System Architecture](attachments/7.png)

*This diagram shows the full envisioned architecture including edge, cloud, mobile dashboard, and ML training pipeline components. Components shown in the cloud and mobile layers are not yet implemented.*

### 3.1.1 High-Level System Architecture

![High-Level System Architecture](attachments/1.png)

### 3.1.2 Component Interaction Diagram

![Component Interaction Sequence](attachments/2.png)

### 3.1.3 Data Flow Architecture

![Data Flow Architecture](attachments/3.png)

## 3.2 Edge Layer (Implemented)

### 3.2.1 Sensing and Preprocessing
- Inputs: heart rate, steps, calories, distance (no accel/gyro/SpO2 in this build).
- Sampling: polled from Health Services; batched into a sliding window of 10 timesteps.
- Preprocessing: normalize features and zero-pad if the window is short; no spectral features.

### 3.2.2 ML Inference Pipeline
- Activity classifier: produces activity probabilities; only the label is used downstream.
- Anomaly detector: LSTM autoencoder on the 10×4 window; reconstruction MSE is the anomaly score.
- Decision: if the anomaly score exceeds the threshold, raise an on-device notification; otherwise, do nothing.
- Failure path: if either model load or inference fails, a simple rule-based check (HR and steps) triggers alerts.
- Execution: both models are loaded from bundled assets; NNAPI delegate optional, but CPU is used by default.

### 3.2.3 Data Handling and Alerts
- No Room database or local history is persisted in this build.
- No background sync, WorkManager jobs, or cloud transmission are active.
- Alerts are local-only notifications on the watch.

## 3.3 Non-Implemented / Planned (Future Work)

These are **not present** today but remain planned extensions:
- **Cloud backend and sync:** API gateway, ingestion Lambdas, and storage (e.g., DynamoDB/S3) with periodic uploads from the watch.
- **OTA model delivery:** Pulling new TFLite versions from a registry instead of bundling them in the app.
- **Personalization:** On-device or cloud-assisted baseline calculation and adaptive thresholds.
- **Richer sensing:** Adding accelerometer/gyroscope/SpO2 features and retraining models to consume them.
- **Persistence:** Room database for local history and reliable uploads when connectivity is available.

### 3.3.1 Future Hybrid Architecture (Planned)

![Future Hybrid Architecture](attachments/4.png)

### 3.3.2 Planned OTA Model Update Flow

![OTA Model Update Flow](attachments/5.png)

## 3.4 Edge Data Flow (As-Built)

1) Health Services provides HR, steps, calories, distance snapshots.
2) Preprocess batches the last 10 samples into a 10×4 tensor.
3) Activity classifier runs; label is recorded for context (not persisted).
4) Anomaly autoencoder runs; reconstruction error becomes the anomaly score.
5) If score > threshold → local notification; else no action.
6) If models fail → rules fallback checks HR/steps and may notify.

### 3.4.1 Detailed Processing Pipeline

![Detailed Processing Pipeline](attachments/6.png)

## 3.5 Constraints and Known Gaps

- No cloud path, no OTA, and no persistence yet.
- Models do not consume accelerometer/gyroscope/SpO2 despite earlier design intent.
- Battery/latency profiling is pending; current behavior is based on small sanity checks only.
- Security/PII handling is limited to on-device use; no data leaves the watch in this build.


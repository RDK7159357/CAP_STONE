# Real-Time Health Monitoring System — Architecture Deck (Slide-Ready)

## 0. How to Use
- Each section = one PPT slide; copy/paste bullets.
- Diagrams are ASCII; replace with visuals if desired.
- Cloud stack assumes AWS; GCP alternates noted.

## 1. Vision & Scope
- Continuous vital monitoring via Wear OS → cloud → ML → mobile alerts.
- Goals: early anomaly detection (<2s end-to-end), low battery impact, secure & compliant.
- Audiences: patients, athletes, caregivers, clinicians.

## 2. High-Level Architecture (E2E Flow)
```
[Wear OS App]
  - Sensors (HR, steps, calories)
  - Room buffer; WorkManager batch sync (1–2m)
  - Retrofit → Auth header (JWT/API key)
        |
        v
[API Gateway]
        |
        v
[Lambda Ingestion]
  - Validate/authn
  - Normalize/persist
        |
        v
[DynamoDB]
  - Time-series store (PK=userId, SK=timestamp)
        |
        +--> [DynamoDB Stream/Kinesis] --> [SageMaker Endpoint]
        |                                   - LSTM AE / Isolation Forest
        |                                   - returns anomalyScore/flag
        |
        +--> [SNS/Firebase] alerts
        |
        +--> [Analytics/BI] (optional S3 lake)
        |
        v
[React Native Mobile Dashboard]
  - Real-time charts
  - Alert inbox (Expo Notifications)
```

## 3. Component Responsibilities
- WearOSApp (Kotlin/Compose): sensor read, buffer (Room), background sync (WorkManager), retry/backoff, minimal battery.
- CloudBackend (API GW + Lambda + DynamoDB): authn/z, validation, persistence, streaming to ML, alert fan-out.
- MLPipeline (Python/TF/Sklearn): preprocessing, training (LSTM AE, Isolation Forest), model registry (S3), deploy to SageMaker endpoint.
- MobileDashboard_RN (React Native + TypeScript): fetch metrics, render charts, manage notifications (Expo Notifications), offline cache (AsyncStorage), settings (Zustand store).
- Observability: CloudWatch logs/metrics, X-Ray traces, alarms (SNS), dashboards.

## 4. Data Flow (Numbered)
1) Sense: Health Services API samples every 5s; stored in Room.
2) Sync: WorkManager batches every 1–2m (gzip, JSON); retries on failure.
3) Ingest: Retrofit POST → API Gateway; Lambda auth/validate → DynamoDB write.
4) Stream: DynamoDB Stream/Kinesis triggers inference Lambda → SageMaker endpoint.
5) Detect: Model returns anomalyScore & flag; persisted back to DynamoDB.
6) Alert: SNS/FCM push to user; dashboard polls/refreshes charts.
7) Observe: CloudWatch metrics/alarms; logs with requestId/userId hash.

## 5. Deployment Topology (AWS)
- Edge: API Gateway REST; optional CloudFront for caching.
- Compute: Lambda (ingestion), Lambda (inference driver), provisioned concurrency for p95.
- Storage: DynamoDB on-demand; S3 for model/artifacts; S3 (optional) data lake.
- ML: SageMaker endpoint (auto-scaling); Canary for model versions.
- Messaging: SNS → FCM/Apple APNs; optional SQS DLQ.
- Identity: Cognito (JWT) or API key for PoC; IAM least-privilege.
- Observability: CloudWatch Metrics/Logs, X-Ray tracing, alarms.
- Envs: dev / stage / prod; per-env config in Parameter Store.

## 6. Security & Privacy
- TLS everywhere; no PII in logs.
- AuthN: Cognito JWT (preferred) or API key; custom authorizer on API GW.
- AuthZ: userId from claims; enforce PK isolation on DynamoDB.
- Secrets: AWS Secrets Manager/SSM; never in code/env files.
- Data retention: DynamoDB TTL (e.g., 90 days); S3 lifecycle to IA/Glacier.
- Compliance aids: audit logs, consent captured in app, opt-in notifications.

## 7. Reliability & Performance
- Targets: p95 ingest < 150 ms, p95 model < 150 ms, end-to-end < 2 s, 99.9% uptime.
- Scaling: Lambda + API GW auto; DynamoDB on-demand WCU/RCU; SageMaker autoscaling warm pools.
- Resilience: DLQ for Lambda, retries with backoff, idempotent writes (requestId), fallback rule-based thresholds if model unavailable.
- Cost controls: DynamoDB on-demand, right-size endpoint, turn off notebooks; CloudFront caching for configs.

## 8. Data Model (DynamoDB)
- Table: HealthMetrics
  - PK: userId (S)
  - SK: timestamp (N, epoch ms)
  - attrs: hr, steps, calories, deviceBattery, deviceFw, anomalyScore, anomalyFlag (bool), uploadLagMs, source (wearos)
- GSI1 (recent reads): PK userId, SK -timestamp (descending via inverted value)
- TTL: expiresAt (epoch) for retention.

## 9. API Contract (Ingest)
- Endpoint: POST /v1/metrics
- Auth: Bearer JWT (cognito) or x-api-key (PoC)
- Request body (sample):
```json
{
  "userId": "u123",
  "deviceId": "watch-001",
  "timestamp": 1700000000000,
  "metrics": {"hr": 82, "steps": 1200, "calories": 35},
  "battery": 78,
  "fw": "1.0.3",
  "source": "wearos"
}
```
- Response: `{ "status": "accepted", "anomalyFlag": false, "score": 0.08 }`
- Errors: 400 (validation), 401 (auth), 429 (throttle), 500 (server).

## 10. ML Design
- Online: LSTM Autoencoder (reconstruction error) + Isolation Forest fallback; threshold calibrated per user segment.
- Offline pipeline: data_cleaner.py → train_lstm_autoencoder.py → evaluate → register artifact (S3) → deploy_to_sagemaker.py.
- Monitoring: input drift (KS test), latency, error rate, alert on p95 > target.
- Rollout: blue/green (prod-v1/prod-v2 endpoints) with weighted traffic; auto-rollback on alarm.

## 11. Sequences (Slide-Ready)
- Normal ingest & score:
```
Wear App -> API GW -> Lambda ingest -> DynamoDB -> Stream -> Inference Lambda -> SageMaker -> DynamoDB (score) -> SNS/FCM -> Dashboard
```
- Failure path (model down):
```
Inference Lambda -> detects endpoint failure -> use rule-based thresholds -> mark degraded -> push alert with note -> queue retry
```
- Offline retrain:
```
S3 data -> Preprocess -> Train -> Eval -> Register -> Deploy new endpoint -> Canary -> Promote
```

## 12. Testing & Quality
- Unit: Kotlin (sensors, repos), Python (handlers, preprocessing), TypeScript (components, services, stores).
- Contract: Ingest API schema via tests + Postman collection.
- Integration: Emulator synthetic data → API → DynamoDB → model → alert.
- Load: k6/Locust against API GW; DynamoDB WCU/RCU alarms; model p95.
- End-to-end: scripted scenario (high HR 10m) verifying alert delivery + dashboard flag.

## 13. Ops Runbook
- Metrics: ingest 2xx rate, Lambda duration/errors, DynamoDB throttles, SageMaker p95/5xx, alert delivery success.
- Alarms: API 5xx > 1%, Lambda DLQ > 0, DynamoDB throttles > 0, model 5xx > 0.5%.
- Dashboards: CloudWatch dashboard with above + business metric (anomalies/hour).
- Logging: structured JSON with requestId/userId hash; X-Ray tracing for cold-start insight.

## 14. Risks & Mitigations
- Battery drain: batch uploads, adjustable sampling, foreground service limits.
- False positives: per-user thresholds, smoothing, cooldown on alerts.
- Latency spikes: provisioned concurrency, model warm pools, fallback rules.
- Cost creep: DynamoDB on-demand alarms, right-size SageMaker, archive old data.
- Security drift: periodic key rotation, least-privilege IAM, dependency scans.

## 15. Rollout Plan
- Dev: synthetic data; verify end-to-end.
- Stage: small pilot users; canary model; alert QA.
- Prod: feature flags for model version; phased rollout; observability SLOs.

## 16. Slide Ordering Suggestion
1) Title & vision
2) High-level architecture diagram
3) Component responsibilities
4) Data flow (numbered)
5) Deployment topology
6) Data model + API contract
7) ML design
8) Security & privacy
9) Reliability & performance
10) Sequences (ingest/alert)
11) Testing & ops
12) Risks & rollout

---
Created for quick PPT transfer. Replace ASCII diagrams with visuals if time permits.

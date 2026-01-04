# Wear OS App – API Integration Guide

This guide explains how to connect the Wear OS app to your backend, step by step. It assumes you keep the current static values in `ApiConfig` and wire real endpoints/keys later.

## 1) Where to configure
- File: `WearOSApp/app/src/main/java/com/capstone/healthmonitor/wear/data/network/ApiConfig.kt`
- Defaults are placeholders. Update `BASE_URL` and `API_KEY` when your backend is ready.
- Runtime override: the Settings screen allows entering a custom API endpoint; the app will redirect requests to that base URL without rebuilding Retrofit.

## 2) Minimal setup (static)
1) Set `ApiConfig.BASE_URL` to your backend root (trailing slash required), e.g. `https://api.example.com/`.
2) Set `ApiConfig.API_KEY` if your backend expects an API key header `X-API-Key`.
3) Keep endpoints unless your backend differs:
   - `health-data/ingest`
   - `health-data/sync`
   - `health-data/status`
4) Build and run on the Wear emulator. Monitoring + sync will hit your static base URL.

## 3) Runtime override (no rebuild)
1) On the watch, open **Settings**.
2) Enter your API base URL in **API Endpoint** (include `https://` and trailing `/`).
3) Tap **Apply**. Subsequent requests are rewritten to this host.
4) To revert, clear the field and Apply (falls back to `ApiConfig.BASE_URL`).

## 4) Permissions & manifest
Ensure these are present (already in the project):
- `android.permission.BODY_SENSORS`
- `android.permission.ACTIVITY_RECOGNITION`
- `android.permission.INTERNET`
- `android.permission.FOREGROUND_SERVICE`
- For API 33+: request `POST_NOTIFICATIONS` at runtime if you want anomaly notifications.

## 5) WorkManager sync interval
- Minimum 15 minutes (platform limit). Settings slider clamps to 15–60 minutes.
- Apply in Settings reschedules the periodic sync with the chosen interval.

## 6) Data model payload
- `HealthMetricRequest` sent in `syncHealthData` body:
  - `userId`: static `user_001` unless you change it.
  - `timestamp`: Unix ms.
  - `metrics` map: includes any present of `heartRate`, `steps`, `calories`, `distance`, `batteryLevel`.
  - `deviceId`: defaults to `wear_<MODEL>`.
- The app expects `HealthMetricResponse { success: Boolean, message: String, anomalyDetected: Boolean? }`.

## 7) End-to-end checklist
- [ ] Set `ApiConfig.BASE_URL` to your backend root (with `/`).
- [ ] Set `ApiConfig.API_KEY` if needed.
- [ ] Confirm emulator/device has network.
- [ ] Start monitoring (Home → Start Monitoring).
- [ ] Verify data writes locally (Recent History updates).
- [ ] Watch logs for sync attempts (`DataSyncWorker`): should POST to `<base>/health-data/sync`.
- [ ] If using runtime override, enter endpoint in Settings and Apply, then trigger sync.

## 8) Testing tips
- Use emulator virtual sensors to generate HR/steps; wait for sync window.
- Temporarily reduce sync interval to 15m for faster verification.
- Check backend logs for received payloads.
- If sync fails, the worker retries with backoff and keeps data buffered in Room.

## 9) Common pitfalls
- Missing trailing slash on base URL → URL rewrite may fail.
- Invalid custom endpoint in Settings → interceptor falls back to static `ApiConfig.BASE_URL`.
- API 33+ notifications blocked → anomaly alerts won’t show; request permission.
- Backend response must return `success = true`; otherwise metrics stay unsynced.

## 10) When ready for production
- Replace static `userId`/`deviceId` with authenticated values.
- Store API key securely (not hardcoded) and/or switch to OAuth/JWT.
- Validate TLS certificates and pin if required.
- Add pagination/filters if backend grows; current sync sends up to 100 unsynced metrics per batch.

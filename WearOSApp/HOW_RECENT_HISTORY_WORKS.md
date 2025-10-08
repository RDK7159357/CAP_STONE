# How Recent History Works - Detailed Explanation

## 📊 Overview

The **Recent History** feature displays the last 5 health measurements on your watch, showing you how your metrics have changed over time with automatic real-time updates.

## 🔄 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    1. DATA COLLECTION                        │
│                                                              │
│  Health Services API → HealthMonitoringService              │
│  (Every 5 seconds)     (Foreground Service)                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    2. DATABASE STORAGE                       │
│                                                              │
│  Room Database (SQLite)                                      │
│  Table: health_metrics                                       │
│  ├── id (auto-increment)                                     │
│  ├── timestamp (Long)                                        │
│  ├── heartRate (Float)                                       │
│  ├── steps (Int)                                            │
│  ├── calories (Float)                                        │
│  ├── isSynced (Boolean)                                      │
│  └── ... more fields                                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    3. DATA RETRIEVAL                         │
│                                                              │
│  HealthRepository.getLatestMetrics(10)                      │
│  └── HealthMetricDao.getRecentMetrics(10)                   │
│      Query: SELECT * FROM health_metrics                     │
│             ORDER BY timestamp DESC                          │
│             LIMIT 10                                         │
│                                                              │
│  Returns: Flow<List<HealthMetric>>                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    4. UI OBSERVATION                         │
│                                                              │
│  MainActivity:                                               │
│  val healthMetrics by healthMetricsFlow.collectAsState()   │
│                                                              │
│  • Flow automatically emits new data when DB changes        │
│  • collectAsState() converts Flow to Compose State          │
│  • UI recomposes automatically when state changes           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    5. UI RENDERING                           │
│                                                              │
│  healthMetrics.take(5).forEach { metric ->                  │
│    // Display each of the last 5 metrics in a Card          │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

## 💡 How It Works Step-by-Step

### Step 1: Service Collects Data
```kotlin
// In HealthMonitoringService.kt
override fun onDataReceived(data: DataPointContainer) {
    val heartRateData = data.getData(DataType.HEART_RATE_BPM)
    heartRateData.forEach { dataPoint ->
        currentHeartRate = dataPoint.value.toFloat()
        saveMetricToDatabase() // ← Saves to Room DB
    }
}
```

**What happens:**
- Every 5 seconds, Health Services API provides new heart rate data
- Service saves it to Room database with current timestamp
- Database automatically triggers Flow update

### Step 2: Repository Provides Flow
```kotlin
// In HealthRepository.kt
fun getLatestMetrics(limit: Int = 10): Flow<List<HealthMetric>> {
    return healthMetricDao.getRecentMetrics(limit)
}
```

**What happens:**
- Repository exposes a Flow that emits List<HealthMetric>
- Flow is "hot" - it stays alive and emits new data when DB changes
- No manual refresh needed!

### Step 3: DAO Query
```kotlin
// In HealthMetricDao.kt
@Query("SELECT * FROM health_metrics ORDER BY timestamp DESC LIMIT :limit")
fun getRecentMetrics(limit: Int): Flow<List<HealthMetric>>
```

**What happens:**
- Query orders by timestamp (newest first)
- Limits results to requested number (10 in our case)
- Returns as Flow - Room automatically re-emits when data changes

### Step 4: MainActivity Observes
```kotlin
// In MainActivity.kt
@Inject
lateinit var healthRepository: HealthRepository

setContent {
    HealthMonitorScreen(
        healthMetricsFlow = healthRepository.getLatestMetrics(10)
    )
}
```

**What happens:**
- MainActivity injects HealthRepository via Hilt
- Passes Flow to the UI composable
- Flow stays connected throughout app lifecycle

### Step 5: UI Displays Data
```kotlin
// In HealthMonitorScreen composable
val healthMetrics by healthMetricsFlow.collectAsState(initial = emptyList())

// Later in the code...
healthMetrics.take(5).forEach { metric ->
    item {
        Card {
            // Display metric.heartRate, metric.steps, etc.
            Text("${metric.heartRate?.toInt() ?: 0} BPM")
            Text(formatTime(metric.timestamp))
        }
    }
}
```

**What happens:**
- `collectAsState()` converts Flow to Compose State
- `.take(5)` gets only first 5 items from the list
- `.forEach` creates a Card for each metric
- When Flow emits new data, UI automatically recomposes

## 🎯 Key Features

### 1. **Automatic Real-Time Updates**
```
New data arrives → Room DB updated → Flow emits → UI recomposes
```
No manual refresh needed! The UI updates automatically.

### 2. **Sorted by Time (Newest First)**
```sql
ORDER BY timestamp DESC
```
Most recent measurement appears first, older ones below.

### 3. **Limited to Last 5 (Performance)**
```kotlin
healthMetrics.take(5)
```
Only shows 5 most recent to:
- Keep UI clean
- Improve performance
- Save battery

### 4. **Shows Sync Status**
```kotlin
if (!metric.isSynced) {
    Text("⏳") // Shows pending sync icon
}
```
Visual indicator if data hasn't been uploaded to cloud yet.

## 📱 What Each Card Shows

```
┌────────────────────────────────┐
│  75 BPM              150👣 ⏳  │  ← Heart Rate | Steps | Sync Status
│  19:25:38                      │  ← Timestamp (HH:mm:ss)
└────────────────────────────────┘
```

### Card Components:
1. **Heart Rate** (BPM) - Red color
2. **Timestamp** - When measurement was taken
3. **Steps** - Step count at that time
4. **Sync Icon** - ⏳ if not synced to cloud yet

## 🔍 Example Data Flow

### Timeline:
```
7:24:30 PM → HR: 75 BPM, Steps: 150 ✓ Synced
7:24:35 PM → HR: 80 BPM, Steps: 151 ✓ Synced
7:24:40 PM → HR: 78 BPM, Steps: 152 ⏳ Pending
7:24:45 PM → HR: 82 BPM, Steps: 153 ⏳ Pending
7:24:50 PM → HR: 85 BPM, Steps: 154 ⏳ Pending  ← Latest (shown at top)
```

### On Your Watch Screen:
```
Recent History
├── 85 BPM | 154👣 ⏳  (19:24:50)  ← Newest
├── 82 BPM | 153👣 ⏳  (19:24:45)
├── 78 BPM | 152👣 ⏳  (19:24:40)
├── 80 BPM | 151👣 ✓  (19:24:35)
└── 75 BPM | 150👣 ✓  (19:24:30)  ← Oldest (5th)
```

## ⚡ Performance Optimizations

### 1. **Lazy Loading**
```kotlin
ScalingLazyColumn {
    healthMetrics.take(5).forEach { metric ->
        item { Card {...} }
    }
}
```
Only renders visible items, saves memory.

### 2. **Limited Database Query**
```kotlin
getRecentMetrics(limit = 10) // Only fetch 10, display 5
```
Fetches 10, displays 5 (buffer for smooth scrolling).

### 3. **Flow-Based Updates**
```kotlin
Flow<List<HealthMetric>> // Reactive, no polling
```
Database pushes updates only when data changes.

## 🧪 Testing the Recent History

### Method 1: Use Mock Data (Current)
```
The service generates mock data every 1 second:
60 BPM → 65 BPM → 70 BPM → 75 BPM → ...

Each creates a new database entry.
Recent History updates automatically.
```

### Method 2: Use Emulator Sensors
```
Android Studio → Extended Controls (...) → Virtual Sensors
→ Health Services Tab
→ Adjust Heart Rate slider
→ Watch history update in real-time
```

### Method 3: Check Database Directly
```bash
# Via ADB
adb shell
run-as com.capstone.healthmonitor.wear
cd databases
sqlite3 health_database

# SQL Query
SELECT id, timestamp, heartRate, steps, isSynced 
FROM health_metrics 
ORDER BY timestamp DESC 
LIMIT 5;
```

## 🔧 Customization Options

### Show More/Less History
```kotlin
// Change from 5 to 10
healthMetrics.take(10).forEach { ... }
```

### Change Sort Order
```kotlin
// In DAO - Show oldest first instead
@Query("SELECT * FROM health_metrics ORDER BY timestamp ASC LIMIT :limit")
```

### Filter by Date
```kotlin
// Show only today's data
val today = healthMetrics.filter { 
    isToday(it.timestamp) 
}.take(5)
```

### Group by Hour
```kotlin
// Show average per hour
val grouped = healthMetrics.groupBy { 
    getHour(it.timestamp) 
}
```

## 🐛 Troubleshooting

### Issue: History not updating
**Solution:**
- Check if service is running
- Verify database permissions
- Check Flow connection in logs

### Issue: Shows old data
**Solution:**
- Clear app data
- Restart service
- Check timestamp formatting

### Issue: Empty history
**Solution:**
- Wait for data collection (5 seconds)
- Check sensor availability
- Verify database writes

## 📊 Summary

**Recent History = Real-time Database-Powered UI**

```
Service → Room DB → Flow → Compose State → UI
  (5s)     (Auto)   (Auto)    (Auto)      (Auto)
```

Everything is **automatic** and **reactive**:
- ✅ No manual refresh
- ✅ No polling
- ✅ No memory leaks
- ✅ Battery efficient
- ✅ Always up-to-date

This is a **production-grade** implementation using Android best practices! 🚀

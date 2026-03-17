package com.capstone.healthmonitor.wear.presentation.ui

import android.Manifest
import android.app.ActivityManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.wear.compose.foundation.lazy.ScalingLazyColumn
import androidx.wear.compose.foundation.lazy.rememberScalingLazyListState
import androidx.wear.compose.foundation.lazy.items
import androidx.wear.compose.material.Button
import androidx.wear.compose.material.Card as WearCard
import androidx.wear.compose.material.Chip
import androidx.wear.compose.material.Colors
import androidx.wear.compose.material.MaterialTheme
import androidx.wear.compose.material.Scaffold
import androidx.wear.compose.material.Text
import androidx.wear.compose.material.TimeText
import androidx.wear.compose.material.ToggleChip
import androidx.compose.material.Slider
import androidx.compose.material.TextField as ComposeTextField
import androidx.compose.material.Card as RegularCard
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkRequest
import com.capstone.healthmonitor.wear.data.local.SettingsDataStore
import com.capstone.healthmonitor.wear.data.local.SettingsState
import com.capstone.healthmonitor.wear.data.repository.HealthRepository
import com.capstone.healthmonitor.wear.domain.model.HealthMetric
import com.capstone.healthmonitor.wear.domain.usecase.LocalAnomalyDetector
import com.capstone.healthmonitor.wear.domain.usecase.TfLiteSanityCheck
import com.capstone.healthmonitor.wear.service.DataSyncWorker
import com.capstone.healthmonitor.wear.service.HealthMonitoringService
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.emptyFlow
import kotlinx.coroutines.launch
import kotlin.math.max
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import androidx.compose.material.ExperimentalMaterialApi

// Direct property accessor — HealthMetric now declares anomalyReasons.
private fun HealthMetric.safeAnomalyReasons(): List<String> = anomalyReasons

@OptIn(ExperimentalMaterialApi::class)
@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject
    lateinit var healthRepository: HealthRepository

    @Inject
    lateinit var settingsDataStore: SettingsDataStore

    @Inject
    lateinit var tfLiteSanityCheck: TfLiteSanityCheck

    @Inject
    lateinit var localAnomalyDetector: LocalAnomalyDetector

    companion object {
        private const val TAG = "MainActivity"
        private const val MIN_SYNC_INTERVAL_MINUTES = 15
        private const val DEFAULT_SYNC_INTERVAL_MINUTES = 15
        private const val DEFAULT_USER_ID = "user_001"
    }

    private val defaultDeviceId: String by lazy { "wear_${Build.MODEL}" }

    private var requestedSyncIntervalMinutes: Int = DEFAULT_SYNC_INTERVAL_MINUTES

    private val requiredPermissions = buildList {
        add(Manifest.permission.BODY_SENSORS)
        add(Manifest.permission.ACTIVITY_RECOGNITION)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            add(Manifest.permission.POST_NOTIFICATIONS)
        }
    }.toTypedArray()

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.values.all { it }
        if (allGranted) {
            startMonitoring(requestedSyncIntervalMinutes)
        } else {
            Log.e(TAG, "Permissions not granted")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        tfLiteSanityCheck.runChecks()

        checkPermissionsAndStart(DEFAULT_SYNC_INTERVAL_MINUTES)

        setContent {
            HealthMonitorTheme {
                HealthMonitorScreen(
                    healthMetricsFlow = healthRepository.getLatestMetrics(50),
                    healthRepository = healthRepository,
                    localAnomalyDetector = localAnomalyDetector,
                    defaultUserId = DEFAULT_USER_ID,
                    defaultDeviceId = defaultDeviceId,
                    onScheduleSyncChange = { interval -> scheduleDataSync(interval) },
                    settingsFlow = settingsDataStore.settingsFlow,
                    onSaveSettings = { settingsDataStore.save(it) }
                )
            }
        }
    }

    private fun checkPermissionsAndStart(intervalMinutes: Int) {
        requestedSyncIntervalMinutes = intervalMinutes
        val permissionsToRequest = requiredPermissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }

        if (permissionsToRequest.isEmpty()) {
            startMonitoring(requestedSyncIntervalMinutes)
        } else {
            permissionLauncher.launch(permissionsToRequest.toTypedArray())
        }
    }

    private fun startMonitoring(intervalMinutes: Int) {
        val serviceIntent = Intent(this, HealthMonitoringService::class.java)
        ContextCompat.startForegroundService(this, serviceIntent)
        scheduleDataSync(intervalMinutes)
        Log.d(TAG, "Health monitoring started")
    }

    private fun scheduleDataSync(intervalMinutes: Int) {
        val safeInterval = max(intervalMinutes, MIN_SYNC_INTERVAL_MINUTES)
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val syncWorkRequest = PeriodicWorkRequestBuilder<DataSyncWorker>(
            safeInterval.toLong(), TimeUnit.MINUTES
        )
            .setConstraints(constraints)
            .setBackoffCriteria(
                BackoffPolicy.EXPONENTIAL,
                WorkRequest.MIN_BACKOFF_MILLIS,
                TimeUnit.MILLISECONDS
            )
            .build()

        val workManager = WorkManager.getInstance(this)
        workManager.cancelUniqueWork(DataSyncWorker.WORK_NAME)
        workManager.enqueueUniquePeriodicWork(
            DataSyncWorker.WORK_NAME,
            ExistingPeriodicWorkPolicy.UPDATE,
            syncWorkRequest
        )

        Log.d(TAG, "Data sync scheduled")
    }
}

@Composable
fun HealthMonitorTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colors = Colors(
            primary = Color(0xFF1976D2),
            primaryVariant = Color(0xFF004BA0),
            secondary = Color(0xFF4CAF50),
            secondaryVariant = Color(0xFF087F23),
            background = Color.Black,
            surface = Color(0xFF1E1E1E),
            error = Color(0xFFCF6679),
            onPrimary = Color.White,
            onSecondary = Color.White,
            onBackground = Color.White,
            onSurface = Color.White,
            onError = Color.Black
        ),
        content = content
    )
}

@Composable
fun HealthMonitorScreen(
    healthMetricsFlow: Flow<List<HealthMetric>> = emptyFlow(),
    healthRepository: HealthRepository,
    localAnomalyDetector: LocalAnomalyDetector = LocalAnomalyDetector(),
    defaultUserId: String,
    defaultDeviceId: String,
    onScheduleSyncChange: (Int) -> Unit,
    settingsFlow: Flow<SettingsState>,
    onSaveSettings: suspend (SettingsState) -> Unit
) {
    val scope = rememberCoroutineScope()
    var currentScreen by remember { mutableStateOf(Screen.Home) }
    val settingsState by settingsFlow.collectAsState(initial = SettingsState())
    var syncIntervalMinutes by rememberSaveable { mutableStateOf(settingsState.syncIntervalMinutes.toFloat()) }
    var notificationsEnabled by rememberSaveable { mutableStateOf(settingsState.notificationsEnabled) }
    var hapticsEnabled by rememberSaveable { mutableStateOf(settingsState.hapticsEnabled) }
    var apiEndpoint by rememberSaveable { mutableStateOf(settingsState.apiEndpoint) }
    var dataRetentionDays by rememberSaveable { mutableStateOf(settingsState.dataRetentionDays.toFloat()) }
    var lastAnomalyId by remember { mutableStateOf<Long?>(null) }
    val haptic = LocalHapticFeedback.current
    val context = LocalContext.current
    var isServiceRunning by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        while (true) {
            isServiceRunning = isHealthServiceRunning(context)
            delay(3000)
        }
    }

    LaunchedEffect(settingsState) {
        syncIntervalMinutes = settingsState.syncIntervalMinutes.toFloat()
        notificationsEnabled = settingsState.notificationsEnabled
        hapticsEnabled = settingsState.hapticsEnabled
        apiEndpoint = settingsState.apiEndpoint
        dataRetentionDays = settingsState.dataRetentionDays.toFloat()
    }

    val rawHealthMetrics by healthMetricsFlow.collectAsState(initial = emptyList())

    // Enrich metrics loaded from DB with in-memory anomaly reasons via LocalAnomalyDetector.
    // DB-loaded HealthMetric objects always have anomalyReasons = emptyList() (field is @Ignore),
    // so we re-compute them here for display purposes.
    val healthMetrics = remember(rawHealthMetrics) {
        rawHealthMetrics.mapIndexed { index, metric ->
            val recentPrior = rawHealthMetrics.drop(index + 1)
            val reasons = localAnomalyDetector.getAnomalyReasons(metric, recentPrior)
            if (reasons != metric.anomalyReasons) metric.also { it.anomalyReasons = reasons } else metric
        }
    }

    val latestMetric = healthMetrics.firstOrNull()

    // Anomaly detection: check anomalyReasons (now populated) or fall back to threshold
    val anomalyMetric = healthMetrics.firstOrNull {
        it.safeAnomalyReasons().isNotEmpty() || (it.heartRate ?: 0f) >= 140f
    }

    val heartRateList = healthMetrics.mapNotNull { it.heartRate }
    val averageHeartRate = if (heartRateList.isNotEmpty()) {
        heartRateList.average().toFloat()
    } else {
        0f
    }

    LaunchedEffect(anomalyMetric?.id, notificationsEnabled, hapticsEnabled) {
        val newId = anomalyMetric?.id
        if (newId != null && newId != lastAnomalyId) {
            Log.d("AnomalyDetection", "New anomaly detected! HR: ${anomalyMetric?.heartRate} BPM, ID: $newId")

            if (hapticsEnabled) {
                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                Log.d("AnomalyDetection", "Haptic feedback triggered")
            }
            if (notificationsEnabled) {
                sendAnomalyNotification(context, anomalyMetric)
                Log.d("AnomalyDetection", "Notification sent")
            }

            currentScreen = Screen.Anomaly
            Log.d("AnomalyDetection", "Navigated to Anomaly Alert screen")

            lastAnomalyId = newId
        }
    }

    when (currentScreen) {
        Screen.Home -> HomeScreen(
            healthMetrics = healthMetrics,
            latestMetric = latestMetric,
            syncIntervalMinutes = syncIntervalMinutes.toInt(),
            onOpenAnomaly = { currentScreen = Screen.Anomaly },
            onOpenTrends = { currentScreen = Screen.Trends },
            onOpenSettings = { currentScreen = Screen.Settings },
            onOpenManualEntry = { currentScreen = Screen.ManualEntry },
            onOpenExport = { currentScreen = Screen.Export },
            anomalyMetric = anomalyMetric,
            isServiceRunning = isServiceRunning,
            healthRepository = healthRepository,
            defaultUserId = defaultUserId,
            defaultDeviceId = defaultDeviceId,
            localAnomalyDetector = localAnomalyDetector
        )

        Screen.Anomaly -> AnomalyAlertScreen(
            anomaly = anomalyMetric,
            averageHeartRate = averageHeartRate,
            onAcknowledge = { currentScreen = Screen.Home },
            onViewHistory = { currentScreen = Screen.Trends }
        )

        Screen.Trends -> TrendsScreen(
            metrics = healthMetrics,
            onBack = { currentScreen = Screen.Home }
        )

        Screen.Settings -> SettingsScreen(
            syncInterval = syncIntervalMinutes,
            notificationsEnabled = notificationsEnabled,
            hapticsEnabled = hapticsEnabled,
            apiEndpoint = apiEndpoint,
            dataRetentionDays = dataRetentionDays,
            onSyncIntervalChange = { syncIntervalMinutes = it },
            onNotificationsToggle = { notificationsEnabled = it },
            onHapticsToggle = { hapticsEnabled = it },
            onApiEndpointChange = { apiEndpoint = it },
            onDataRetentionChange = { dataRetentionDays = it },
            onApply = { chosenInterval ->
                val newState = SettingsState(
                    syncIntervalMinutes = chosenInterval.toInt(),
                    notificationsEnabled = notificationsEnabled,
                    hapticsEnabled = hapticsEnabled,
                    apiEndpoint = apiEndpoint,
                    dataRetentionDays = dataRetentionDays.toInt()
                )
                scope.launch { onSaveSettings(newState) }
                onScheduleSyncChange(chosenInterval.toInt())
                currentScreen = Screen.Home
            },
            onBack = { currentScreen = Screen.Home }
        )

        Screen.ManualEntry -> ManualEntryScreen(
            defaultUserId = defaultUserId,
            defaultDeviceId = defaultDeviceId,
            healthRepository = healthRepository,
            onBack = { currentScreen = Screen.Home }
        )

        Screen.Export -> ExportScreen(
            metrics = healthMetrics,
            onBack = { currentScreen = Screen.Home }
        )
    }
}

@Composable
private fun HomeScreen(
    healthMetrics: List<HealthMetric>,
    latestMetric: HealthMetric?,
    syncIntervalMinutes: Int,
    onOpenAnomaly: () -> Unit,
    onOpenTrends: () -> Unit,
    onOpenSettings: () -> Unit,
    onOpenManualEntry: () -> Unit,
    onOpenExport: () -> Unit,
    anomalyMetric: HealthMetric?,
    isServiceRunning: Boolean,
    healthRepository: HealthRepository,
    defaultUserId: String,
    defaultDeviceId: String,
    localAnomalyDetector: LocalAnomalyDetector
) {
    val listState = rememberScalingLazyListState()
    val scope = rememberCoroutineScope()
    val unsyncedCount = healthMetrics.count { !it.isSynced }

    Scaffold(timeText = { TimeText() }) {
        ScalingLazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colors.background),
            state = listState,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            item { Spacer(modifier = Modifier.height(28.dp)) }

            item {
                Text(
                    text = "Health Monitor",
                    style = MaterialTheme.typography.title3,
                    color = MaterialTheme.colors.primary,
                    textAlign = TextAlign.Center
                )
            }

            item { Spacer(modifier = Modifier.height(12.dp)) }

            item {
                WearCard(
                    modifier = Modifier.fillMaxWidth(0.9f),
                    onClick = {}
                ) {
                    Column(
                        modifier = Modifier.padding(8.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = if (isServiceRunning) "● " else "○ ",
                                color = if (isServiceRunning) Color(0xFF2ECC71) else Color.Gray,
                                fontSize = 16.sp
                            )
                            Text(
                                text = if (isServiceRunning) "Background Monitoring" else "Service Stopped",
                                color = if (isServiceRunning) Color(0xFF2ECC71) else Color.Gray,
                                style = MaterialTheme.typography.caption1,
                                fontWeight = FontWeight.Bold
                            )
                        }
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = "Auto-running 24/7",
                            style = MaterialTheme.typography.caption2,
                            color = Color.Gray
                        )
                    }
                }
            }

            item { Spacer(modifier = Modifier.height(6.dp)) }

            item {
                Row(
                    modifier = Modifier.fillMaxWidth(0.9f),
                    horizontalArrangement = Arrangement.SpaceEvenly
                ) {
                    Text(
                        text = "☁️ Sync: ${syncIntervalMinutes}m",
                        style = MaterialTheme.typography.caption2,
                        color = Color.Gray
                    )
                    Text(
                        text = if (unsyncedCount > 0) "⏳ $unsyncedCount pending" else "✓ Synced",
                        style = MaterialTheme.typography.caption2,
                        color = if (unsyncedCount > 0) Color(0xFFF39C12) else Color(0xFF2ECC71)
                    )
                }
            }

            item { Spacer(modifier = Modifier.height(10.dp)) }

            if (latestMetric != null) {
                item {
                    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
                        Text(text = "❤️", style = MaterialTheme.typography.display1)
                        val hrValue = latestMetric.heartRate?.toInt() ?: 0
                        Text(text = "$hrValue", style = MaterialTheme.typography.display1, color = Color(0xFFE74C3C))
                        Text(text = "BPM", style = MaterialTheme.typography.caption1, color = Color.Gray)
                    }
                }

                item { Spacer(modifier = Modifier.height(12.dp)) }

                item {
                    Row(
                        modifier = Modifier.fillMaxWidth(0.9f),
                        horizontalArrangement = Arrangement.SpaceEvenly
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text(text = "🚶")
                            Text(text = "${latestMetric.steps ?: 0}", color = Color(0xFF3498DB))
                            Text(text = "steps", style = MaterialTheme.typography.caption2, color = Color.Gray)
                        }

                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text(text = "🔥")
                            val calValue = latestMetric.calories?.toInt() ?: 0
                            Text(text = "$calValue", color = Color(0xFFF39C12))
                            Text(text = "kcal", style = MaterialTheme.typography.caption2, color = Color.Gray)
                        }
                    }
                }

                item { Spacer(modifier = Modifier.height(12.dp)) }

                if (latestMetric.batteryLevel != null) {
                    item {
                        val batteryColor = if (latestMetric.batteryLevel < 20) Color(0xFFE74C3C) else Color.Gray
                        Text(text = "🔋 ${latestMetric.batteryLevel}%", style = MaterialTheme.typography.caption2, color = batteryColor)
                    }
                    item { Spacer(modifier = Modifier.height(6.dp)) }
                }

                item {
                    Text(text = "${healthMetrics.size} metrics stored", style = MaterialTheme.typography.caption2, color = Color.Gray)
                }

                item { Spacer(modifier = Modifier.height(12.dp)) }

                if (anomalyMetric != null) {
                    item {
                        Chip(
                            modifier = Modifier.fillMaxWidth(0.9f),
                            onClick = onOpenAnomaly,
                            label = { Text("Anomaly: ${(anomalyMetric.heartRate?.toInt() ?: 0)} BPM") },
                            secondaryLabel = { Text("Tap to view details") },
                            icon = { Text("⚠️") }
                        )
                    }
                    item { Spacer(modifier = Modifier.height(10.dp)) }
                }

                item {
                    Text(text = "Recent History", style = MaterialTheme.typography.caption1, color = MaterialTheme.colors.primary)
                }

                item { Spacer(modifier = Modifier.height(6.dp)) }

                items(healthMetrics.take(5)) { metric ->
                    val displayHr = metric.heartRate?.toInt() ?: 0
                    val displaySteps = metric.steps ?: 0
                    val displayTime = formatTime(metric.timestamp)

                    RegularCard(
                        modifier = Modifier.fillMaxWidth(0.9f).padding(vertical = 2.dp),
                        onClick = {}
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(8.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(text = "$displayHr BPM", style = MaterialTheme.typography.caption1, color = Color(0xFFE74C3C))
                                Text(text = displayTime, style = MaterialTheme.typography.caption2, color = Color.Gray)
                            }
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text(text = "$displaySteps👣 ", style = MaterialTheme.typography.caption2, color = Color(0xFF3498DB))
                                Text(text = if (metric.isSynced) "✓" else "⏳", color = if (metric.isSynced) Color(0xFF2ECC71) else Color.Gray)
                            }
                        }
                    }
                }
            } else {
                item { Text(text = "Waiting for data...", color = Color.Gray) }
            }

            item { Spacer(modifier = Modifier.height(12.dp)) }

            item {
                Row(modifier = Modifier.fillMaxWidth(0.9f), horizontalArrangement = Arrangement.SpaceEvenly) {
                    Chip(onClick = onOpenTrends, label = { Text("Trends") }, modifier = Modifier.weight(1f).padding(horizontal = 2.dp))
                    Chip(onClick = onOpenSettings, label = { Text("Settings") }, modifier = Modifier.weight(1f).padding(horizontal = 2.dp))
                }
            }

            item { Spacer(modifier = Modifier.height(6.dp)) }

            item {
                Row(modifier = Modifier.fillMaxWidth(0.9f), horizontalArrangement = Arrangement.SpaceEvenly) {
                    Chip(onClick = onOpenManualEntry, label = { Text("Manual") }, modifier = Modifier.weight(1f).padding(horizontal = 2.dp))
                    Chip(onClick = onOpenExport, label = { Text("Export") }, modifier = Modifier.weight(1f).padding(horizontal = 2.dp))
                }
            }

            item { Spacer(modifier = Modifier.height(6.dp)) }

            item {
                Chip(
                    onClick = {
                        kotlinx.coroutines.MainScope().launch {
                            createTestAnomaly(healthRepository, defaultUserId, defaultDeviceId, localAnomalyDetector)
                        }
                    },
                    label = { Text("Test Anomaly") },
                    modifier = Modifier.fillMaxWidth(0.9f),
                    icon = { Text("⚠️") }
                )
            }

            item { Spacer(modifier = Modifier.height(28.dp)) }
        }
    }
}

@Composable
private fun AnomalyAlertScreen(
    anomaly: HealthMetric?,
    averageHeartRate: Float?,
    onAcknowledge: () -> Unit,
    onViewHistory: () -> Unit
) {
    val listState = rememberScalingLazyListState()

    // Collect anomaly reasons safely outside of ScalingLazyColumn DSL
    val reasons: List<String> = remember(anomaly) {
        anomaly?.safeAnomalyReasons() ?: emptyList()
    }

    Scaffold(timeText = { TimeText() }) {
        ScalingLazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colors.background),
            state = listState,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            item { Spacer(modifier = Modifier.height(24.dp)) }
            item {
                Text("Anomaly Alert", style = MaterialTheme.typography.title3, color = Color(0xFFE74C3C))
            }
            item { Spacer(modifier = Modifier.height(8.dp)) }

            if (anomaly != null) {
                item {
                    WearCard(modifier = Modifier.fillMaxWidth(0.9f), onClick = {}) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text(text = "⚠️ Anomaly Detected", fontWeight = FontWeight.Bold)
                            Spacer(modifier = Modifier.height(6.dp))
                            Text(text = "HR: ${(anomaly.heartRate ?: 0f).toInt()} BPM", color = Color(0xFFE74C3C))
                            Text(text = "Steps: ${anomaly.steps ?: 0}", color = Color.Gray, style = MaterialTheme.typography.caption2)
                            averageHeartRate?.let { avg ->
                                Text(text = "Avg: ${avg.toInt()} BPM", style = MaterialTheme.typography.caption2, color = Color.LightGray)
                            }
                            Text(text = "Time: ${formatTime(anomaly.timestamp)}", style = MaterialTheme.typography.caption2, color = Color.Gray)
                        }
                    }
                }

                // Show anomaly reasons if available — uses items() DSL, no forEach inside item {}
                if (reasons.isNotEmpty()) {
                    item { Spacer(modifier = Modifier.height(6.dp)) }

                    item {
                        WearCard(modifier = Modifier.fillMaxWidth(0.9f), onClick = {}) {
                            Column(modifier = Modifier.padding(12.dp)) {
                                Text(
                                    text = "Why?",
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFFF39C12),
                                    style = MaterialTheme.typography.caption1
                                )
                                Spacer(modifier = Modifier.height(4.dp))
                                // Render all reasons inside a single item using Column — safe for Composables
                                Column {
                                    reasons.forEach { reason ->
                                        Text(
                                            text = "• $reason",
                                            style = MaterialTheme.typography.caption2,
                                            color = Color.LightGray
                                        )
                                        Spacer(modifier = Modifier.height(2.dp))
                                    }
                                }
                            }
                        }
                    }
                }
            } else {
                item { Text("No anomaly detected", color = Color.Gray) }
            }

            item { Spacer(modifier = Modifier.height(10.dp)) }

            item {
                Row(
                    modifier = Modifier.fillMaxWidth(0.9f),
                    horizontalArrangement = Arrangement.SpaceEvenly
                ) {
                    Button(
                        onClick = onAcknowledge,
                        modifier = Modifier.fillMaxWidth(0.45f)
                    ) { Text("Acknowledge", modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)) }
                    Button(
                        onClick = onViewHistory,
                        modifier = Modifier.fillMaxWidth(0.45f)
                    ) { Text("View Details", modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)) }
                }
            }

            item { Spacer(modifier = Modifier.height(28.dp)) }
        }
    }
}

@Composable
private fun TrendsScreen(
    metrics: List<HealthMetric>,
    onBack: () -> Unit
) {
    val listState = rememberScalingLazyListState()
    val heartRates = metrics.take(20).mapNotNull { it.heartRate }
    val average = heartRates.takeIf { it.isNotEmpty() }?.average()
    val maxValue = heartRates.maxOrNull()
    val minValue = heartRates.minOrNull()

    Scaffold(timeText = { TimeText() }) {
        ScalingLazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colors.background),
            state = listState,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            item { Spacer(modifier = Modifier.height(20.dp)) }
            item { Text("Heart Rate Trends", style = MaterialTheme.typography.title3, color = MaterialTheme.colors.primary) }
            item { Spacer(modifier = Modifier.height(8.dp)) }

            item {
                TrendChart(
                    values = heartRates,
                    modifier = Modifier
                        .fillMaxWidth(0.9f)
                        .height(120.dp)
                        .background(Color(0xFF111111), RoundedCornerShape(12.dp))
                        .padding(8.dp)
                )
            }

            item { Spacer(modifier = Modifier.height(8.dp)) }

            average?.let {
                item { Text("Avg: ${it.toInt()} BPM", style = MaterialTheme.typography.caption1, color = Color.LightGray) }
            }
            maxValue?.let {
                item { Text("Max: ${it.toInt()} BPM", style = MaterialTheme.typography.caption2, color = Color(0xFFE74C3C)) }
            }
            minValue?.let {
                item { Text("Min: ${it.toInt()} BPM", style = MaterialTheme.typography.caption2, color = Color(0xFF2ECC71)) }
            }

            item { Spacer(modifier = Modifier.height(6.dp)) }

            item {
                Button(
                    onClick = onBack,
                    modifier = Modifier.fillMaxWidth(0.8f)
                ) { Text("Back", modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)) }
            }
            item { Spacer(modifier = Modifier.height(24.dp)) }
        }
    }
}

@Composable
private fun TrendChart(values: List<Float>, modifier: Modifier = Modifier) {
    if (values.isEmpty()) {
        Text("No data yet", color = Color.Gray, style = MaterialTheme.typography.caption2, modifier = Modifier.padding(8.dp))
        return
    }

    val maxValue = values.maxOrNull() ?: 0f
    val minValue = values.minOrNull() ?: 0f
    val range = (maxValue - minValue).takeIf { it != 0f } ?: 1f

    Canvas(modifier = modifier) {
        val path = Path()
        values.forEachIndexed { index, value ->
            val x = if (values.size == 1) size.width / 2 else size.width * index / (values.size - 1).toFloat()
            val normalized = (value - minValue) / range
            val y = size.height * (1f - normalized)
            if (index == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }

        drawPath(
            path = path,
            color = Color(0xFFE74C3C),
            style = Stroke(width = 6f, cap = StrokeCap.Round)
        )
    }
}

@Composable
private fun SettingsScreen(
    syncInterval: Float,
    notificationsEnabled: Boolean,
    hapticsEnabled: Boolean,
    apiEndpoint: String,
    dataRetentionDays: Float,
    onSyncIntervalChange: (Float) -> Unit,
    onNotificationsToggle: (Boolean) -> Unit,
    onHapticsToggle: (Boolean) -> Unit,
    onApiEndpointChange: (String) -> Unit,
    onDataRetentionChange: (Float) -> Unit,
    onApply: (Float) -> Unit,
    onBack: () -> Unit
) {
    val listState = rememberScalingLazyListState()
    Scaffold(timeText = { TimeText() }) {
        ScalingLazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colors.background),
            state = listState,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            item { Spacer(modifier = Modifier.height(18.dp)) }
            item { Text("Settings", style = MaterialTheme.typography.title3, color = MaterialTheme.colors.primary) }
            item { Spacer(modifier = Modifier.height(6.dp)) }

            item {
                WearCard(
                    modifier = Modifier.fillMaxWidth(0.9f),
                    onClick = {}
                ) {
                    Column(
                        modifier = Modifier.padding(8.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = "ℹ️ Continuous Monitoring",
                            style = MaterialTheme.typography.caption1,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF3498DB)
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = "Health data collected 24/7 in background",
                            style = MaterialTheme.typography.caption2,
                            color = Color.Gray,
                            textAlign = TextAlign.Center
                        )
                    }
                }
            }
            item { Spacer(modifier = Modifier.height(10.dp)) }

            item { Text("Sync Interval (${syncInterval.toInt()} min)", style = MaterialTheme.typography.caption1) }
            item {
                Slider(
                    value = syncInterval,
                    onValueChange = onSyncIntervalChange,
                    valueRange = 15f..60f,
                    steps = 3,
                    modifier = Modifier.fillMaxWidth(0.9f)
                )
            }

            item { ToggleChip(checked = notificationsEnabled, onCheckedChange = onNotificationsToggle, label = { Text("Notifications") }, toggleControl = { }) }
            item { ToggleChip(checked = hapticsEnabled, onCheckedChange = onHapticsToggle, label = { Text("Haptics for alerts") }, toggleControl = { }) }

            item { Spacer(modifier = Modifier.height(6.dp)) }
            item { Text("API Endpoint", style = MaterialTheme.typography.caption1) }
            item {
                ComposeTextField(
                    value = apiEndpoint,
                    onValueChange = onApiEndpointChange,
                    label = { Text("Base URL") },
                    modifier = Modifier.fillMaxWidth(0.9f)
                )
            }

            item { Spacer(modifier = Modifier.height(6.dp)) }
            item { Text("Data retention (${dataRetentionDays.toInt()} days)", style = MaterialTheme.typography.caption1) }
            item {
                Slider(
                    value = dataRetentionDays,
                    onValueChange = onDataRetentionChange,
                    valueRange = 3f..30f,
                    steps = 5,
                    modifier = Modifier.fillMaxWidth(0.9f)
                )
            }

            item { Spacer(modifier = Modifier.height(10.dp)) }
            item {
                Button(
                    onClick = { onApply(syncInterval) },
                    modifier = Modifier.fillMaxWidth(0.8f)
                ) { Text("Apply", modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)) }
            }
            item { Spacer(modifier = Modifier.height(6.dp)) }
            item {
                Button(
                    onClick = onBack,
                    modifier = Modifier.fillMaxWidth(0.8f)
                ) { Text("Back", modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)) }
            }
            item { Spacer(modifier = Modifier.height(22.dp)) }
        }
    }
}

@Composable
private fun ManualEntryScreen(
    defaultUserId: String,
    defaultDeviceId: String,
    healthRepository: HealthRepository,
    onBack: () -> Unit
) {
    val scope = rememberCoroutineScope()
    var heartRate by rememberSaveable { mutableStateOf(80f) }
    var steps by rememberSaveable { mutableStateOf(0f) }
    var calories by rememberSaveable { mutableStateOf(0f) }
    var saveMessage by remember { mutableStateOf("") }

    val listState = rememberScalingLazyListState()
    Scaffold(timeText = { TimeText() }) {
        ScalingLazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colors.background),
            state = listState,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            item { Spacer(modifier = Modifier.height(18.dp)) }
            item { Text("Manual Entry", style = MaterialTheme.typography.title3, color = MaterialTheme.colors.primary) }
            item { Spacer(modifier = Modifier.height(10.dp)) }

            item { Text("Heart Rate: ${heartRate.toInt()} BPM", style = MaterialTheme.typography.caption1) }
            item {
                Slider(
                    value = heartRate,
                    onValueChange = { heartRate = it },
                    valueRange = 40f..200f,
                    steps = 8,
                    modifier = Modifier.fillMaxWidth(0.9f)
                )
            }

            item { Text("Steps: ${steps.toInt()}", style = MaterialTheme.typography.caption1) }
            item {
                Slider(
                    value = steps,
                    onValueChange = { steps = it },
                    valueRange = 0f..10000f,
                    steps = 10,
                    modifier = Modifier.fillMaxWidth(0.9f)
                )
            }

            item { Text("Calories: ${calories.toInt()} kcal", style = MaterialTheme.typography.caption1) }
            item {
                Slider(
                    value = calories,
                    onValueChange = { calories = it },
                    valueRange = 0f..2000f,
                    steps = 10,
                    modifier = Modifier.fillMaxWidth(0.9f)
                )
            }

            item { Spacer(modifier = Modifier.height(8.dp)) }

            item {
                Button(
                    onClick = {
                        scope.launch {
                            val result = healthRepository.saveMetric(
                                HealthMetric(
                                    userId = defaultUserId,
                                    timestamp = System.currentTimeMillis(),
                                    heartRate = heartRate,
                                    steps = steps.toInt(),
                                    calories = calories,
                                    deviceId = defaultDeviceId,
                                    isSynced = false
                                )
                            )
                            saveMessage = if (result.isSuccess) "Saved locally" else "Failed to save"
                        }
                    },
                    modifier = Modifier.fillMaxWidth(0.8f)
                ) {
                    Text("Save Measurement", modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp))
                }
            }

            if (saveMessage.isNotBlank()) {
                item { Text(saveMessage, color = Color.LightGray, style = MaterialTheme.typography.caption2) }
            }

            item { Spacer(modifier = Modifier.height(8.dp)) }
            item {
                Button(
                    onClick = onBack,
                    modifier = Modifier.fillMaxWidth(0.8f)
                ) { Text("Back", modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)) }
            }
            item { Spacer(modifier = Modifier.height(22.dp)) }
        }
    }
}

@Composable
private fun ExportScreen(
    metrics: List<HealthMetric>,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val recentMetrics = remember(metrics) { metrics.take(20) }
    val csv = remember(recentMetrics) { buildCsv(recentMetrics) }
    val listState = rememberScalingLazyListState()

    Scaffold(timeText = { TimeText() }) {
        ScalingLazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colors.background),
            state = listState,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            item { Spacer(modifier = Modifier.height(18.dp)) }
            item { Text("Export & Share", style = MaterialTheme.typography.title3, color = MaterialTheme.colors.primary) }
            item { Spacer(modifier = Modifier.height(8.dp)) }
            item { Text("Share last ${recentMetrics.size} metrics as CSV", style = MaterialTheme.typography.caption2, color = Color.Gray) }
            item { Spacer(modifier = Modifier.height(10.dp)) }

            item {
                Button(
                    onClick = {
                        val intent = Intent(Intent.ACTION_SEND).apply {
                            type = "text/csv"
                            putExtra(Intent.EXTRA_SUBJECT, "Health metrics export")
                            putExtra(Intent.EXTRA_TEXT, csv)
                        }
                        context.startActivity(Intent.createChooser(intent, "Share health data"))
                    },
                    enabled = recentMetrics.isNotEmpty(),
                    modifier = Modifier.fillMaxWidth(0.8f)
                ) {
                    Text(
                        if (recentMetrics.isEmpty()) "No data" else "Share CSV",
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)
                    )
                }
            }

            item { Spacer(modifier = Modifier.height(8.dp)) }
            item {
                Button(
                    onClick = onBack,
                    modifier = Modifier.fillMaxWidth(0.8f)
                ) { Text("Back", modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)) }
            }
            item { Spacer(modifier = Modifier.height(22.dp)) }
        }
    }
}

private fun buildCsv(metrics: List<HealthMetric>): String {
    if (metrics.isEmpty()) return "No data available"
    val header = "timestamp,heartRate,steps,calories,isSynced"
    val rows = metrics.joinToString("\n") { metric ->
        val ts = formatTime(metric.timestamp)
        val hr = metric.heartRate ?: 0f
        val st = metric.steps ?: 0
        val cal = metric.calories ?: 0f
        "$ts,$hr,$st,$cal,${metric.isSynced}"
    }
    return "$header\n$rows"
}

private const val ANOMALY_CHANNEL_ID = "anomaly_alerts"

private fun sendAnomalyNotification(context: Context, anomaly: HealthMetric?) {
    if (anomaly == null) return

    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
        val channel = NotificationChannel(
            ANOMALY_CHANNEL_ID,
            "Anomaly Alerts",
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Alerts when elevated heart rate is detected"
        }
        val notificationManager = context.getSystemService(NotificationManager::class.java)
        notificationManager?.createNotificationChannel(channel)
    }

    // Use first anomaly reason if available, otherwise generic HR text
    val reasonText = anomaly.safeAnomalyReasons().firstOrNull()
        ?: "HR ${(anomaly.heartRate ?: 0f).toInt()} BPM at ${formatTime(anomaly.timestamp)}"

    val builder = NotificationCompat.Builder(context, ANOMALY_CHANNEL_ID)
        .setSmallIcon(android.R.drawable.ic_dialog_alert)
        .setContentTitle("Health Anomaly Detected")
        .setContentText(reasonText)
        .setPriority(NotificationCompat.PRIORITY_HIGH)
        .setAutoCancel(true)

    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
        ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
    ) {
        NotificationManagerCompat.from(context).notify(anomaly.id.toInt(), builder.build())
    }
}

private enum class Screen { Home, Anomaly, Trends, Settings, ManualEntry, Export }

private fun formatTime(timestamp: Long): String {
    val sdf = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault())
    return sdf.format(java.util.Date(timestamp))
}

private fun isHealthServiceRunning(context: Context): Boolean {
    val activityManager = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
    @Suppress("DEPRECATION")
    return activityManager.getRunningServices(Int.MAX_VALUE).any { serviceInfo ->
        serviceInfo.service.className == HealthMonitoringService::class.java.name
    }
}

private suspend fun createTestAnomaly(
    healthRepository: HealthRepository,
    userId: String,
    deviceId: String,
    anomalyDetector: LocalAnomalyDetector
) {
    Log.d("TestAnomaly", "Creating test anomaly metric with HR=155 BPM (threshold=140)")

    // Build the metric first (without reasons) so we can pass it to the detector
    val baseMetric = HealthMetric(
        userId = userId,
        timestamp = System.currentTimeMillis(),
        heartRate = 155f,
        steps = 1200,
        calories = 95f,
        distance = 0.8f,
        deviceId = deviceId,
        isSynced = false,
        batteryLevel = 85
    )

    // Compute reasons and attach them so the UI can display the "Why?" card
    val reasons = anomalyDetector.getAnomalyReasons(baseMetric)
    val testMetric = baseMetric.apply { anomalyReasons = reasons }

    Log.d("TestAnomaly", "Anomaly reasons: $reasons")

    val result = healthRepository.saveMetric(testMetric)
    if (result.isSuccess) {
        Log.d("TestAnomaly", "✓ Test anomaly metric saved successfully!")
        Log.d("TestAnomaly", "Expected behavior: Anomaly Alert screen should appear + haptics + notification")
        val syncResult = healthRepository.syncMetricsToCloud()
        if (syncResult.isSuccess) {
            Log.d("TestAnomaly", "? Synced to cloud!")
        } else {
            Log.e("TestAnomaly", "? Cloud sync failed: ${syncResult.exceptionOrNull()?.message}")
        }
    } else {
        Log.e("TestAnomaly", "✗ Failed to create test anomaly: ${result.exceptionOrNull()?.message}")
    }
}




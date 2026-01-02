package com.capstone.healthmonitor.wear.presentation.ui

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.wear.compose.foundation.lazy.ScalingLazyColumn
import androidx.wear.compose.foundation.lazy.rememberScalingLazyListState
import androidx.wear.compose.material.*
import androidx.work.*
import com.capstone.healthmonitor.wear.data.repository.HealthRepository
import com.capstone.healthmonitor.wear.domain.model.HealthMetric
import com.capstone.healthmonitor.wear.service.DataSyncWorker
import com.capstone.healthmonitor.wear.service.HealthMonitoringService
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.emptyFlow
import java.util.concurrent.TimeUnit
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject
    lateinit var healthRepository: HealthRepository

    companion object {
        private const val TAG = "MainActivity"
        private val REQUIRED_PERMISSIONS = arrayOf(
            Manifest.permission.BODY_SENSORS,
            Manifest.permission.ACTIVITY_RECOGNITION
        )
    }

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.values.all { it }
        if (allGranted) {
            startMonitoring()
        } else {
            Log.e(TAG, "Permissions not granted")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            HealthMonitorTheme {
                HealthMonitorScreen(
                    onStartMonitoring = { checkPermissionsAndStart() },
                    healthMetricsFlow = healthRepository.getLatestMetrics(10)
                )
            }
        }
    }

    private fun checkPermissionsAndStart() {
        val permissionsToRequest = REQUIRED_PERMISSIONS.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }

        if (permissionsToRequest.isEmpty()) {
            startMonitoring()
        } else {
            permissionLauncher.launch(permissionsToRequest.toTypedArray())
        }
    }

    private fun startMonitoring() {
        // Start foreground service
        val serviceIntent = Intent(this, HealthMonitoringService::class.java)
        ContextCompat.startForegroundService(this, serviceIntent)

        // Schedule periodic data sync
        scheduleDataSync()

        Log.d(TAG, "Health monitoring started")
    }

    private fun scheduleDataSync() {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val syncWorkRequest = PeriodicWorkRequestBuilder<DataSyncWorker>(
            15, TimeUnit.MINUTES // Minimum interval is 15 minutes
        )
            .setConstraints(constraints)
            .setBackoffCriteria(
                BackoffPolicy.EXPONENTIAL,
                WorkRequest.MIN_BACKOFF_MILLIS,
                TimeUnit.MILLISECONDS
            )
            .build()

        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            DataSyncWorker.WORK_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
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
    onStartMonitoring: () -> Unit,
    healthMetricsFlow: Flow<List<HealthMetric>>
) {
    var isMonitoring by remember { mutableStateOf(false) }
    val healthMetrics by healthMetricsFlow.collectAsState(initial = emptyList())
    val latestMetric = healthMetrics.firstOrNull()
    val listState = rememberScalingLazyListState()

    Scaffold(
        timeText = { TimeText() }
    ) {
ScalingLazyColumn([[]]
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colors.background),
            state = listState,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            item {
                Spacer(modifier = Modifier.height(32.dp))
            }
            
            item {
                Text(
                    text = "Health Monitor",
                    style = MaterialTheme.typography.title3,
                    color = MaterialTheme.colors.primary,
                    textAlign = TextAlign.Center
                )
            }

            item {
                Spacer(modifier = Modifier.height(16.dp))
            }

            if (!isMonitoring) {
                item {
                    Button(
                        onClick = {
                            onStartMonitoring()
                            isMonitoring = true
                        },
                        modifier = Modifier.fillMaxWidth(0.8f)
                    ) {
                        Text("Start Monitoring")
                    }
                }
            } else {
                item {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.Center
                    ) {
                        Text(
                            text = "● ",
                            style = MaterialTheme.typography.body1,
                            color = MaterialTheme.colors.secondary
                        )
                        Text(
                            text = "Monitoring Active",
                            style = MaterialTheme.typography.body1,
                            color = MaterialTheme.colors.secondary
                        )
                    }
                }

                item {
                    Spacer(modifier = Modifier.height(8.dp))
                }

                // Sync Status
                item {
                    val unsyncedCount = healthMetrics.count { !it.isSynced }
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.Center
                    ) {
                        Text(
                            text = if (unsyncedCount > 0) "⏳ $unsyncedCount pending sync" else "✓ All synced",
                            style = MaterialTheme.typography.caption2,
                            color = if (unsyncedCount > 0) Color(0xFFF39C12) else Color(0xFF2ECC71)
                        )
                    }
                }

                item {
                    Spacer(modifier = Modifier.height(12.dp))
                }

                // Display latest health metrics
                if (latestMetric != null) {
                    // Heart Rate - Large Display
                    item {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                text = "❤️",
                                style = MaterialTheme.typography.display1
                            )
                            Text(
                                text = "${latestMetric.heartRate?.toInt() ?: 0}",
                                style = MaterialTheme.typography.display1,
                                color = Color(0xFFE74C3C)
                            )
                            Text(
                                text = "BPM",
                                style = MaterialTheme.typography.caption1,
                                color = Color.Gray
                            )
                        }
                    }

                    item {
                        Spacer(modifier = Modifier.height(12.dp))
                    }

                    // Steps and Calories
                    item {
                        Row(
                            modifier = Modifier.fillMaxWidth(0.9f),
                            horizontalArrangement = Arrangement.SpaceEvenly
                        ) {
                            // Steps
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Text(
                                    text = "🚶",
                                    style = MaterialTheme.typography.body1
                                )
                                Text(
                                    text = "${latestMetric.steps ?: 0}",
                                    style = MaterialTheme.typography.title3,
                                    color = Color(0xFF3498DB)
                                )
                                Text(
                                    text = "steps",
                                    style = MaterialTheme.typography.caption2,
                                    color = Color.Gray
                                )
                            }

                            // Calories
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Text(
                                    text = "🔥",
                                    style = MaterialTheme.typography.body1
                                )
                                Text(
                                    text = "${latestMetric.calories?.toInt() ?: 0}",
                                    style = MaterialTheme.typography.title3,
                                    color = Color(0xFFF39C12)
                                )
                                Text(
                                    text = "kcal",
                                    style = MaterialTheme.typography.caption2,
                                    color = Color.Gray
                                )
                            }
                        }
                    }

                    item {
                        Spacer(modifier = Modifier.height(12.dp))
                    }

                    // Battery Level (if available)
                    if (latestMetric.batteryLevel != null) {
                        item {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.Center
                            ) {
                                Text(
                                    text = "🔋 ${latestMetric.batteryLevel}%",
                                    style = MaterialTheme.typography.caption2,
                                    color = if (latestMetric.batteryLevel!! < 20) Color(0xFFE74C3C) else Color.Gray
                                )
                            }
                        }

                        item {
                            Spacer(modifier = Modifier.height(8.dp))
                        }
                    }

                    // Data Summary
                    item {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                text = "${healthMetrics.size} metrics stored",
                                style = MaterialTheme.typography.caption2,
                                color = Color.Gray
                            )
                        }
                    }

                    item {
                        Spacer(modifier = Modifier.height(12.dp))
                    }

                    // Recent Metrics History (last 5)
                    item {
                        Text(
                            text = "Recent History",
                            style = MaterialTheme.typography.caption1,
                            color = MaterialTheme.colors.primary
                        )
                    }

                    item {
                        Spacer(modifier = Modifier.height(8.dp))
                    }

                    // Display recent metrics (last 5)
                    healthMetrics.take(5).forEach { metric ->
                        item {
                            Card(
                                modifier = Modifier
                                    .fillMaxWidth(0.9f)
                                    .padding(vertical = 2.dp),
                                onClick = { }
                            ) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(8.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Column {
                                        Text(
                                            text = "${metric.heartRate?.toInt() ?: 0} BPM",
                                            style = MaterialTheme.typography.caption1,
                                            color = Color(0xFFE74C3C)
                                        )
                                        Text(
                                            text = formatTime(metric.timestamp),
                                            style = MaterialTheme.typography.caption2,
                                            color = Color.Gray
                                        )
                                    }
                                    Row {
                                        Text(
                                            text = "${metric.steps ?: 0}👣 ",
                                            style = MaterialTheme.typography.caption2,
                                            color = Color(0xFF3498DB)
                                        )
                                        if (!metric.isSynced) {
                                            Text(
                                                text = "⏳",
                                                style = MaterialTheme.typography.caption2
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }

                } else {
                    item {
                        Text(
                            text = "Waiting for data...",
                            style = MaterialTheme.typography.caption2,
                            color = Color.Gray
                        )
                    }
                }
            }
            
            item {
                Spacer(modifier = Modifier.height(32.dp))
            }
        }
    }
}

// Helper function to format timestamp
private fun formatTime(timestamp: Long): String {
    val sdf = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault())
    return sdf.format(java.util.Date(timestamp))
}

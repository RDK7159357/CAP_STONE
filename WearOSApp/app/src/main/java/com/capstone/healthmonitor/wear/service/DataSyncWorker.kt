package com.capstone.healthmonitor.wear.service

import android.content.Context
import android.util.Log
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.capstone.healthmonitor.wear.data.repository.HealthRepository
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject

/**
 * WorkManager worker that periodically syncs health data to cloud backend
 */
@HiltWorker
class DataSyncWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted workerParams: WorkerParameters,
    private val repository: HealthRepository
) : CoroutineWorker(appContext, workerParams) {

    companion object {
        private const val TAG = "DataSyncWorker"
        const val WORK_NAME = "health_data_sync"
    }

    override suspend fun doWork(): Result {
        Log.d(TAG, "Starting data synchronization")

        return try {
            // Get unsynced count
            val unsyncedCount = repository.getUnsyncedCount()
            Log.d(TAG, "Unsynced metrics: $unsyncedCount")

            if (unsyncedCount == 0) {
                Log.d(TAG, "No data to sync")
                return Result.success()
            }

            // Sync to cloud
            val syncResult = repository.syncMetricsToCloud()

            if (syncResult.isSuccess) {
                val syncedCount = syncResult.getOrNull() ?: 0
                Log.d(TAG, "Successfully synced $syncedCount metrics")
                
                // Cleanup old data
                repository.cleanupOldData(olderThanDays = 7)
                
                Result.success()
            } else {
                Log.e(TAG, "Sync failed: ${syncResult.exceptionOrNull()?.message}")
                Result.retry()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error during sync", e)
            Result.retry()
        }
    }
}

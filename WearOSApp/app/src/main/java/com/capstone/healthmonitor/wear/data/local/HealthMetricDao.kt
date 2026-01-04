package com.capstone.healthmonitor.wear.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.capstone.healthmonitor.wear.domain.model.HealthMetric
import kotlinx.coroutines.flow.Flow

@Dao
interface HealthMetricDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMetric(metric: HealthMetric): Long

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMetrics(metrics: List<HealthMetric>)

    @Update
    suspend fun updateMetric(metric: HealthMetric)

    @Query("SELECT * FROM health_metrics WHERE isSynced = 0 ORDER BY timestamp ASC LIMIT :limit")
    suspend fun getUnsyncedMetrics(limit: Int = 100): List<HealthMetric>

    @Query("SELECT * FROM health_metrics ORDER BY timestamp DESC LIMIT :limit")
    fun getRecentMetrics(limit: Int = 50): Flow<List<HealthMetric>>

    @Query("SELECT * FROM health_metrics ORDER BY timestamp DESC LIMIT :limit")
    suspend fun getRecentMetricsSync(limit: Int = 50): List<HealthMetric>

    @Query("SELECT * FROM health_metrics WHERE timestamp >= :startTime AND timestamp <= :endTime ORDER BY timestamp ASC")
    suspend fun getMetricsByTimeRange(startTime: Long, endTime: Long): List<HealthMetric>

    @Query("UPDATE health_metrics SET isSynced = 1 WHERE id IN (:ids)")
    suspend fun markAsSynced(ids: List<Long>)

    @Query("DELETE FROM health_metrics WHERE isSynced = 1 AND timestamp < :beforeTimestamp")
    suspend fun deleteOldSyncedMetrics(beforeTimestamp: Long)

    @Query("SELECT COUNT(*) FROM health_metrics WHERE isSynced = 0")
    suspend fun getUnsyncedCount(): Int

    @Query("DELETE FROM health_metrics")
    suspend fun deleteAll()
}

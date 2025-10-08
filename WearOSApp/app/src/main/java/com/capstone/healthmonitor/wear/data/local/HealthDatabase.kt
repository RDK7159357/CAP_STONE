package com.capstone.healthmonitor.wear.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.capstone.healthmonitor.wear.domain.model.HealthMetric

@Database(
    entities = [HealthMetric::class],
    version = 1,
    exportSchema = false
)
abstract class HealthDatabase : RoomDatabase() {
    abstract fun healthMetricDao(): HealthMetricDao

    companion object {
        const val DATABASE_NAME = "health_monitor_db"
    }
}

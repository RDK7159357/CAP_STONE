package com.capstone.healthmonitor.wear.di

import android.content.Context
import androidx.room.Room
import com.capstone.healthmonitor.wear.data.local.HealthDatabase
import com.capstone.healthmonitor.wear.data.local.HealthMetricDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideHealthDatabase(@ApplicationContext context: Context): HealthDatabase {
        return Room.databaseBuilder(
            context,
            HealthDatabase::class.java,
            HealthDatabase.DATABASE_NAME
        )
            .fallbackToDestructiveMigration()
            .build()
    }

    @Provides
    @Singleton
    fun provideHealthMetricDao(database: HealthDatabase): HealthMetricDao {
        return database.healthMetricDao()
    }
}

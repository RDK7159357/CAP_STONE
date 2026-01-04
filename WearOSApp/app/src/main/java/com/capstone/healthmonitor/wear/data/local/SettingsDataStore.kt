package com.capstone.healthmonitor.wear.data.local

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStoreFile
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import androidx.datastore.preferences.core.PreferenceDataStoreFactory

/**
 * Persist user-adjustable settings for the Wear app.
 */
@Singleton
class SettingsDataStore @Inject constructor(
    @ApplicationContext context: Context
) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val dataStore: DataStore<Preferences> = PreferenceDataStoreFactory.create(
        scope = scope
    ) {
        context.preferencesDataStoreFile(DATA_STORE_NAME)
    }

    val settingsFlow: Flow<SettingsState> = dataStore.data.map { prefs ->
        SettingsState(
            syncIntervalMinutes = prefs[KEY_SYNC_INTERVAL] ?: DEFAULT_SYNC_INTERVAL_MIN,
            notificationsEnabled = prefs[KEY_NOTIFICATIONS] ?: true,
            hapticsEnabled = prefs[KEY_HAPTICS] ?: true,
            apiEndpoint = prefs[KEY_API_ENDPOINT] ?: "",
            dataRetentionDays = prefs[KEY_RETENTION_DAYS] ?: DEFAULT_RETENTION_DAYS
        )
    }

    suspend fun save(settings: SettingsState) {
        dataStore.edit { prefs ->
            prefs[KEY_SYNC_INTERVAL] = settings.syncIntervalMinutes
            prefs[KEY_NOTIFICATIONS] = settings.notificationsEnabled
            prefs[KEY_HAPTICS] = settings.hapticsEnabled
            prefs[KEY_API_ENDPOINT] = settings.apiEndpoint
            prefs[KEY_RETENTION_DAYS] = settings.dataRetentionDays
        }
    }

    companion object {
        private const val DATA_STORE_NAME = "wear_settings"
        private const val DEFAULT_SYNC_INTERVAL_MIN = 15
        private const val DEFAULT_RETENTION_DAYS = 7

        private val KEY_SYNC_INTERVAL = intPreferencesKey("sync_interval_minutes")
        private val KEY_NOTIFICATIONS = booleanPreferencesKey("notifications_enabled")
        private val KEY_HAPTICS = booleanPreferencesKey("haptics_enabled")
        private val KEY_API_ENDPOINT = stringPreferencesKey("api_endpoint")
        private val KEY_RETENTION_DAYS = intPreferencesKey("data_retention_days")
    }
}

/**
 * Snapshot of persisted settings with safe defaults.
 */
data class SettingsState(
    val syncIntervalMinutes: Int = 15,
    val notificationsEnabled: Boolean = true,
    val hapticsEnabled: Boolean = true,
    val apiEndpoint: String = "",
    val dataRetentionDays: Int = 7
)

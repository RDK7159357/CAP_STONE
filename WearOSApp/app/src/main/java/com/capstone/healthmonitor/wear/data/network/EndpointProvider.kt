package com.capstone.healthmonitor.wear.data.network

import com.capstone.healthmonitor.wear.data.local.SettingsDataStore
import javax.inject.Inject
import javax.inject.Singleton
import java.util.concurrent.atomic.AtomicReference
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

/**
 * Holds the current base URL for API calls, updating when settings change.
 */
@Singleton
class EndpointProvider @Inject constructor(
    settingsDataStore: SettingsDataStore
) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val baseUrlRef = AtomicReference(ensureTrailingSlash(ApiConfig.BASE_URL))

    init {
        scope.launch {
            settingsDataStore.settingsFlow.collectLatest { settings ->
                val userUrl = settings.apiEndpoint.trim()
                val resolved = if (userUrl.isNotBlank()) userUrl else ApiConfig.BASE_URL
                val normalized = ensureTrailingSlash(resolved)
                if (normalized != baseUrlRef.get()) {
                    baseUrlRef.set(normalized)
                }
            }
        }
    }

    fun getBaseUrl(): String = baseUrlRef.get()

    private fun ensureTrailingSlash(url: String): String = if (url.endsWith("/")) url else "$url/"
}

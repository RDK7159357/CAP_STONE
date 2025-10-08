package com.capstone.healthmonitor.wear.data.network

import com.capstone.healthmonitor.wear.domain.model.HealthMetricRequest
import com.capstone.healthmonitor.wear.domain.model.HealthMetricResponse
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST

/**
 * Retrofit API interface for cloud backend communication
 */
interface HealthApiService {

    @POST(ApiConfig.ENDPOINT_INGEST)
    suspend fun ingestHealthData(
        @Body request: HealthMetricRequest,
        @Header("X-API-Key") apiKey: String = ApiConfig.API_KEY
    ): Response<HealthMetricResponse>

    @POST(ApiConfig.ENDPOINT_SYNC)
    suspend fun syncHealthData(
        @Body requests: List<HealthMetricRequest>,
        @Header("X-API-Key") apiKey: String = ApiConfig.API_KEY
    ): Response<HealthMetricResponse>

    @GET(ApiConfig.ENDPOINT_STATUS)
    suspend fun checkStatus(
        @Header("X-API-Key") apiKey: String = ApiConfig.API_KEY
    ): Response<Map<String, Any>>
}

package com.capstone.healthmonitor.wear.data.network

/**
 * API Configuration
 * Replace these values with your actual cloud backend endpoints
 */
object ApiConfig {
    // TODO: Replace with your actual API endpoint after deploying cloud backend
    const val BASE_URL = "https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/prod/"
    
    // Alternative for Google Cloud
    // const val BASE_URL = "https://us-central1-your-project-id.cloudfunctions.net/"
    
    // API Key for authentication (if using API key authentication)
    const val API_KEY = "your-api-key-here"
    
    // Timeouts
    const val CONNECT_TIMEOUT = 30L // seconds
    const val READ_TIMEOUT = 30L // seconds
    const val WRITE_TIMEOUT = 30L // seconds
    
    // Endpoints
    const val ENDPOINT_INGEST = "health-data/ingest"
    const val ENDPOINT_SYNC = "health-data/sync"
    const val ENDPOINT_STATUS = "health-data/status"
}

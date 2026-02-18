package com.capstone.healthmonitor.wear.data.network

/**
 * API Configuration
 * Replace these values with your actual cloud backend endpoints
 */
object ApiConfig {
    // AWS Lambda API Gateway endpoint (ap-south-2)
    const val BASE_URL = "https://u8tkgz3vsf.execute-api.ap-south-2.amazonaws.com/prod/"
    
    // API Key for authentication
    const val API_KEY = "27tpgpLoMk7A8mDknvE8S8AhzwBeS6fm1U7KpQhT"
    
    // Timeouts
    const val CONNECT_TIMEOUT = 30L // seconds
    const val READ_TIMEOUT = 30L // seconds
    const val WRITE_TIMEOUT = 30L // seconds
    
    // Endpoints
    const val ENDPOINT_INGEST = "health-data/ingest"
    const val ENDPOINT_SYNC = "health-data/sync"
    const val ENDPOINT_STATUS = "health-data/status"
}

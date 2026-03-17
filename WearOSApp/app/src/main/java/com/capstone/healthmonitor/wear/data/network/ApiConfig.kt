package com.capstone.healthmonitor.wear.data.network

object ApiConfig {
    const val BASE_URL = "https://t6rlkix2lg.execute-api.ap-south-2.amazonaws.com/prod/"
    const val API_KEY = "test123"
    const val CONNECT_TIMEOUT = 30L
    const val READ_TIMEOUT = 30L
    const val WRITE_TIMEOUT = 30L
    const val ENDPOINT_INGEST = "health-data/ingest"
    const val ENDPOINT_SYNC = "sync"
    const val ENDPOINT_STATUS = "health-data/status"
}

package com.capstone.healthmonitor.wear.data.network

import javax.inject.Inject
import javax.inject.Singleton
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.Interceptor
import okhttp3.Response

/**
 * Rewrites request URLs to the current base URL from settings without recreating Retrofit.
 */
@Singleton
class DynamicBaseUrlInterceptor @Inject constructor(
    private val endpointProvider: EndpointProvider
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()
        val base = endpointProvider.getBaseUrl()
        return try {
            val newBase = base.toHttpUrl()
            val newUrl = original.url.newBuilder()
                .scheme(newBase.scheme)
                .host(newBase.host)
                .port(newBase.port)
                .build()
            chain.proceed(original.newBuilder().url(newUrl).build())
        } catch (_: Exception) {
            // If the custom URL is invalid, fall back to the original
            chain.proceed(original)
        }
    }
}

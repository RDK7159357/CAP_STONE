/**
 * API Service Module
 */

import axios, { AxiosInstance, AxiosError, AxiosResponse } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { ApiConfig } from '@/config/api.config';
import { HealthMetric } from '@/types';

/**
 * Custom error class for API errors
 */
class ApiError extends Error {
  constructor(
    public statusCode: number | null,
    public message: string,
    public originalError?: Error
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * API Service class for handling all HTTP requests
 */
class ApiService {
  private client: AxiosInstance;
  private requestInterceptor: number | null = null;
  private responseInterceptor: number | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: ApiConfig.baseUrl,
      timeout: ApiConfig.connectTimeout,
      headers: ApiConfig.headers,
    });

    this.setupInterceptors();
  }

  /**
   * Setup request and response interceptors
   */
  private setupInterceptors(): void {
    // Request interceptor
    this.requestInterceptor = this.client.interceptors.request.use(
      async (config) => {
        // Add auth token if available
        const token = await AsyncStorage.getItem('authToken');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error('[API] Request error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.responseInterceptor = this.client.interceptors.response.use(
      (response) => {
        console.log(`[API] Response: ${response.status} ${response.statusText}`);
        return response;
      },
      (error: AxiosError) => {
        const statusCode = error.response?.status || null;
        const message = error.response?.statusText || error.message;
        
        console.error(`[API] Error ${statusCode}: ${message}`);

        // Handle specific error codes
        if (statusCode === 401) {
          // Unauthorized - clear auth token
          AsyncStorage.removeItem('authToken');
          // Could trigger logout here
        } else if (statusCode === 403) {
          // Forbidden
          console.warn('[API] Access forbidden');
        } else if (statusCode === 404) {
          // Not found
          console.warn('[API] Resource not found');
        } else if (statusCode === 500) {
          // Server error
          console.error('[API] Server error');
        }

        return Promise.reject(new ApiError(statusCode, message, error));
      }
    );
  }

  /**
   * GET request
   */
  async get<T = any>(url: string, config?: any): Promise<T> {
    try {
      const response: AxiosResponse<T> = await this.client.get(url, config);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * POST request
   */
  async post<T = any>(url: string, data?: any, config?: any): Promise<T> {
    try {
      const response: AxiosResponse<T> = await this.client.post(
        url,
        data,
        config
      );
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * PUT request
   */
  async put<T = any>(url: string, data?: any, config?: any): Promise<T> {
    try {
      const response: AxiosResponse<T> = await this.client.put(
        url,
        data,
        config
      );
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * DELETE request
   */
  async delete<T = any>(url: string, config?: any): Promise<T> {
    try {
      const response: AxiosResponse<T> = await this.client.delete(url, config);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * Health Data specific endpoints
   */

  async getHealthMetrics(): Promise<HealthMetric[]> {
    return this.get<HealthMetric[]>('/health/metrics');
  }

  async postHealthMetric(metric: Omit<HealthMetric, 'id'>): Promise<HealthMetric> {
    return this.post<HealthMetric>('/health/metrics', metric);
  }

  async getHealthHistory(
    startDate?: string,
    endDate?: string
  ): Promise<HealthMetric[]> {
    const params: any = {};
    if (startDate) params.startDate = startDate;
    if (endDate) params.endDate = endDate;
    return this.get<HealthMetric[]>('/health-data/history', { params });
  }

  async syncHealthData(): Promise<{ synced: number; timestamp: string }> {
    return this.post<{ synced: number; timestamp: string }>('/health-data/sync');
  }

  /**
   * Error handling
   */
  private handleError(error: any): ApiError {
    if (error instanceof ApiError) {
      return error;
    }

    if (axios.isAxiosError(error)) {
      const statusCode = error.response?.status || null;
      const message =
        error.response?.data?.message ||
        error.message ||
        'An error occurred';
      return new ApiError(statusCode, message, error);
    }

    return new ApiError(null, 'An unknown error occurred', error);
  }

  /**
   * Set authentication token
   */
  async setAuthToken(token: string): Promise<void> {
    await AsyncStorage.setItem('authToken', token);
    this.client.defaults.headers.common.Authorization = `Bearer ${token}`;
  }

  /**
   * Clear authentication token
   */
  async clearAuthToken(): Promise<void> {
    await AsyncStorage.removeItem('authToken');
    delete this.client.defaults.headers.common.Authorization;
  }

  /**
   * Get current auth token
   */
  async getAuthToken(): Promise<string | null> {
    return AsyncStorage.getItem('authToken');
  }

  /**
   * Health check - verify API connectivity
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.client.get('/health', {
        timeout: 5000,
      });
      return response.status === 200;
    } catch {
      return false;
    }
  }

  /**
   * Cleanup interceptors
   */
  destroy(): void {
    if (this.requestInterceptor !== null) {
      this.client.interceptors.request.eject(this.requestInterceptor);
    }
    if (this.responseInterceptor !== null) {
      this.client.interceptors.response.eject(this.responseInterceptor);
    }
  }
}

// Export singleton instance
export const apiService = new ApiService();

// Export class for testing
export { ApiService, ApiError };
export default apiService;

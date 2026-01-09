/**
 * Zustand Store for Health Data
 * Equivalent to Flutter Provider pattern
 */

import { create } from 'zustand';
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { HealthMetric, HealthDataState, HealthDataActions } from '@/types';
import { ApiConfig } from '@/config/api.config';

// Mock data generator for development
function getMockHealthMetrics(): HealthMetric[] {
  const now = new Date();
  const metrics: HealthMetric[] = [];
  
  for (let i = 0; i < 10; i++) {
    const timestamp = new Date(now.getTime() - i * 60 * 60 * 1000);
    const isAnomaly = Math.random() > 0.8;
    metrics.push({
      id: `mock-${i}`,
      heartRate: Math.floor(Math.random() * (100 - 60) + 60),
      steps: Math.floor(Math.random() * 5000),
      calories: Math.floor(Math.random() * (2000 - 1500) + 1500),
      distance: parseFloat((Math.random() * 5).toFixed(2)),
      timestamp: timestamp.toISOString(),
      isAnomaly,
      anomalyScore: isAnomaly ? parseFloat((Math.random() * 1).toFixed(2)) : 0,
    });
  }
  
  return metrics;
}

// Create axios instance
const apiClient = axios.create({
  baseURL: ApiConfig.baseUrl,
  timeout: ApiConfig.connectTimeout,
  headers: ApiConfig.headers,
});

// Combine state and actions
type HealthStore = HealthDataState & HealthDataActions;

export const useHealthStore = create<HealthStore>((set, get) => ({
  metrics: [],
  isLoading: false,
  error: null,
  recentAnomalies: [],
  todayMetrics: null,

  setMetrics: (metrics: HealthMetric[]) => {
    const sortedMetrics = metrics.sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
    
    // Get recent anomalies
    const recentAnomalies = sortedMetrics.filter(m => m.isAnomaly).slice(0, 5);
    
    // Get today's metrics
    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const todayEnd = new Date(todayStart.getTime() + 24 * 60 * 60 * 1000);
    
    const todayMetrics = sortedMetrics.find(
      m => new Date(m.timestamp) >= todayStart && new Date(m.timestamp) < todayEnd
    ) || null;
    
    set({
      metrics: sortedMetrics,
      recentAnomalies,
      todayMetrics,
    });
  },

  setLoading: (isLoading: boolean) => set({ isLoading }),

  setError: (error: string | null) => set({ error }),

  fetchHealthMetrics: async () => {
    set({ isLoading: true, error: null });
    try {
      // Try to fetch from API
      const response = await apiClient.get('/health/metrics');
      const metrics: HealthMetric[] = response.data;
      
      // Store in local storage for offline support
      await AsyncStorage.setItem('healthMetrics', JSON.stringify(metrics));
      
      get().setMetrics(metrics);
    } catch (error) {
      console.error('API fetch error:', error);
      
      // Fall back to cached data if available
      try {
        const cachedData = await AsyncStorage.getItem('healthMetrics');
        if (cachedData) {
          const metrics: HealthMetric[] = JSON.parse(cachedData);
          get().setMetrics(metrics);
          set({ error: null }); // Clear error if we have cached data
        } else {
          // Load mock data as final fallback
          const mockMetrics = getMockHealthMetrics();
          get().setMetrics(mockMetrics);
          set({ error: null });
        }
      } catch {
        // Load mock data if everything else fails
        const mockMetrics = getMockHealthMetrics();
        get().setMetrics(mockMetrics);
        set({ error: null });
      }
    } finally {
      set({ isLoading: false });
    }
  },

  uploadHealthMetric: async (metricData: Omit<HealthMetric, 'id'>) => {
    try {
      const metric: HealthMetric = {
        id: `${Date.now()}`,
        ...metricData,
      };
      
      await apiClient.post('/health/metrics', metric);
      
      // Refresh metrics after upload
      await get().fetchHealthMetrics();
      return true;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to upload metric';
      set({ error: errorMessage });
      return false;
    }
  },

  clearError: () => set({ error: null }),
}));

export default useHealthStore;

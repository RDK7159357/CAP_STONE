/**
 * Type definitions for Health Metrics
 */

export interface HealthMetric {
  id: string;
  timestamp: string; // ISO 8601 datetime
  heartRate: number;
  steps: number;
  calories: number;
  distance: number;
  isAnomaly: boolean;
  anomalyScore: number;
}

export interface HealthDataState {
  metrics: HealthMetric[];
  isLoading: boolean;
  error: string | null;
  recentAnomalies: HealthMetric[];
  todayMetrics: HealthMetric | null;
}

export interface HealthDataActions {
  setMetrics: (metrics: HealthMetric[]) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  fetchHealthMetrics: () => Promise<void>;
  uploadHealthMetric: (metric: Omit<HealthMetric, 'id'>) => Promise<boolean>;
  clearError: () => void;
}

export interface NotificationPayload {
  title: string;
  body: string;
  data?: Record<string, any>;
}

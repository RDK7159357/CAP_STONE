/**
 * Storage Service for local caching
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { HealthMetric } from '@/types';

class StorageService {
  private static readonly METRICS_KEY = 'healthMetrics';
  private static readonly USER_PREFS_KEY = 'userPreferences';
  private static readonly LAST_SYNC_KEY = 'lastSync';

  /**
   * Save metrics to local storage
   */
  async saveMetrics(metrics: HealthMetric[]): Promise<void> {
    try {
      await AsyncStorage.setItem(StorageService.METRICS_KEY, JSON.stringify(metrics));
      await this.setLastSync();
    } catch (error) {
      console.error('Failed to save metrics:', error);
      throw error;
    }
  }

  /**
   * Get metrics from local storage
   */
  async getMetrics(): Promise<HealthMetric[]> {
    try {
      const data = await AsyncStorage.getItem(StorageService.METRICS_KEY);
      return data ? JSON.parse(data) : [];
    } catch (error) {
      console.error('Failed to get metrics:', error);
      return [];
    }
  }

  /**
   * Clear all metrics
   */
  async clearMetrics(): Promise<void> {
    try {
      await AsyncStorage.removeItem(StorageService.METRICS_KEY);
    } catch (error) {
      console.error('Failed to clear metrics:', error);
      throw error;
    }
  }

  /**
   * Save user preferences
   */
  async saveUserPreferences(preferences: Record<string, any>): Promise<void> {
    try {
      await AsyncStorage.setItem(StorageService.USER_PREFS_KEY, JSON.stringify(preferences));
    } catch (error) {
      console.error('Failed to save preferences:', error);
      throw error;
    }
  }

  /**
   * Get user preferences
   */
  async getUserPreferences(): Promise<Record<string, any>> {
    try {
      const data = await AsyncStorage.getItem(StorageService.USER_PREFS_KEY);
      return data ? JSON.parse(data) : {};
    } catch (error) {
      console.error('Failed to get preferences:', error);
      return {};
    }
  }

  /**
   * Set last sync timestamp
   */
  private async setLastSync(): Promise<void> {
    try {
      await AsyncStorage.setItem(StorageService.LAST_SYNC_KEY, new Date().toISOString());
    } catch (error) {
      console.error('Failed to set last sync:', error);
    }
  }

  /**
   * Get last sync timestamp
   */
  async getLastSync(): Promise<string | null> {
    try {
      return await AsyncStorage.getItem(StorageService.LAST_SYNC_KEY);
    } catch (error) {
      console.error('Failed to get last sync:', error);
      return null;
    }
  }

  /**
   * Clear all storage
   */
  async clearAll(): Promise<void> {
    try {
      await AsyncStorage.multiRemove([
        StorageService.METRICS_KEY,
        StorageService.USER_PREFS_KEY,
        StorageService.LAST_SYNC_KEY,
      ]);
    } catch (error) {
      console.error('Failed to clear storage:', error);
      throw error;
    }
  }
}

export const storageService = new StorageService();
export default StorageService;

/**
 * Home Screen
 */

import React, { useEffect } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  RefreshControl,
  SafeAreaView,
  Text,
  TouchableOpacity,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useHealthStore } from '@/store/health.store';
import {
  MetricCard,
  AnomalyAlert,
  MetricCardSkeleton,
  ErrorFallback,
} from '@/components';
import { Colors, Spacing } from '@/config/theme.config';

export const HomeScreen = () => {
  const {
    metrics,
    isLoading,
    error,
    recentAnomalies,
    todayMetrics,
    fetchHealthMetrics,
    clearError,
  } = useHealthStore();

  // Fetch data on component mount
  useEffect(() => {
    fetchHealthMetrics();
  }, []);

  if (error && metrics.length === 0) {
    return (
      <ErrorFallback
        error={error}
        onRetry={() => {
          clearError();
          fetchHealthMetrics();
        }}
      />
    );
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Health Monitor</Text>
        <TouchableOpacity
          style={styles.refreshButton}
          onPress={() => fetchHealthMetrics()}
        >
          <MaterialCommunityIcons
            name="refresh"
            size={24}
            color={Colors.primary}
          />
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.scrollView}
        refreshControl={
          <RefreshControl
            refreshing={isLoading && metrics.length > 0}
            onRefresh={fetchHealthMetrics}
            tintColor={Colors.primary}
          />
        }
      >
        <View style={styles.content}>
          {/* Today's Summary */}
          {isLoading && metrics.length === 0 ? (
            <View>
              <MetricCardSkeleton />
              <MetricCardSkeleton />
              <MetricCardSkeleton />
              <MetricCardSkeleton />
            </View>
          ) : (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Today's Summary</Text>
              {todayMetrics ? (
                <>
                  <MetricCard
                    icon="heart"
                    label="Heart Rate"
                    value={`${todayMetrics.heartRate} bpm`}
                    color={Colors.heartRate}
                  />
                  <MetricCard
                    icon="walk"
                    label="Steps"
                    value={`${todayMetrics.steps}`}
                    color={Colors.steps}
                  />
                  <MetricCard
                    icon="fire"
                    label="Calories"
                    value={`${todayMetrics.calories.toFixed(1)} kcal`}
                    color={Colors.calories}
                  />
                  <MetricCard
                    icon="ruler"
                    label="Distance"
                    value={`${todayMetrics.distance.toFixed(2)} km`}
                    color={Colors.distance}
                  />
                </>
              ) : (
                <View style={styles.noDataContainer}>
                  <Text style={styles.noDataText}>No data available for today</Text>
                </View>
              )}
            </View>
          )}

          {/* Anomalies Section */}
          {recentAnomalies.length > 0 && (
            <AnomalyAlert anomalies={recentAnomalies} />
          )}

          {/* Error Banner */}
          {error && metrics.length > 0 && (
            <View style={styles.errorBanner}>
              <MaterialCommunityIcons
                name="information"
                size={20}
                color={Colors.warning}
              />
              <Text style={styles.errorBannerText}>{error}</Text>
            </View>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.white,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.gray200,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: Colors.gray900,
  },
  refreshButton: {
    padding: Spacing.md,
  },
  scrollView: {
    flex: 1,
  },
  content: {
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.lg,
  },
  card: {
    backgroundColor: Colors.white,
    borderRadius: 12,
    marginBottom: Spacing.lg,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: Colors.gray200,
  },
  cardTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: Colors.gray900,
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.lg,
    marginBottom: Spacing.md,
  },
  noDataContainer: {
    alignItems: 'center',
    paddingVertical: Spacing.lg,
  },
  noDataText: {
    color: Colors.gray600,
    fontSize: 16,
  },
  errorBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: `${Colors.warning}20`,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderRadius: 8,
    marginBottom: Spacing.lg,
  },
  errorBannerText: {
    marginLeft: Spacing.md,
    flex: 1,
    color: Colors.warning,
    fontSize: 14,
  },
});

export default HomeScreen;

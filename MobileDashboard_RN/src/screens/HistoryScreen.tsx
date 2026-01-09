/**
 * History Screen
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  SafeAreaView,
  Text,
  FlatList,
  SectionList,
} from 'react-native';
import { Colors, Spacing, BorderRadius } from '@/config/theme.config';
import { useHealthStore } from '@/store/health.store';
import { HealthMetric } from '@/types';
import dayjs from 'dayjs';
import { MetricCardSkeleton } from '@/components';

export const HistoryScreen = () => {
  const { metrics, isLoading } = useHealthStore();
  const [groupedMetrics, setGroupedMetrics] = useState<
    Array<{ title: string; data: HealthMetric[] }>
  >([]);

  useEffect(() => {
    groupMetricsByDate();
  }, [metrics]);

  const groupMetricsByDate = () => {
    const grouped = metrics.reduce(
      (acc, metric) => {
        const dateKey = dayjs(metric.timestamp).format('YYYY-MM-DD');
        const dateLabel = dayjs(metric.timestamp).format('dddd, MMMM D, YYYY');

        const existingGroup = acc.find((g) => g.title === dateLabel);
        if (existingGroup) {
          existingGroup.data.push(metric);
        } else {
          acc.push({ title: dateLabel, data: [metric] });
        }
        return acc;
      },
      [] as Array<{ title: string; data: HealthMetric[] }>
    );

    setGroupedMetrics(grouped);
  };

  const renderMetricItem = ({ item }: { item: HealthMetric }) => (
    <View style={styles.metricItem}>
      <View style={styles.metricTime}>
        <Text style={styles.timeText}>
          {dayjs(item.timestamp).format('HH:mm')}
        </Text>
      </View>
      <View style={styles.metricDetails}>
        <View style={styles.metricRow}>
          <Text style={styles.metricLabel}>HR:</Text>
          <Text style={[styles.metricValue, { color: Colors.heartRate }]}>
            {item.heartRate} bpm
          </Text>
        </View>
        <View style={styles.metricRow}>
          <Text style={styles.metricLabel}>Steps:</Text>
          <Text style={[styles.metricValue, { color: Colors.steps }]}>
            {item.steps}
          </Text>
        </View>
        <View style={styles.metricRow}>
          <Text style={styles.metricLabel}>Calories:</Text>
          <Text style={[styles.metricValue, { color: Colors.calories }]}>
            {item.calories.toFixed(1)} kcal
          </Text>
        </View>
        <View style={styles.metricRow}>
          <Text style={styles.metricLabel}>Distance:</Text>
          <Text style={[styles.metricValue, { color: Colors.distance }]}>
            {item.distance.toFixed(2)} km
          </Text>
        </View>
      </View>
      {item.isAnomaly && (
        <View
          style={[
            styles.anomalyBadge,
            { backgroundColor: `${Colors.anomaly}20` },
          ]}
        >
          <Text style={{ color: Colors.anomaly, fontSize: 12, fontWeight: '600' }}>
            Anomaly
          </Text>
        </View>
      )}
    </View>
  );

  const renderSectionHeader = ({ section: { title } }: { section: { title: string } }) => (
    <View style={styles.sectionHeader}>
      <Text style={styles.sectionTitle}>{title}</Text>
    </View>
  );

  if (isLoading && metrics.length === 0) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>History</Text>
        </View>
        <ScrollView style={styles.scrollView}>
          {[...Array(5)].map((_, i) => (
            <View key={i}>
              <MetricCardSkeleton />
              <MetricCardSkeleton />
              <MetricCardSkeleton />
            </View>
          ))}
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>History</Text>
      </View>

      {groupedMetrics.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>No data available</Text>
        </View>
      ) : (
        <SectionList
          sections={groupedMetrics}
          keyExtractor={(item) => item.id}
          renderItem={renderMetricItem}
          renderSectionHeader={renderSectionHeader}
          contentContainerStyle={styles.listContent}
          scrollEnabled={true}
        />
      )}
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.white,
  },
  header: {
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
  scrollView: {
    flex: 1,
  },
  listContent: {
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
  },
  sectionHeader: {
    paddingVertical: Spacing.md,
    marginTop: Spacing.lg,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.gray600,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  metricItem: {
    backgroundColor: Colors.gray100,
    borderRadius: BorderRadius.lg,
    padding: Spacing.lg,
    marginBottom: Spacing.md,
    borderLeftWidth: 4,
    borderLeftColor: Colors.primary,
  },
  metricTime: {
    marginBottom: Spacing.md,
  },
  timeText: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.gray900,
  },
  metricDetails: {
    marginBottom: Spacing.md,
  },
  metricRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: Spacing.sm,
  },
  metricLabel: {
    fontSize: 12,
    color: Colors.gray600,
    fontWeight: '500',
  },
  metricValue: {
    fontSize: 12,
    fontWeight: '600',
  },
  anomalyBadge: {
    alignSelf: 'flex-start',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.lg,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 16,
    color: Colors.gray600,
  },
});

export default HistoryScreen;

/**
 * Anomaly Alert Card Component
 * Displays recent anomalies with human-readable explanations of why each was flagged.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, BorderRadius } from '@/config/theme.config';
import { HealthMetric } from '@/types';

interface AnomalyAlertProps {
  anomalies: HealthMetric[];
}

export const AnomalyAlert: React.FC<AnomalyAlertProps> = ({ anomalies }) => {
  if (anomalies.length === 0) {
    return null;
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <MaterialCommunityIcons
          name="alert-circle"
          size={24}
          color={Colors.anomaly}
        />
        <Text style={styles.title}>Recent Anomalies</Text>
      </View>

      {anomalies.map((anomaly) => (
        <View key={anomaly.id} style={styles.anomalyItem}>
          <MaterialCommunityIcons
            name="alert"
            size={20}
            color={Colors.anomaly}
          />
          <View style={styles.anomalyContent}>
            <View style={styles.anomalyHeader}>
              <Text style={styles.anomalyScore}>
                Score: {anomaly.anomalyScore.toFixed(2)}
              </Text>
              {anomaly.anomalySource && (
                <View style={styles.sourceBadge}>
                  <Text style={styles.sourceText}>
                    {anomaly.anomalySource}
                  </Text>
                </View>
              )}
            </View>
            <Text style={styles.anomalyTime}>
              {new Date(anomaly.timestamp).toLocaleTimeString()}
            </Text>

            {/* Anomaly Explanation */}
            {anomaly.anomalyReasons && anomaly.anomalyReasons.length > 0 && (
              <View style={styles.reasonsContainer}>
                {anomaly.anomalyReasons.map((reason, index) => (
                  <View key={index} style={styles.reasonRow}>
                    <MaterialCommunityIcons
                      name="information-outline"
                      size={14}
                      color={Colors.gray600}
                    />
                    <Text style={styles.reasonText}>{reason}</Text>
                  </View>
                ))}
              </View>
            )}
          </View>
        </View>
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: `${Colors.anomaly}10`,
    borderRadius: BorderRadius.lg,
    padding: Spacing.lg,
    marginBottom: Spacing.lg,
    borderLeftWidth: 4,
    borderLeftColor: Colors.anomaly,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: Spacing.md,
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    marginLeft: Spacing.md,
    color: Colors.gray900,
  },
  anomalyItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingVertical: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: `${Colors.anomaly}20`,
  },
  anomalyContent: {
    marginLeft: Spacing.md,
    flex: 1,
  },
  anomalyHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  anomalyScore: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.gray900,
  },
  sourceBadge: {
    backgroundColor: `${Colors.anomaly}20`,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 2,
    borderRadius: BorderRadius.sm,
  },
  sourceText: {
    fontSize: 11,
    fontWeight: '600',
    color: Colors.anomaly,
    textTransform: 'uppercase',
  },
  anomalyTime: {
    fontSize: 12,
    color: Colors.gray600,
    marginTop: Spacing.xs,
  },
  reasonsContainer: {
    marginTop: Spacing.sm,
    backgroundColor: `${Colors.anomaly}08`,
    borderRadius: BorderRadius.sm,
    padding: Spacing.sm,
  },
  reasonRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 4,
  },
  reasonText: {
    fontSize: 13,
    color: Colors.gray700,
    marginLeft: Spacing.xs,
    flex: 1,
    lineHeight: 18,
  },
});

export default AnomalyAlert;

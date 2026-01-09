/**
 * Anomaly Alert Card Component
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
            <Text style={styles.anomalyScore}>
              Score: {anomaly.anomalyScore.toFixed(2)}
            </Text>
            <Text style={styles.anomalyTime}>
              {new Date(anomaly.timestamp).toLocaleTimeString()}
            </Text>
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
    alignItems: 'center',
    paddingVertical: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: `${Colors.anomaly}20`,
  },
  anomalyContent: {
    marginLeft: Spacing.md,
    flex: 1,
  },
  anomalyScore: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.gray900,
  },
  anomalyTime: {
    fontSize: 12,
    color: Colors.gray600,
    marginTop: Spacing.xs,
  },
});

export default AnomalyAlert;

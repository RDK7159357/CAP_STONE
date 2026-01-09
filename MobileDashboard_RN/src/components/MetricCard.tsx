/**
 * Metric Card Component
 */

import React from 'react';
import { View, Text, StyleSheet, ViewStyle, TextStyle } from 'react-native';
import { Colors, Spacing, BorderRadius, Typography } from '@/config/theme.config';
import { MaterialCommunityIcons } from '@expo/vector-icons';

interface MetricCardProps {
  icon: string;
  label: string;
  value: string;
  color: string;
  style?: ViewStyle;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  icon,
  label,
  value,
  color,
  style,
}) => {
  return (
    <View style={[styles.container, style]}>
      <View style={[styles.iconContainer, { backgroundColor: `${color}20` }]}>
        <MaterialCommunityIcons name={icon as any} size={32} color={color} />
      </View>
      <View style={styles.content}>
        <Text style={styles.label}>{label}</Text>
        <Text style={[styles.value, { color }]}>{value}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: Colors.gray200,
  },
  iconContainer: {
    width: 56,
    height: 56,
    borderRadius: BorderRadius.lg,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: Spacing.md,
  },
  content: {
    flex: 1,
  },
  label: {
    fontSize: 14,
    color: Colors.gray600,
    marginBottom: Spacing.xs,
  },
  value: {
    fontSize: 18,
    fontWeight: '600',
  } as TextStyle,
});

export default MetricCard;

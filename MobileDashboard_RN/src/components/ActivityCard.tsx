/**
 * Activity Classification Card Component
 * Displays the user's current detected activity state with icon and label.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, BorderRadius } from '@/config/theme.config';

type ActivityState = 'sleep' | 'rest' | 'walk' | 'run' | 'exercise' | 'other';

interface ActivityCardProps {
    activityState: ActivityState | string | null | undefined;
    timestamp?: string;
}

const ACTIVITY_CONFIG: Record<
    ActivityState,
    { icon: string; label: string; color: string }
> = {
    sleep: { icon: 'sleep', label: 'Sleeping', color: '#6C5CE7' },
    rest: { icon: 'sofa', label: 'Resting', color: '#0984E3' },
    walk: { icon: 'walk', label: 'Walking', color: '#00B894' },
    run: { icon: 'run', label: 'Running', color: '#E17055' },
    exercise: { icon: 'dumbbell', label: 'Exercising', color: '#D63031' },
    other: { icon: 'dots-horizontal', label: 'Other', color: '#636E72' },
};

export const ActivityCard: React.FC<ActivityCardProps> = ({
    activityState,
    timestamp,
}) => {
    const state = (activityState || 'other') as ActivityState;
    const config = ACTIVITY_CONFIG[state] || ACTIVITY_CONFIG.other;

    return (
        <View style={[styles.container, { borderLeftColor: config.color }]}>
            <View style={styles.header}>
                <MaterialCommunityIcons
                    name="run-fast"
                    size={20}
                    color={Colors.activity}
                />
                <Text style={styles.title}>Activity</Text>
            </View>

            <View style={styles.content}>
                <View
                    style={[styles.iconCircle, { backgroundColor: `${config.color}15` }]}
                >
                    <MaterialCommunityIcons
                        name={config.icon as any}
                        size={28}
                        color={config.color}
                    />
                </View>
                <View style={styles.textContainer}>
                    <Text style={[styles.activityLabel, { color: config.color }]}>
                        {config.label}
                    </Text>
                    {timestamp && (
                        <Text style={styles.timestamp}>
                            {new Date(timestamp).toLocaleTimeString([], {
                                hour: '2-digit',
                                minute: '2-digit',
                            })}
                        </Text>
                    )}
                </View>
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        backgroundColor: Colors.white,
        borderRadius: BorderRadius.lg,
        padding: Spacing.lg,
        marginBottom: Spacing.lg,
        borderWidth: 1,
        borderColor: Colors.gray200,
        borderLeftWidth: 4,
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: Spacing.md,
    },
    title: {
        fontSize: 16,
        fontWeight: '600',
        marginLeft: Spacing.sm,
        color: Colors.gray900,
    },
    content: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    iconCircle: {
        width: 48,
        height: 48,
        borderRadius: 24,
        justifyContent: 'center',
        alignItems: 'center',
    },
    textContainer: {
        marginLeft: Spacing.md,
        flex: 1,
    },
    activityLabel: {
        fontSize: 20,
        fontWeight: '700',
    },
    timestamp: {
        fontSize: 12,
        color: Colors.gray600,
        marginTop: 2,
    },
});

export default ActivityCard;

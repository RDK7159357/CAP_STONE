/**
 * Settings Screen
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  SafeAreaView,
  Text,
  TouchableOpacity,
  Switch,
  Alert,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, BorderRadius } from '@/config/theme.config';
import { storageService } from '@/services/storage.service';
import { useHealthStore } from '@/store/health.store';

interface Settings {
  notificationsEnabled: boolean;
  darkMode: boolean;
  syncOnWifi: boolean;
  cacheSize: string;
}

export const SettingsScreen = () => {
  const [settings, setSettings] = useState<Settings>({
    notificationsEnabled: true,
    darkMode: false,
    syncOnWifi: true,
    cacheSize: '0 MB',
  });

  const { metrics } = useHealthStore();

  useEffect(() => {
    loadSettings();
    calculateCacheSize();
  }, []);

  const loadSettings = async () => {
    try {
      const prefs = await storageService.getUserPreferences();
      setSettings((prev) => ({
        ...prev,
        notificationsEnabled: prefs.notificationsEnabled ?? true,
        darkMode: prefs.darkMode ?? false,
        syncOnWifi: prefs.syncOnWifi ?? true,
      }));
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  };

  const calculateCacheSize = () => {
    try {
      const size = JSON.stringify(metrics).length / 1024 / 1024;
      setSettings((prev) => ({
        ...prev,
        cacheSize: `${size.toFixed(2)} MB`,
      }));
    } catch (error) {
      console.error('Failed to calculate cache size:', error);
    }
  };

  const handleSettingChange = async (
    key: keyof Settings,
    value: any
  ) => {
    setSettings((prev) => ({
      ...prev,
      [key]: value,
    }));

    try {
      const updatedPrefs = {
        notificationsEnabled: settings.notificationsEnabled,
        darkMode: settings.darkMode,
        syncOnWifi: settings.syncOnWifi,
      };

      if (key !== 'cacheSize') {
        updatedPrefs[key as keyof typeof updatedPrefs] = value;
        await storageService.saveUserPreferences(updatedPrefs);
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
    }
  };

  const handleClearCache = () => {
    Alert.alert(
      'Clear Cache',
      'Are you sure you want to clear all cached data?',
      [
        { text: 'Cancel', onPress: () => {} },
        {
          text: 'Clear',
          onPress: async () => {
            try {
              await storageService.clearMetrics();
              setSettings((prev) => ({
                ...prev,
                cacheSize: '0 MB',
              }));
              Alert.alert('Success', 'Cache cleared successfully');
            } catch (error) {
              Alert.alert('Error', 'Failed to clear cache');
            }
          },
          style: 'destructive',
        },
      ]
    );
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Settings</Text>
      </View>

      <ScrollView style={styles.scrollView}>
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Notifications</Text>
          <View style={styles.settingItem}>
            <View style={styles.settingLabel}>
              <MaterialCommunityIcons
                name="bell"
                size={24}
                color={Colors.primary}
              />
              <Text style={styles.settingText}>Enable Notifications</Text>
            </View>
            <Switch
              value={settings.notificationsEnabled}
              onValueChange={(value) =>
                handleSettingChange('notificationsEnabled', value)
              }
              trackColor={{ false: Colors.gray300, true: Colors.primary }}
              thumbColor={Colors.white}
            />
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Display</Text>
          <View style={styles.settingItem}>
            <View style={styles.settingLabel}>
              <MaterialCommunityIcons
                name="moon-waning-crescent"
                size={24}
                color={Colors.primary}
              />
              <Text style={styles.settingText}>Dark Mode</Text>
            </View>
            <Switch
              value={settings.darkMode}
              onValueChange={(value) => handleSettingChange('darkMode', value)}
              trackColor={{ false: Colors.gray300, true: Colors.primary }}
              thumbColor={Colors.white}
            />
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Sync</Text>
          <View style={styles.settingItem}>
            <View style={styles.settingLabel}>
              <MaterialCommunityIcons
                name="wifi"
                size={24}
                color={Colors.primary}
              />
              <Text style={styles.settingText}>Sync Only on WiFi</Text>
            </View>
            <Switch
              value={settings.syncOnWifi}
              onValueChange={(value) => handleSettingChange('syncOnWifi', value)}
              trackColor={{ false: Colors.gray300, true: Colors.primary }}
              thumbColor={Colors.white}
            />
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Storage</Text>
          <View style={styles.settingItem}>
            <View style={styles.settingLabel}>
              <MaterialCommunityIcons
                name="database"
                size={24}
                color={Colors.primary}
              />
              <View>
                <Text style={styles.settingText}>Cache Size</Text>
                <Text style={styles.settingSubtext}>{settings.cacheSize}</Text>
              </View>
            </View>
          </View>
          <TouchableOpacity
            style={styles.dangerButton}
            onPress={handleClearCache}
          >
            <MaterialCommunityIcons
              name="delete"
              size={20}
              color={Colors.error}
            />
            <Text style={styles.dangerButtonText}>Clear Cache</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>About</Text>
          <View style={styles.infoItem}>
            <Text style={styles.infoLabel}>Version</Text>
            <Text style={styles.infoValue}>1.0.0</Text>
          </View>
          <View style={styles.infoItem}>
            <Text style={styles.infoLabel}>Build</Text>
            <Text style={styles.infoValue}>1</Text>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.gray100,
  },
  header: {
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    backgroundColor: Colors.white,
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
  section: {
    backgroundColor: Colors.white,
    marginBottom: Spacing.lg,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.gray600,
    marginBottom: Spacing.md,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  settingItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.gray200,
  },
  settingLabel: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  settingText: {
    fontSize: 16,
    color: Colors.gray900,
    marginLeft: Spacing.md,
    fontWeight: '500',
  },
  settingSubtext: {
    fontSize: 12,
    color: Colors.gray600,
    marginTop: Spacing.xs,
  },
  dangerButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.lg,
    backgroundColor: `${Colors.error}10`,
    borderRadius: BorderRadius.md,
    marginTop: Spacing.md,
  },
  dangerButtonText: {
    marginLeft: Spacing.md,
    fontSize: 16,
    color: Colors.error,
    fontWeight: '600',
  },
  infoItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.gray200,
  },
  infoLabel: {
    fontSize: 14,
    color: Colors.gray600,
  },
  infoValue: {
    fontSize: 14,
    color: Colors.gray900,
    fontWeight: '600',
  },
});

export default SettingsScreen;

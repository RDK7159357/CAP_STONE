/**
 * Main App Component
 */

import React, { useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import * as SplashScreen from 'expo-splash-screen';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { RootNavigator } from '@/navigation';
import { notificationService } from '@/services/notification.service';

// Keep the splash screen visible while we fetch resources
SplashScreen.preventAutoHideAsync();

export default function App() {
  const initializeApp = async () => {
    try {
      // Initialize notifications
      await notificationService.initialize();
      // Hide splash screen once initialized
      await SplashScreen.hideAsync();
      console.log('App initialized successfully');
    } catch (error) {
      console.error('Failed to initialize app:', error);
      await SplashScreen.hideAsync();
    }
  };

  useEffect(() => {
    // Initialize app services
    initializeApp();
  }, []);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <RootNavigator />
      <StatusBar style="light" />
    </GestureHandlerRootView>
  );
}

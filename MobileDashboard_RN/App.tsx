/**
 * Main App Component
 */

import React, { useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import * as SplashScreen from 'expo-splash-screen';
import { useFonts } from 'expo-font';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { RootNavigator } from '@/navigation';
import { notificationService } from '@/services/notification.service';

// Keep the splash screen visible while we fetch resources
SplashScreen.preventAutoHideAsync();

export default function App() {
  const [fontsLoaded, fontError] = useFonts({
    // Add custom fonts here if needed
    // 'Roboto-Regular': require('@/assets/fonts/Roboto-Regular.ttf'),
    // 'Roboto-Bold': require('@/assets/fonts/Roboto-Bold.ttf'),
  });

  const initializeApp = async () => {
    try {
      // Initialize notifications
      await notificationService.initialize();
      console.log('App initialized successfully');
    } catch (error) {
      console.error('Failed to initialize app:', error);
    }
  };

  useEffect(() => {
    // Initialize app services
    initializeApp();
  }, []);

  useEffect(() => {
    // Hide splash screen when fonts are loaded
    if (fontsLoaded || fontError) {
      SplashScreen.hideAsync();
    }
  }, [fontsLoaded, fontError]);

  // Don't render until fonts are loaded
  if (!fontsLoaded && !fontError) {
    return null;
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <RootNavigator />
      <StatusBar style="light" />
    </GestureHandlerRootView>
  );
}

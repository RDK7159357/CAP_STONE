import React, { useEffect } from 'react';
import * as Notifications from 'expo-notifications';
import Constants from 'expo-constants';
import { RootNavigator } from './src/navigation';

// ─── Notification Handler ────────────────────────────────────────────────────
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

const API_BASE_URL = 'https://t6rlkix2lg.execute-api.ap-south-2.amazonaws.com/prod';
const API_KEY = 'test123';

async function registerForPushNotifications(userId: string = "user_001") {
  try {
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    if (finalStatus !== 'granted') {
      console.warn('Notification permission denied');
      return null;
    }

    const tokenData = await Notifications.getExpoPushTokenAsync({
      projectId: Constants.expoConfig?.extra?.eas?.projectId,
    });
    const token = tokenData.data;
    console.log('Expo Push Token:', token);

    const response = await fetch(`${API_BASE_URL}/notifications/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
      },
      body: JSON.stringify({
        userId: userId,
        deviceId: "my_phone_01",
        pushToken: token,
        platform: "expo",
      }),
    });

    const responseText = await response.text();
    console.log('Register response status:', response.status);
    console.log('Register response body:', responseText);

    if (!response.ok) {
      console.error(`Backend registration failed [${response.status}]:`, responseText);
      return token;
    }

    console.log('Push token registered successfully!');
    return token;

  } catch (error: any) {
    console.error('Push notification registration error:', error?.message || error);
    return null;
  }
}

// ─── Root Component ──────────────────────────────────────────────────────────
export default function App() {
  useEffect(() => {
    registerForPushNotifications();
  }, []);

  return <RootNavigator />;
}

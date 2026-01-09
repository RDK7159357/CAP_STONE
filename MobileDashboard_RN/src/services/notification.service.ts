/**
 * Notification Service using Expo Notifications
 */

import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import * as Device from 'expo-device';
import Constants from 'expo-constants';

// Configure notification behavior
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

class NotificationService {
  private expoPushToken: string | null = null;
  private foregroundSubscription: any = null;
  private responseSubscription: any = null;
  private tokenSubscription: any = null;

  async initialize(): Promise<void> {
    try {
      // Register for push notifications
      await this.registerForPushNotifications();

      // Listen for incoming notifications
      this.setupNotificationListeners();
    } catch (error) {
      console.error('Failed to initialize notifications:', error);
    }
  }

  private async registerForPushNotifications(): Promise<void> {
    // Check if device is physical and running on iOS
    if (Platform.OS === 'web') {
      console.log('Push notifications not supported on web');
      return;
    }

    if (!Device.isDevice) {
      console.warn('Must use physical device for push notifications');
      return;
    }

    // Get existing permissions
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    // Request permission if not already granted
    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    if (finalStatus !== 'granted') {
      console.warn('Failed to get push notification permissions');
      return;
    }

    // Get Expo push token
    const projectId = Constants.expoConfig?.extra?.eas?.projectId || Constants.easProjectId;
    
    if (!projectId) {
      console.warn('Project ID not configured for Expo notifications');
      return;
    }

    const token = await Notifications.getExpoPushTokenAsync({ projectId });
    this.expoPushToken = token.data;
    console.log('Expo push token:', this.expoPushToken);

    // TODO: Send token to backend server

    // Listen for token refresh
    this.tokenSubscription = Notifications.addPushTokenListener((token) => {
      this.expoPushToken = token.data;
      console.log('Push token refreshed:', token.data);
      // TODO: Send updated token to backend
    });
  }

  private setupNotificationListeners(): void {
    // Listen for notifications when app is in foreground
    this.foregroundSubscription = Notifications.addNotificationReceivedListener((notification) => {
      console.log('Notification received in foreground:', notification);
    });

    // Listen for notification taps/interactions
    this.responseSubscription = Notifications.addNotificationResponseReceivedListener((response) => {
      console.log('Notification response:', response);
      // TODO: Handle notification tap, navigate to appropriate screen
    });
  }

  private cleanup(): void {
    if (this.foregroundSubscription) {
      Notifications.removeNotificationSubscription(this.foregroundSubscription);
    }
    if (this.responseSubscription) {
      Notifications.removeNotificationSubscription(this.responseSubscription);
    }
    if (this.tokenSubscription) {
      this.tokenSubscription.remove();
    }
  }

  async showLocalNotification(title: string, body: string, data?: Record<string, any>): Promise<void> {
    try {
      await Notifications.scheduleNotificationAsync({
        content: {
          title,
          body,
          sound: 'default',
          data: data || {},
        },
        trigger: null, // Immediate
      });
    } catch (error) {
      console.error('Failed to show notification:', error);
    }
  }

  getExpoPushToken(): string | null {
    return this.expoPushToken;
  }

  destroy(): void {
    this.cleanup();
  }
}

export const notificationService = new NotificationService();
export default NotificationService;

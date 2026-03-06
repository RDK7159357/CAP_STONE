# Health Monitor Dashboard - React Native + Expo Migration

This is a complete migration of the Flutter Mobile Dashboard to **React Native with Expo**, maintained with TypeScript for type safety.

## 🎯 Project Overview

Cross-platform mobile dashboard for visualizing health monitoring data and receiving real-time anomaly alerts, built with React Native and Expo.

### ✨ Features Migrated

- 📊 **Real-time Health Metrics Visualization** - Heart rate, steps, calories, distance
- 📈 **Historical Trend Tracking** - View metrics organized by date with anomaly badges
- 🔔 **Push Notifications** - Anomaly alerts via Expo Notifications with contextual reasons
- 💡 **Anomaly Explainability** - Alert cards show *why* each anomaly occurred (source + reasons)
- 🌙 **Dark Mode Support** - Automatic theme switching
- 📱 **Material Design UI** - Consistent, modern interface
- 💾 **Offline Support** - Local caching with AsyncStorage
- 🔄 **Sync Management** - WiFi-only sync option

## 📋 Architecture

### State Management
- **Zustand** - Lightweight state management (replaced Flutter Provider)
- Global health data store with actions for fetch, upload, and error handling

### Storage
- **AsyncStorage** - Local data persistence for offline access
- User preferences and metrics caching

### Notifications
- **Expo Notifications** - Cross-platform push notifications
- Foreground and background message handling

### Navigation
- **React Navigation** - Bottom tab navigation (Home, History, Settings)
- Gesture-based navigation with gesture handlers

### UI Components
- **React Native Core** - Safe areas, scrolling, animations
- **Expo Vector Icons** - Material Community Icons
- **Custom Components** - Metric cards, anomaly alerts, loading skeletons

## 🚀 Getting Started

### Prerequisites

- Node.js 16+ and npm/yarn
- Expo CLI (`npm install -g expo-cli`)
- iOS Simulator or Android Emulator (or physical device)

### Installation

```bash
# Navigate to project directory
cd MobileDashboard_RN

# Install dependencies
npm install
# or
yarn install

# Start the Expo development server
npm start
# or
yarn start
```

### Running on Devices

**iOS Simulator:**
```bash
npm run ios
```

**Android Emulator:**
```bash
npm run android
```

**Web (development):**
```bash
npm run web
```

**Physical Device:**
1. Download Expo Go app (iOS App Store or Google Play)
2. Scan QR code from terminal
3. App opens in Expo Go

## 📁 Project Structure

```
src/
├── config/              # Configuration files
│   ├── api.config.ts    # API endpoints and headers
│   └── theme.config.ts  # Colors, spacing, typography
├── store/               # State management
│   └── health.store.ts  # Zustand health data store
├── services/            # Business logic services
│   ├── notification.service.ts
│   └── storage.service.ts
├── components/          # Reusable UI components
│   ├── MetricCard.tsx
│   ├── AnomalyAlert.tsx
│   ├── Skeleton.tsx
│   ├── ErrorFallback.tsx
│   └── index.ts
├── screens/             # Screen components
│   ├── HomeScreen.tsx
│   ├── HistoryScreen.tsx
│   ├── SettingsScreen.tsx
│   └── index.ts
├── navigation/          # Navigation configuration
│   ├── RootNavigator.tsx
│   ├── BottomTabNavigator.tsx
│   └── index.ts
├── types/               # TypeScript type definitions
│   └── index.ts
├── utils/               # Utility functions
│   ├── dateUtils.ts
│   ├── numberUtils.ts
│   └── index.ts
├── App.tsx              # Main app component
└── index.ts             # Entry point

assets/                  # Images, icons, animations
package.json             # Dependencies and scripts
app.json                 # Expo configuration
tsconfig.json            # TypeScript configuration
```

## 🔧 Configuration

### API Configuration

Edit `src/config/api.config.ts`:

```typescript
export const ApiConfig = {
  baseUrl: 'https://u8tkgz3vsf.execute-api.ap-south-2.amazonaws.com/prod/',
  apiKey: 'your-api-key-here',
  userId: 'demo-user-dhanush',
  // ... other config
};
```

### Theme Configuration

Customize colors, spacing, and typography in `src/config/theme.config.ts`.

## 📡 API Integration

The app uses **Axios** for HTTP requests with automatic retry and timeout handling. Base configuration is in `src/config/api.config.ts`.

### Health Data Endpoints

- `GET /health/metrics` - Fetch user's latest health metrics (with anomalyReasons & anomalySource)
- `POST /health-data/ingest` - Ingest new health metric
- `POST /health-data/sync` - Batch sync from Wear OS
- `GET /health-data/history` - Get historical data (with anomalyReasons & anomalySource)

## 🔔 Push Notifications

The app integrates with **Expo Notifications** for push alerts:

1. **Registration** - Automatically requests permissions on startup
2. **Token Management** - Gets and refreshes Expo push token
3. **Message Handling** - Foreground, background, and tap handlers
4. **Local Notifications** - Shows immediate alerts when triggered

### Sending Notifications

The backend should send notifications using the Expo push service:

```bash
curl -X POST https://exp.host/--/api/v2/push/send \
  -H 'Accept: application/json' \
  -H 'Accept-Encoding: gzip, deflate' \
  -H 'Content-Type: application/json' \
  -d '{
    "to": "[EXPO_PUSH_TOKEN]",
    "sound": "default",
    "title": "Health Alert",
    "body": "Heart rate 180 BPM is dangerously high (threshold: 140 BPM)"
  }'
```

> The backend uses the first anomaly reason as the push notification body, so users see *why* the alert was triggered.

## 💾 Data Persistence

- **Local Storage** - Metrics cached in AsyncStorage for offline access
- **Auto-sync** - Data syncs automatically when online
- **Fallback** - Shows cached data if network unavailable

## 🎨 Theming

The app supports light and dark modes with automatic detection based on system settings.

### Custom Theme

Modify colors in `src/config/theme.config.ts`:

```typescript
export const Colors = {
  primary: '#007AFF',
  heartRate: '#E74C3C',
  // ... more colors
};
```

## 🧪 Testing

Run tests with:

```bash
npm test
```

Build for production:

```bash
npm run build
```

## 📝 Key Differences from Flutter Version

| Feature | Flutter | React Native |
|---------|---------|--------------|
| State Management | Provider | Zustand |
| Navigation | Native Navigator | React Navigation |
| Storage | Hive + SharedPreferences | AsyncStorage |
| Notifications | Firebase Messaging | Expo Notifications |
| Styling | Material Design | Custom Theme Config |
| Charts | FL Charts, Syncfusion | React Native SVG Charts |

## 🐛 Debugging

**Enable verbose logging:**
```typescript
// In App.tsx
import { LogBox } from 'react-native';
LogBox.ignoreAllLogs(); // Production only
```

**Network debugging:**
- Enable Reactotron for network inspection
- Use Expo DevTools

## 📚 Dependencies

### Core
- `react-native` - Mobile UI framework
- `expo` - Development platform
- `react-navigation` - Navigation library

### State & Storage
- `zustand` - State management
- `@react-native-async-storage/async-storage` - Persistent storage

### Networking
- `axios` - HTTP client

### UI
- `react-native-gesture-handler` - Gesture support
- `@react-native-community/netinfo` - Network detection
- `lottie-react-native` - Animations

### Utilities
- `dayjs` - Date manipulation
- `TypeScript` - Type safety

## 🚀 Deployment

### iOS (TestFlight)
```bash
eas build --platform ios
eas submit --platform ios
```

### Android (Play Store)
```bash
eas build --platform android
eas submit --platform android
```

### Web
```bash
npm run web
```

## 📖 Documentation

- [React Native Docs](https://reactnative.dev)
- [Expo Docs](https://docs.expo.dev)
- [React Navigation](https://reactnavigation.org)
- [Zustand](https://github.com/pmndrs/zustand)

## 📄 License

Same as original project

## 🤝 Support

For issues or questions, please refer to the original project documentation or React Native/Expo official guides.

---

**Migration Status:** ✅ Complete - All Flutter features migrated to React Native + Expo

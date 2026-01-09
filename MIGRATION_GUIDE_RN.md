# Flutter to React Native Migration Guide

## 📋 Migration Overview

This document outlines the migration from the original Flutter Mobile Dashboard to React Native + Expo implementation.

## 🔄 Component & Feature Mapping

### Architecture Changes

| Flutter | React Native | Rationale |
|---------|--------------|-----------|
| `Provider` pattern | `Zustand` store | Lighter weight, simpler API |
| `MultiProvider` | Zustand hooks | Direct store access |
| `ChangeNotifier` | Zustand actions | Cleaner action dispatching |
| `build(BuildContext)` | React functional components | Modern React patterns |
| Hive + SharedPreferences | AsyncStorage | Standard RN storage |

### Screen & Navigation

```
Flutter                     React Native
├── HomeScreen            ├── HomeScreen
├── HistoryScreen         ├── HistoryScreen
├── SettingsScreen        ├── SettingsScreen
└── Navigation            └── Bottom Tab Navigation
    (MaterialApp)             (React Navigation)
```

### UI Components

```
Flutter                     React Native
├── Scaffold              ├── SafeAreaView
├── AppBar                ├── Custom Header
├── MaterialApp           ├── NavigationContainer
├── RefreshIndicator      ├── ScrollView + RefreshControl
├── Card                  ├── View (custom styling)
├── Icon + IconButton     ├── MaterialCommunityIcons
└── CircularProgress      └── Animated Loader
```

### Services

```
Flutter                          React Native
├── NotificationService          ├── notification.service.ts
│   (Firebase Messaging)          │   (Expo Notifications)
│
├── API (http package)            └── apiClient (Axios)
│
└── Local Storage                 └── storage.service.ts
    (SharedPreferences, Hive)        (AsyncStorage)
```

## 🔄 Detailed Migrations

### 1. State Management: Provider → Zustand

**Flutter (Before):**
```dart
class HealthDataProvider extends ChangeNotifier {
  List<HealthMetric> _metrics = [];
  bool _isLoading = false;
  
  Future<void> fetchHealthMetrics() async {
    _isLoading = true;
    notifyListeners();
    // ... fetch logic
  }
}
```

**React Native (After):**
```typescript
export const useHealthStore = create<HealthStore>((set, get) => ({
  metrics: [],
  isLoading: false,
  
  fetchHealthMetrics: async () => {
    set({ isLoading: true });
    // ... fetch logic
  },
}));
```

**Usage Changes:**
```typescript
// Before (Flutter):
Consumer<HealthDataProvider>(
  builder: (context, provider, child) {
    provider.fetchHealthMetrics();
  }
)

// After (React Native):
const HomeScreen = () => {
  const { fetchHealthMetrics } = useHealthStore();
  useEffect(() => {
    fetchHealthMetrics();
  }, []);
}
```

### 2. Navigation: Native → React Navigation

**Flutter Structure:**
```dart
MaterialApp(
  home: HomeScreen(),
  theme: ThemeConfig.lightTheme,
  darkTheme: ThemeConfig.darkTheme,
)
```

**React Native Structure:**
```typescript
<NavigationContainer>
  <Tab.Navigator>
    <Tab.Screen name="Home" component={HomeScreen} />
    <Tab.Screen name="History" component={HistoryScreen} />
    <Tab.Screen name="Settings" component={SettingsScreen} />
  </Tab.Navigator>
</NavigationContainer>
```

### 3. UI Components

**Metric Card Component:**

Flutter:
```dart
class MetricCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;
  
  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, color: color),
        Expanded(child: Text(label)),
        Text(value),
      ],
    );
  }
}
```

React Native:
```typescript
export const MetricCard: React.FC<MetricCardProps> = ({
  icon,
  label,
  value,
  color,
}) => (
  <View style={styles.container}>
    <MaterialCommunityIcons name={icon} color={color} />
    <Text style={styles.label}>{label}</Text>
    <Text style={styles.value}>{value}</Text>
  </View>
);
```

### 4. Notifications: Firebase → Expo

**Firebase (Flutter):**
```dart
FirebaseMessaging.onMessage.listen((RemoteMessage message) {
  _showLocalNotification(
    title: message.notification!.title,
    body: message.notification!.body,
  );
});
```

**Expo (React Native):**
```typescript
Notifications.addNotificationReceivedListener((notification) => {
  console.log('Notification received:', notification);
});
```

### 5. Local Storage: Hive → AsyncStorage

**Hive (Flutter):**
```dart
final box = await Hive.openBox('health_metrics');
box.put('metrics', metricsJson);
final metrics = box.get('metrics');
```

**AsyncStorage (React Native):**
```typescript
await AsyncStorage.setItem('healthMetrics', JSON.stringify(metrics));
const metrics = JSON.parse(await AsyncStorage.getItem('healthMetrics'));
```

### 6. API Calls: http → Axios

**http Package (Flutter):**
```dart
final response = await http.get(
  Uri.parse('${ApiConfig.baseUrl}/health/metrics'),
  headers: ApiConfig.headers,
).timeout(const Duration(seconds: 10));

if (response.statusCode == 200) {
  final data = json.decode(response.body);
}
```

**Axios (React Native):**
```typescript
const apiClient = axios.create({
  baseURL: ApiConfig.baseUrl,
  timeout: ApiConfig.connectTimeout,
  headers: ApiConfig.headers,
});

const response = await apiClient.get('/health/metrics');
const data = response.data;
```

## 📦 Dependency Mapping

| Flutter Package | React Native Equivalent | Purpose |
|-----------------|------------------------|---------|
| `provider` | `zustand` | State management |
| `firebase_core` | `expo-notifications` | Push notifications |
| `firebase_messaging` | `expo-notifications` | Cloud messaging |
| `hive` | `@react-native-async-storage/async-storage` | Local storage |
| `shared_preferences` | `@react-native-async-storage/async-storage` | Preferences |
| `http` | `axios` | HTTP requests |
| `intl` | `dayjs` | Date formatting |
| `fl_chart` | `react-native-svg-charts` | Charts (optional) |
| `flutter_local_notifications` | `expo-notifications` | Local notifications |
| `connectivity_plus` | `@react-native-community/netinfo` | Network detection |

## 🚀 Testing the Migration

### Before Running

1. **Install Dependencies:**
   ```bash
   cd MobileDashboard_RN
   npm install
   ```

2. **Configure API:**
   ```typescript
   // src/config/api.config.ts
   export const ApiConfig = {
     baseUrl: 'YOUR_API_ENDPOINT',
     apiKey: 'YOUR_API_KEY',
   };
   ```

3. **Setup Expo:**
   ```bash
   npm install -g expo-cli
   ```

### Running

```bash
# Start dev server
npm start

# iOS
npm run ios

# Android
npm run android

# Web
npm run web
```

### Key Testing Points

- [ ] Data fetches on app load
- [ ] Pull-to-refresh works
- [ ] Navigation between tabs smooth
- [ ] Local data persists after close
- [ ] Error handling shows fallback UI
- [ ] Settings save and persist
- [ ] History view displays sorted dates
- [ ] Anomalies highlighted correctly

## ⚠️ Common Issues & Solutions

### Issue: Blank Screen

**Solution:** Check console for errors, ensure Expo CLI is latest version:
```bash
npm install -g expo-cli@latest
```

### Issue: API Calls Fail

**Solution:** Verify API configuration in `src/config/api.config.ts` and check network tab in Expo DevTools.

### Issue: Notifications Not Showing

**Solution:** 
- Check permissions are granted
- Verify Expo push token is sent to backend
- Test with `notificationService.showLocalNotification()`

### Issue: Styles Not Applied

**Solution:** RN uses different style properties. Check platform-specific code:
```typescript
const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: 16,
  }
});
```

## 📚 Migration Checklist

- [x] Project structure created
- [x] Dependencies configured
- [x] API configuration setup
- [x] State management (Zustand store)
- [x] Navigation structure
- [x] Home screen UI
- [x] History screen UI
- [x] Settings screen UI
- [x] Components (MetricCard, AnomalyAlert, Skeleton, ErrorFallback)
- [x] Services (Notifications, Storage)
- [x] Theme configuration
- [x] TypeScript types
- [x] Utility functions
- [ ] Asset images/icons
- [ ] Push notification token handling
- [ ] End-to-end testing
- [ ] Production build

## 🔗 Related Documentation

- [React Native Official Guide](https://reactnative.dev)
- [Expo Getting Started](https://docs.expo.dev)
- [React Navigation](https://reactnavigation.org)
- [Zustand Documentation](https://github.com/pmndrs/zustand)
- [Axios Documentation](https://axios-http.com)

## 💡 Next Steps

1. **Add Assets** - Copy/create images for app icons and branding
2. **Setup Backend** - Ensure API endpoints are compatible
3. **Configure Notifications** - Get Expo push tokens to backend
4. **Testing** - Run on physical devices and emulators
5. **Build for Production** - Use EAS Build for iOS/Android
6. **Deploy** - Submit to App Store and Play Store

---

**Migration Date:** January 2026
**Status:** ✅ Code Migration Complete - Ready for Testing

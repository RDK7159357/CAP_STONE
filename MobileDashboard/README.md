# Mobile Dashboard - Flutter App

## Overview
Cross-platform mobile dashboard for visualizing health monitoring data and receiving anomaly alerts.

## Features
- 📊 Real-time health metrics visualization
- 📈 Historical trend charts
- 🔔 Push notifications for anomalies
- 📱 Material Design UI
- 🌙 Dark mode support
- 📶 Offline support with local caching

## Setup

### Prerequisites
- Flutter SDK 3.13.0 or higher
- Dart SDK 3.1.0 or higher
- Android Studio / Xcode (for mobile development)
- Firebase account (for push notifications)

### Installation

1. **Install Flutter**
   ```bash
   # Download from: https://flutter.dev/docs/get-started/install
   flutter --version
   ```

2. **Create Flutter Project**
   ```bash
   cd MobileDashboard
   flutter create health_monitor_dashboard
   cd health_monitor_dashboard
   ```

3. **Install Dependencies**
   ```bash
   flutter pub get
   ```

4. **Setup Firebase**
   ```bash
   # Install Firebase CLI
   npm install -g firebase-tools
   
   # Login to Firebase
   firebase login
   
   # Initialize Firebase
   firebase init
   
   # Add Firebase to Flutter
   flutterfire configure
   ```

### Configuration

Edit `lib/config/api_config.dart`:
```dart
class ApiConfig {
  static const String baseUrl = 'YOUR_API_GATEWAY_URL';
  static const String apiKey = 'YOUR_API_KEY';
}
```

## Project Structure

```
lib/
├── main.dart
├── config/
│   ├── api_config.dart
│   └── theme_config.dart
├── models/
│   ├── health_metric.dart
│   └── user.dart
├── providers/
│   ├── health_data_provider.dart
│   └── auth_provider.dart
├── screens/
│   ├── home_screen.dart
│   ├── dashboard_screen.dart
│   ├── history_screen.dart
│   └── settings_screen.dart
├── widgets/
│   ├── metric_card.dart
│   ├── chart_widget.dart
│   └── alert_dialog.dart
└── services/
    ├── api_service.dart
    ├── notification_service.dart
    └── local_storage_service.dart
```

## Usage

### Run on Emulator/Device

```bash
# List devices
flutter devices

# Run on specific device
flutter run -d <device_id>

# Run in release mode
flutter run --release
```

### Build for Production

#### Android
```bash
flutter build apk --release
flutter build appbundle --release
```

#### iOS
```bash
flutter build ios --release
```

### Testing

```bash
# Run all tests
flutter test

# Run with coverage
flutter test --coverage
```

## Key Features Implementation

### 1. Real-time Data Fetching
```dart
// Fetch latest metrics every 30 seconds
Timer.periodic(Duration(seconds: 30), (timer) {
  fetchLatestMetrics();
});
```

### 2. Push Notifications
```dart
// Listen for anomaly notifications
FirebaseMessaging.onMessage.listen((RemoteMessage message) {
  showAnomalyAlert(message.data);
});
```

### 3. Data Visualization
Uses `fl_chart` package for beautiful, interactive charts:
- Line charts for heart rate trends
- Bar charts for steps/calories
- Pie charts for daily activity summary

### 4. Offline Support
Uses `hive` for local data caching:
```dart
// Save data locally
await Hive.box('metrics').put('latest', metricData);

// Retrieve when offline
final cachedData = Hive.box('metrics').get('latest');
```

## Screenshots

Place screenshots in `assets/screenshots/`:
- Dashboard view
- Chart details
- Alert notification
- Settings screen

## Firebase Setup for Push Notifications

1. **Create Firebase Project**
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Create new project
   - Add Android/iOS app

2. **Download Configuration Files**
   - Android: `google-services.json` → `android/app/`
   - iOS: `GoogleService-Info.plist` → `ios/Runner/`

3. **Setup Cloud Messaging**
   - Enable Firebase Cloud Messaging
   - Get server key for backend integration

4. **Configure Lambda to Send Notifications**
   ```python
   import requests
   
   def send_push_notification(user_token, title, body):
       url = 'https://fcm.googleapis.com/fcm/send'
       headers = {
           'Authorization': 'key=YOUR_SERVER_KEY',
           'Content-Type': 'application/json'
       }
       payload = {
           'to': user_token,
           'notification': {
               'title': title,
               'body': body
           }
       }
       response = requests.post(url, json=payload, headers=headers)
   ```

## Environment Variables

Create `.env` file:
```
API_BASE_URL=https://your-api.com
API_KEY=your-api-key
FIREBASE_PROJECT_ID=your-project-id
```

## Troubleshooting

**Issue**: Build fails on iOS
```bash
cd ios
pod install
cd ..
flutter clean
flutter pub get
```

**Issue**: Firebase not working
- Verify `google-services.json` / `GoogleService-Info.plist` are in correct locations
- Check Firebase configuration in `main.dart`
- Ensure all Firebase dependencies are added

**Issue**: Charts not rendering
- Check data format matches chart requirements
- Verify fl_chart version compatibility
- Clear cache: `flutter clean`

## Deployment

### Google Play Store (Android)
1. Generate signed APK
2. Create app listing
3. Upload APK/App Bundle
4. Submit for review

### App Store (iOS)
1. Create app in App Store Connect
2. Archive app in Xcode
3. Upload with Transporter
4. Submit for review

## Next Steps
- [ ] Implement user authentication
- [ ] Add more chart types
- [ ] Implement data export (PDF/CSV)
- [ ] Add multi-language support
- [ ] Implement Apple Health / Google Fit integration

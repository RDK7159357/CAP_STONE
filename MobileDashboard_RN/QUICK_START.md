# React Native Expo - Quick Start Guide

Get the Health Monitor Dashboard up and running in minutes!

## ✅ Prerequisites

- **Node.js** 16+ ([Download](https://nodejs.org))
- **npm** 8+ (comes with Node.js)
- **Expo CLI** (`npm install -g expo-cli`)
- **iOS Simulator** or **Android Emulator** (or physical device)

## 🚀 Quick Setup (5 minutes)

### 1. Navigate to Project

```bash
cd /Users/ramadugudhanush/Documents/CAP_STONE/MobileDashboard_RN
```

### 2. Install Dependencies

```bash
npm install
```

This installs all required packages including React Native, Expo, navigation, state management, and utilities.

### 3. Configure API (Important!)

Edit `src/config/api.config.ts`:

```typescript
export const ApiConfig = {
  baseUrl: 'https://your-actual-api-endpoint.com/prod/',
  apiKey: 'your-actual-api-key',
  // ... rest of config
};
```

### 4. Start Development Server

```bash
npm start
```

You'll see:
```
📱 Expo DevTools
────────────────────────────────
Press e │ open in Expo Go
Press i │ open iOS Simulator
Press a │ open Android Emulator
Press w │ open in web browser
Press r │ reload app
Press m │ toggle menu
```

### 5. Choose Your Target

**iOS Simulator:**
```bash
# Press 'i' in terminal, or:
npm run ios
```

**Android Emulator:**
```bash
# Press 'a' in terminal, or:
npm run android
```

**Web Browser:**
```bash
# Press 'w' in terminal, or:
npm run web
```

**Physical Device:**
1. Install **Expo Go** app (iOS App Store / Google Play)
2. Scan QR code displayed in terminal
3. App opens in Expo Go

## 📱 Screens Overview

### 🏠 Home Screen
- Today's health metrics summary
- Heart rate, steps, calories, distance
- Recent anomalies alert
- Pull-to-refresh to update

### 📊 History Screen
- Metrics organized by date
- Detailed time-based data
- Anomaly badges on flagged entries
- Scrollable historical view

### ⚙️ Settings Screen
- Enable/disable notifications
- Dark mode toggle
- WiFi-only sync option
- Cache management
- About section

## 🔧 Common Commands

```bash
# Development
npm start              # Start Expo dev server
npm run ios           # Run on iOS simulator
npm run android       # Run on Android emulator
npm run web           # Run in browser

# Code Quality
npm run lint          # Run ESLint
npm run type-check    # TypeScript type checking
npm test              # Run tests (if configured)

# Building
npm run build         # Build for production
```

## 🐛 Debugging

### VS Code Debug Mode
1. Open Command Palette (`Cmd+Shift+P`)
2. Select "Debug: JavaScript Debug Terminal"
3. Run `npm start`

### Expo DevTools
- **React DevTools** - Component inspection
- **Redux DevTools** - State debugging (if added)
- **Network Inspector** - API call monitoring

### Console Logging
```typescript
console.log('Debug message');
console.warn('Warning message');
console.error('Error message');
```

## 📁 Key Files to Know

| File | Purpose |
|------|---------|
| `App.tsx` | Main app entry point |
| `src/navigation/` | Tab navigation setup |
| `src/screens/` | Three main screens |
| `src/store/health.store.ts` | Global state (Zustand) |
| `src/services/` | API and notification logic |
| `src/config/api.config.ts` | API configuration |
| `src/config/theme.config.ts` | Colors and styling |
| `package.json` | Dependencies |
| `app.json` | Expo configuration |

## 🔌 API Integration

The app makes requests to:

```
GET  /health/metrics          - Fetch user metrics
POST /health/metrics          - Upload new metric
GET  /health-data/sync        - Sync data
GET  /health-data/history     - Get history
```

**Configure endpoint in:** `src/config/api.config.ts`

## 🔔 Notifications

App receives push notifications from backend:

1. **Initialization** - Automatic on app start
2. **Permissions** - Requested from user
3. **Token** - Expo token logged to console (send to backend)
4. **Receiving** - Shows alerts when anomalies detected

**Test locally:**
```typescript
// In any component
import { notificationService } from '@/services/notification.service';

notificationService.showLocalNotification(
  'Test Alert',
  'This is a test notification'
);
```

## 💾 Local Data

App automatically caches metrics in device storage:
- **Persists** after app closes
- **Updates** when new data fetched
- **Accessible offline** in History screen
- **Can be cleared** from Settings

## 🎨 Theming

Customize appearance in `src/config/theme.config.ts`:

```typescript
export const Colors = {
  primary: '#007AFF',      // Blue - primary actions
  heartRate: '#E74C3C',    // Red
  steps: '#3498DB',        // Blue
  calories: '#F39C12',     // Orange
  distance: '#2ECC71',     // Green
  anomaly: '#E67E22',      // Dark orange
  // ... more colors
};
```

## ⚡ Performance Tips

1. **Reduce Logging** - Comment out `console.log` calls
2. **Optimize Images** - Use appropriate sizes
3. **Lazy Load Data** - Implement pagination
4. **Cache Strategy** - Keep local data fresh
5. **Monitor Network** - Check API response times

## 🆘 Troubleshooting

### "Module not found" Error
```bash
# Clear cache and reinstall
rm -rf node_modules
npm install
npm start
```

### "Cannot find native module"
```bash
# Rebuild app
npm start
# Press 'r' to reload
```

### "API calls failing"
- Check internet connection
- Verify API configuration in `api.config.ts`
- Check network tab in Expo DevTools
- Ensure API server is running

### "Notifications not working"
- Allow permissions when prompted
- Check `notificationService.initialize()` in `App.tsx`
- Log Expo push token from console

## 📖 Learning Resources

- **[React Native Docs](https://reactnative.dev/)** - Official guide
- **[Expo Docs](https://docs.expo.dev/)** - Platform guide  
- **[React Navigation](https://reactnavigation.org/)** - Navigation patterns
- **[Zustand](https://github.com/pmndrs/zustand)** - State management
- **[TypeScript](https://www.typescriptlang.org/docs/)** - Type checking

## 🚀 Next Steps

1. ✅ **Test locally** - Verify all screens work
2. 🔧 **Configure API** - Connect to real backend
3. 📤 **Setup notifications** - Get tokens to backend
4. 📦 **Build for iOS** - Use EAS Build
5. 📦 **Build for Android** - Use EAS Build
6. 🎯 **Publish to stores** - App Store & Play Store

## 📞 Support

For issues:
1. Check console errors (`npm start`)
2. Review error messages
3. Check [React Native docs](https://reactnative.dev/)
4. Check [Expo troubleshooting](https://docs.expo.dev/troubleshooting/troubleshooting-overview/)

---

**Happy coding!** 🎉

Start with `npm start` and choose your platform. The app is fully functional and ready to test!

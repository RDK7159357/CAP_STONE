/**
 * Theme Configuration for React Native
 */

export const Colors = {
  // Primary colors
  primary: '#007AFF',
  
  // Metric colors
  heartRate: '#E74C3C',
  steps: '#3498DB',
  calories: '#F39C12',
  distance: '#2ECC71',
  anomaly: '#E67E22',
  
  // Neutral colors
  white: '#FFFFFF',
  black: '#000000',
  gray100: '#F5F5F5',
  gray200: '#EEEEEE',
  gray300: '#E0E0E0',
  gray400: '#BDBDBD',
  gray500: '#9E9E9E',
  gray600: '#757575',
  gray700: '#616161',
  gray800: '#424242',
  gray900: '#212121',
  
  // Semantic colors
  error: '#FF3B30',
  warning: '#FF9500',
  success: '#34C759',
  info: '#00C7BE',
};

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  '2xl': 32,
};

export const BorderRadius = {
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  full: 999,
};

export const Typography = {
  heading1: {
    fontSize: 32,
    fontWeight: '700',
    lineHeight: 40,
  },
  heading2: {
    fontSize: 28,
    fontWeight: '700',
    lineHeight: 36,
  },
  heading3: {
    fontSize: 24,
    fontWeight: '600',
    lineHeight: 32,
  },
  heading4: {
    fontSize: 20,
    fontWeight: '600',
    lineHeight: 28,
  },
  body: {
    fontSize: 16,
    fontWeight: '400',
    lineHeight: 24,
  },
  caption: {
    fontSize: 12,
    fontWeight: '400',
    lineHeight: 16,
  },
};

export const LightTheme = {
  colors: Colors,
  background: Colors.white,
  surface: Colors.gray100,
  text: Colors.gray900,
  textSecondary: Colors.gray600,
  border: Colors.gray300,
};

export const DarkTheme = {
  colors: Colors,
  background: Colors.gray900,
  surface: Colors.gray800,
  text: Colors.white,
  textSecondary: Colors.gray400,
  border: Colors.gray700,
};

export default {
  Colors,
  Spacing,
  BorderRadius,
  Typography,
  LightTheme,
  DarkTheme,
};

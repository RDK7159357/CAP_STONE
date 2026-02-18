/**
 * API Configuration
 * Replace with your actual API endpoint after cloud deployment
 */

import Constants from 'expo-constants';

const extra = Constants.expoConfig?.extra ?? {};

const apiBaseUrl =
  typeof extra.apiBaseUrl === 'string'
    ? extra.apiBaseUrl
    : 'https://u8tkgz3vsf.execute-api.ap-south-2.amazonaws.com/prod/';

const apiKey =
  typeof extra.apiKey === 'string'
    ? extra.apiKey
    : '27tpgpLoMk7A8mDknvE8S8AhzwBeS6fm1U7KpQhT';

const userId =
  typeof extra.userId === 'string'
    ? extra.userId
    : 'user_001';

const normalizedBaseUrl = apiBaseUrl.replace(/\/+$/, '');

const headers: Record<string, string> = {
  'Content-Type': 'application/json',
  'x-api-key': apiKey,
};

export const ApiConfig = {
  // AWS API Gateway endpoint (ap-south-2)
  baseUrl: normalizedBaseUrl,

  // API Key for authentication
  apiKey,

  // Demo user id used for token registration
  userId,

  // Headers
  headers,

  // Endpoints
  endpoints: {
    healthData: 'health-data/ingest',
    sync: 'health-data/sync',
    history: 'health-data/history',
    registerPushToken: 'notifications/register',
  },

  // Timeouts (in milliseconds)
  connectTimeout: 30000,
  receiveTimeout: 30000,

  // Pagination
  pageSize: 50,
};

export default ApiConfig;

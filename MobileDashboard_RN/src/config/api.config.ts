/**
 * API Configuration
 * Replace with your actual API endpoint after cloud deployment
 */

export const ApiConfig = {
  // AWS API Gateway endpoint (ap-south-2)
  baseUrl: 'https://u8tkgz3vsf.execute-api.ap-south-2.amazonaws.com/prod/',
  
  // API Key for authentication
  apiKey: '27tpgpLoMk7A8mDknvE8S8AhzwBeS6fm1U7KpQhT',

  // Demo user id used for token registration
  userId: 'user_001',
  
  // Headers
  headers: {
    'Content-Type': 'application/json',
    'x-api-key': '27tpgpLoMk7A8mDknvE8S8AhzwBeS6fm1U7KpQhT',
  },
  
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

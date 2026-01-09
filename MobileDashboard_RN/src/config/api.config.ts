/**
 * API Configuration
 * Replace with your actual API endpoint after cloud deployment
 */

export const ApiConfig = {
  // Use mock API for development
  // Replace with your actual endpoint when ready
  baseUrl: 'http://localhost:3000/api/',
  
  // AWS API Gateway endpoint (update when ready)
  // baseUrl: 'https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/prod/',
  
  // Alternative for Google Cloud
  // baseUrl: 'https://us-central1-your-project-id.cloudfunctions.net/',
  
  // API Key for authentication
  apiKey: 'development-key',
  
  // Headers
  headers: {
    'Content-Type': 'application/json',
    'x-api-key': 'development-key',
  },
  
  // Endpoints
  endpoints: {
    healthData: 'health-data/ingest',
    sync: 'health-data/sync',
    history: 'health-data/history',
  },
  
  // Timeouts (in milliseconds)
  connectTimeout: 30000,
  receiveTimeout: 30000,
  
  // Pagination
  pageSize: 50,
};

export default ApiConfig;

class ApiConfig {
  // TODO: Replace with your actual API endpoint after cloud deployment
  static const String baseUrl = 'https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/prod/';
  
  // Alternative for Google Cloud
  // static const String baseUrl = 'https://us-central1-your-project-id.cloudfunctions.net/';
  
  // API Key for authentication
  static const String apiKey = 'your-api-key-here';
  
  // Headers
  static Map<String, String> get headers => {
    'Content-Type': 'application/json',
    'x-api-key': apiKey,
  };
  
  // Endpoints
  static const String healthDataEndpoint = 'health-data/ingest';
  static const String syncEndpoint = 'health-data/sync';
  static const String historyEndpoint = 'health-data/history';
  
  // Timeouts
  static const Duration connectTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
  
  // Pagination
  static const int pageSize = 50;
}

import 'package:flutter/foundation.dart';
import '../config/api_config.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;

class HealthMetric {
  final String id;
  final DateTime timestamp;
  final int heartRate;
  final int steps;
  final double calories;
  final double distance;
  final bool isAnomaly;
  final double anomalyScore;

  HealthMetric({
    required this.id,
    required this.timestamp,
    required this.heartRate,
    required this.steps,
    required this.calories,
    required this.distance,
    this.isAnomaly = false,
    this.anomalyScore = 0.0,
  });

  factory HealthMetric.fromJson(Map<String, dynamic> json) {
    return HealthMetric(
      id: json['id'] ?? '',
      timestamp: DateTime.parse(json['timestamp']),
      heartRate: json['heart_rate'] ?? 0,
      steps: json['steps'] ?? 0,
      calories: (json['calories'] ?? 0.0).toDouble(),
      distance: (json['distance'] ?? 0.0).toDouble(),
      isAnomaly: json['is_anomaly'] ?? false,
      anomalyScore: (json['anomaly_score'] ?? 0.0).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'timestamp': timestamp.toIso8601String(),
      'heart_rate': heartRate,
      'steps': steps,
      'calories': calories,
      'distance': distance,
      'is_anomaly': isAnomaly,
      'anomaly_score': anomalyScore,
    };
  }
}

class HealthDataProvider extends ChangeNotifier {
  List<HealthMetric> _metrics = [];
  bool _isLoading = false;
  String? _error;

  List<HealthMetric> get metrics => _metrics;
  bool get isLoading => _isLoading;
  String? get error => _error;

  // Get recent anomalies
  List<HealthMetric> get recentAnomalies {
    return _metrics.where((m) => m.isAnomaly).take(5).toList();
  }

  // Get today's metrics
  HealthMetric? get todayMetrics {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    
    try {
      return _metrics.firstWhere(
        (m) => m.timestamp.isAfter(today) && m.timestamp.isBefore(today.add(const Duration(days: 1))),
      );
    } catch (e) {
      return null;
    }
  }

  // Fetch health metrics from API
  Future<void> fetchHealthMetrics() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final response = await http.get(
        Uri.parse('${ApiConfig.baseUrl}/health/metrics'),
        headers: ApiConfig.headers,
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        _metrics = data.map((json) => HealthMetric.fromJson(json)).toList();
        _metrics.sort((a, b) => b.timestamp.compareTo(a.timestamp));
      } else {
        _error = 'Failed to load health metrics: ${response.statusCode}';
      }
    } catch (e) {
      _error = 'Error fetching health metrics: $e';
      debugPrint(_error);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  // Upload health metric
  Future<bool> uploadHealthMetric(HealthMetric metric) async {
    try {
      final response = await http.post(
        Uri.parse('${ApiConfig.baseUrl}/health/metrics'),
        headers: ApiConfig.headers,
        body: json.encode(metric.toJson()),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200 || response.statusCode == 201) {
        await fetchHealthMetrics();
        return true;
      } else {
        _error = 'Failed to upload metric: ${response.statusCode}';
        notifyListeners();
        return false;
      }
    } catch (e) {
      _error = 'Error uploading metric: $e';
      notifyListeners();
      return false;
    }
  }

  // Clear error
  void clearError() {
    _error = null;
    notifyListeners();
  }
}

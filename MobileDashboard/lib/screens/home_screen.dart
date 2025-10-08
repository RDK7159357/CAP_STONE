import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/health_data_provider.dart';
import '../config/theme_config.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    // Fetch initial data
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<HealthDataProvider>().fetchHealthMetrics();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Health Monitor'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              context.read<HealthDataProvider>().fetchHealthMetrics();
            },
          ),
        ],
      ),
      body: Consumer<HealthDataProvider>(
        builder: (context, provider, child) {
          if (provider.isLoading && provider.metrics.isEmpty) {
            return const Center(child: CircularProgressIndicator());
          }

          if (provider.error != null) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.error_outline, size: 64, color: Colors.red),
                  const SizedBox(height: 16),
                  Text(
                    provider.error!,
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontSize: 16),
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () {
                      provider.clearError();
                      provider.fetchHealthMetrics();
                    },
                    child: const Text('Retry'),
                  ),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () => provider.fetchHealthMetrics(),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // Today's Summary Card
                _buildTodaySummaryCard(provider),
                const SizedBox(height: 16),

                // Recent Anomalies
                if (provider.recentAnomalies.isNotEmpty) ...[
                  _buildAnomaliesCard(provider),
                  const SizedBox(height: 16),
                ],

                // Recent Metrics
                _buildRecentMetricsSection(provider),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildTodaySummaryCard(HealthDataProvider provider) {
    final todayMetrics = provider.todayMetrics;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "Today's Summary",
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            if (todayMetrics != null) ...[
              _buildMetricRow(
                Icons.favorite,
                'Heart Rate',
                '${todayMetrics.heartRate} bpm',
                ThemeConfig.heartRateColor,
              ),
              _buildMetricRow(
                Icons.directions_walk,
                'Steps',
                '${todayMetrics.steps}',
                ThemeConfig.stepsColor,
              ),
              _buildMetricRow(
                Icons.local_fire_department,
                'Calories',
                '${todayMetrics.calories.toStringAsFixed(1)} kcal',
                ThemeConfig.caloriesColor,
              ),
              _buildMetricRow(
                Icons.straighten,
                'Distance',
                '${todayMetrics.distance.toStringAsFixed(2)} km',
                ThemeConfig.distanceColor,
              ),
            ] else ...[
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(16.0),
                  child: Text('No data available for today'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildMetricRow(IconData icon, String label, String value, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(icon, color: color, size: 28),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              label,
              style: const TextStyle(fontSize: 16),
            ),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAnomaliesCard(HealthDataProvider provider) {
    return Card(
      color: ThemeConfig.anomalyColor.withValues(alpha: 0.1),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.warning_amber_rounded, color: ThemeConfig.anomalyColor),
                SizedBox(width: 8),
                Text(
                  'Recent Anomalies',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ...provider.recentAnomalies.map((metric) {
              return ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.warning, color: ThemeConfig.anomalyColor),
                title: Text(
                  'Anomaly Score: ${metric.anomalyScore.toStringAsFixed(2)}',
                ),
                subtitle: Text(
                  _formatDateTime(metric.timestamp),
                  style: const TextStyle(fontSize: 12),
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildRecentMetricsSection(HealthDataProvider provider) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Recent Metrics',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        if (provider.metrics.isEmpty)
          const Center(
            child: Padding(
              padding: EdgeInsets.all(32.0),
              child: Text('No metrics available'),
            ),
          )
        else
          ...provider.metrics.take(10).map((metric) {
            return Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor: metric.isAnomaly
                      ? ThemeConfig.anomalyColor
                      : ThemeConfig.heartRateColor,
                  child: Icon(
                    metric.isAnomaly ? Icons.warning : Icons.favorite,
                    color: Colors.white,
                  ),
                ),
                title: Text(
                  'HR: ${metric.heartRate} bpm | Steps: ${metric.steps}',
                ),
                subtitle: Text(_formatDateTime(metric.timestamp)),
                trailing: metric.isAnomaly
                    ? Chip(
                        label: const Text(
                          'Anomaly',
                          style: TextStyle(fontSize: 10),
                        ),
                        backgroundColor: ThemeConfig.anomalyColor.withValues(alpha: 0.2),
                      )
                    : null,
              ),
            );
          }),
      ],
    );
  }

  String _formatDateTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inHours < 1) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inDays < 1) {
      return '${difference.inHours}h ago';
    } else {
      return '${dateTime.day}/${dateTime.month}/${dateTime.year} ${dateTime.hour}:${dateTime.minute.toString().padLeft(2, '0')}';
    }
  }
}

/**
 * Dashboard Page - Main overview of the AI Query Analyzer
 */
import React, { useEffect, useState } from 'react';
import {
  Activity,
  Database,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Clock,
  Zap,
} from 'lucide-react';
import { getStats, getCollectorStatus, getAnalyzerStatus, getHealth } from '../services/api';
import type { StatsResponse, CollectorStatus, AnalyzerStatus, HealthStatus } from '../types';

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [collectorStatus, setCollectorStatus] = useState<CollectorStatus | null>(null);
  const [analyzerStatus, setAnalyzerStatus] = useState<AnalyzerStatus | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
    // Refresh every 30 seconds
    const interval = setInterval(loadDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      const [statsData, collectorData, analyzerData, healthData] = await Promise.all([
        getStats(),
        getCollectorStatus(),
        getAnalyzerStatus(),
        getHealth(),
      ]);

      setStats(statsData);
      setCollectorStatus(collectorData);
      setAnalyzerStatus(analyzerData);
      setHealth(healthData);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  const getHealthStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600';
      case 'degraded':
        return 'text-yellow-600';
      case 'unhealthy':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getImprovementLevelColor = (level: string) => {
    switch (level) {
      case 'CRITICAL':
        return 'bg-red-100 text-red-800';
      case 'HIGH':
        return 'bg-orange-100 text-orange-800';
      case 'MEDIUM':
        return 'bg-yellow-100 text-yellow-800';
      case 'LOW':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">AI Query Analyzer Dashboard</h1>
          <p className="mt-2 text-gray-600">
            Monitor slow queries and optimization suggestions in real-time
          </p>
        </div>

        {/* Health Status */}
        {health && (
          <div className="mb-6 p-4 bg-white rounded-lg shadow-md border-l-4 border-green-500">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <CheckCircle className={getHealthStatusColor(health.status)} size={24} />
                <div>
                  <p className="font-semibold">System Status: {health.status.toUpperCase()}</p>
                  <p className="text-sm text-gray-600">
                    Uptime: {Math.floor(health.uptime_seconds / 3600)}h{' '}
                    {Math.floor((health.uptime_seconds % 3600) / 60)}m
                  </p>
                </div>
              </div>
              <div className="flex space-x-4">
                <div className="text-center">
                  <p className="text-xs text-gray-500">Database</p>
                  <p className={`font-semibold ${getHealthStatusColor(health.database.status)}`}>
                    {health.database.status}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-gray-500">Redis</p>
                  <p className={`font-semibold ${getHealthStatusColor(health.redis.status)}`}>
                    {health.redis.status}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats && (
            <>
              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Total Queries</p>
                    <p className="text-3xl font-bold text-gray-900">{stats.total_queries}</p>
                  </div>
                  <Database className="text-primary-600" size={32} />
                </div>
              </div>

              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Analyzed</p>
                    <p className="text-3xl font-bold text-green-600">
                      {stats.analysis_status.analyzed}
                    </p>
                  </div>
                  <CheckCircle className="text-green-600" size={32} />
                </div>
              </div>

              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Pending Analysis</p>
                    <p className="text-3xl font-bold text-yellow-600">
                      {stats.analysis_status.pending}
                    </p>
                  </div>
                  <Clock className="text-yellow-600" size={32} />
                </div>
              </div>

              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Last 24h</p>
                    <p className="text-3xl font-bold text-primary-600">
                      {stats.recent_activity.last_24h}
                    </p>
                  </div>
                  <TrendingUp className="text-primary-600" size={32} />
                </div>
              </div>
            </>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Improvement Level Distribution */}
          {stats && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4 flex items-center">
                <AlertTriangle className="mr-2 text-orange-600" size={24} />
                Improvement Potential
              </h2>
              <div className="space-y-3">
                {Object.entries(stats.improvement_distribution).map(([level, count]) => (
                  <div key={level} className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <span className={`badge ${getImprovementLevelColor(level)}`}>{level}</span>
                      <span className="text-sm text-gray-600">queries</span>
                    </div>
                    <span className="font-semibold text-gray-900">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Database Distribution */}
          {stats && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4 flex items-center">
                <Database className="mr-2 text-primary-600" size={24} />
                Databases
              </h2>
              <div className="space-y-3">
                {Object.entries(stats.databases).map(([dbType, data]) => (
                  <div key={dbType} className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">{dbType.toUpperCase()}</p>
                      <p className="text-sm text-gray-600">
                        Avg: {data.avg_duration_ms.toFixed(2)}ms
                      </p>
                    </div>
                    <span className="badge badge-info">{data.count} queries</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Collector Status */}
        {collectorStatus && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4 flex items-center">
              <Activity className="mr-2 text-primary-600" size={24} />
              Collector Status
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-gray-600">MySQL Collected</p>
                <p className="text-2xl font-bold text-gray-900">
                  {collectorStatus.mysql_total_collected}
                </p>
                <p className="text-xs text-gray-500">
                  Last run:{' '}
                  {collectorStatus.mysql_last_run
                    ? new Date(collectorStatus.mysql_last_run).toLocaleTimeString()
                    : 'Never'}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">PostgreSQL Collected</p>
                <p className="text-2xl font-bold text-gray-900">
                  {collectorStatus.postgres_total_collected}
                </p>
                <p className="text-xs text-gray-500">
                  Last run:{' '}
                  {collectorStatus.postgres_last_run
                    ? new Date(collectorStatus.postgres_last_run).toLocaleTimeString()
                    : 'Never'}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Analyzed</p>
                <p className="text-2xl font-bold text-gray-900">
                  {collectorStatus.total_analyzed}
                </p>
                <p className="text-xs text-gray-500">
                  Last run:{' '}
                  {collectorStatus.analyzer_last_run
                    ? new Date(collectorStatus.analyzer_last_run).toLocaleTimeString()
                    : 'Never'}
                </p>
              </div>
            </div>

            {/* Scheduled Jobs */}
            <div className="mt-4 pt-4 border-t border-gray-200">
              <p className="text-sm font-medium text-gray-700 mb-2">Scheduled Jobs:</p>
              <div className="space-y-1">
                {collectorStatus.jobs.map((job) => (
                  <div key={job.id} className="flex justify-between text-sm">
                    <span className="text-gray-600">{job.name}</span>
                    <span className="text-gray-500">
                      Next: {job.next_run ? new Date(job.next_run).toLocaleTimeString() : 'N/A'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Analyzer Status */}
        {analyzerStatus && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center">
              <Zap className="mr-2 text-yellow-600" size={24} />
              Analyzer Status
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-gray-600">High Impact</p>
                <p className="text-2xl font-bold text-red-600">
                  {analyzerStatus.analyses.high_impact}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Medium Impact</p>
                <p className="text-2xl font-bold text-orange-600">
                  {analyzerStatus.analyses.medium_impact}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Low Impact</p>
                <p className="text-2xl font-bold text-yellow-600">
                  {analyzerStatus.analyses.low_impact}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Total Analyses</p>
                <p className="text-2xl font-bold text-gray-900">
                  {analyzerStatus.analyses.total}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;

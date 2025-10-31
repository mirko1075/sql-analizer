/**
 * Statistics Page - Performance metrics and trends
 */
import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  Database,
  Clock,
  AlertTriangle,
  CheckCircle,
  Activity,
} from 'lucide-react';
import { getStats, getTopSlowQueries, getUnanalyzedQueries } from '../services/api';
import type { StatsResponse, SlowQuery } from '../types';

const Statistics: React.FC = () => {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [topQueries, setTopQueries] = useState<SlowQuery[]>([]);
  const [unanalyzedQueries, setUnanalyzedQueries] = useState<SlowQuery[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStatistics();
  }, []);

  const loadStatistics = async () => {
    try {
      setLoading(true);
      const [statsData, topData, unanalyzedData] = await Promise.all([
        getStats(),
        getTopSlowQueries(10),
        getUnanalyzedQueries(10),
      ]);

      setStats(statsData);
      setTopQueries(topData);
      setUnanalyzedQueries(unanalyzedData);
    } catch (error) {
      console.error('Failed to load statistics:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (ms: number): string => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
    return `${(ms / 60000).toFixed(2)}m`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          <p className="mt-4 text-gray-600">Loading statistics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center">
            <BarChart3 className="mr-3 text-primary-600" size={32} />
            Statistics & Trends
          </h1>
          <p className="mt-2 text-gray-600">
            Performance metrics and query analysis overview
          </p>
        </div>

        {/* Overview Cards */}
        {stats && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Total Queries</p>
                    <p className="text-3xl font-bold text-gray-900">{stats.total_slow_queries}</p>
                  </div>
                  <Database className="text-primary-600" size={32} />
                </div>
              </div>

              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Analyzed</p>
                    <p className="text-3xl font-bold text-green-600">
                      {stats.total_analyzed}
                    </p>
                  </div>
                  <CheckCircle className="text-green-600" size={32} />
                </div>
              </div>

              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Pending</p>
                    <p className="text-3xl font-bold text-yellow-600">
                      {stats.total_pending}
                    </p>
                  </div>
                  <Clock className="text-yellow-600" size={32} />
                </div>
              </div>

              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Databases Monitored</p>
                    <p className="text-3xl font-bold text-primary-600">
                      {stats.databases_monitored}
                    </p>
                  </div>
                  <Activity className="text-primary-600" size={32} />
                </div>
              </div>
            </div>

            {/* Improvement Distribution */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-8">
              <h2 className="text-xl font-semibold mb-4 flex items-center">
                <AlertTriangle className="mr-2 text-orange-600" size={24} />
                Improvement Potential Distribution
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {stats.improvement_summary.map((item) => {
                  const colors: Record<string, string> = {
                    CRITICAL: 'bg-red-500',
                    HIGH: 'bg-orange-500',
                    MEDIUM: 'bg-yellow-500',
                    LOW: 'bg-green-500',
                  };

                  return (
                    <div key={item.improvement_level} className="text-center">
                      <div
                        className={`${colors[item.improvement_level] || 'bg-gray-500'} text-white rounded-lg p-4 mb-2`}
                      >
                        <p className="text-3xl font-bold">{item.count}</p>
                      </div>
                      <p className="text-sm text-gray-600">{item.improvement_level}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Top Slow Queries */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center">
              <Clock className="mr-2 text-red-600" size={24} />
              Slowest Queries
            </h2>
            <div className="space-y-3">
              {topQueries.length > 0 ? (
                topQueries.map((query, index) => (
                  <div key={query.id} className="border-l-4 border-red-500 pl-4 py-2">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-900">
                        #{index + 1} • {query.source_db_type.toUpperCase()}
                      </span>
                      <span className="text-sm font-bold text-red-600">
                        {formatDuration(query.avg_duration_ms)}
                      </span>
                    </div>
                    <code className="text-xs text-gray-600 font-mono">
                      {query.fingerprint.substring(0, 80)}...
                    </code>
                  </div>
                ))
              ) : (
                <p className="text-gray-500 text-center py-4">No slow queries found</p>
              )}
            </div>
          </div>

          {/* Unanalyzed Queries */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center">
              <AlertTriangle className="mr-2 text-yellow-600" size={24} />
              Pending Analysis
            </h2>
            <div className="space-y-3">
              {unanalyzedQueries.length > 0 ? (
                unanalyzedQueries.map((query, index) => (
                  <div key={query.id} className="border-l-4 border-yellow-500 pl-4 py-2">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-900">
                        #{index + 1} • {query.source_db_type.toUpperCase()}
                      </span>
                      <span className="badge badge-warning">Not Analyzed</span>
                    </div>
                    <code className="text-xs text-gray-600 font-mono">
                      {query.fingerprint.substring(0, 80)}...
                    </code>
                  </div>
                ))
              ) : (
                <p className="text-gray-500 text-center py-4">All queries analyzed!</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Statistics;

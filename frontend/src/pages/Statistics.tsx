/**
 * Statistics Page - Performance trends and analytics
 */
import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  BarChart3,
  Brain,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import {
  getPerformanceTrends,
  getQueryDistribution,
  getAIInsights,
} from '../services/api';

interface DailyMetric {
  metric_date: string;
  source_db_type: string;
  source_db_host: string;
  total_queries: number;
  unique_fingerprints: number;
  avg_duration_ms?: number;
  p95_duration_ms?: number;
  p99_duration_ms?: number;
  avg_rows_examined?: number;
  avg_rows_returned?: number;
  avg_efficiency_ratio?: number;
  analyzed_count: number;
  high_impact_count: number;
}

interface PerformanceTrends {
  metrics: DailyMetric[];
  date_range: {
    start: string;
    end: string;
  };
  summary: {
    total_queries: number;
    avg_duration_ms: number;
    max_p95_duration_ms: number;
    total_high_impact: number;
    days_covered: number;
  };
}

interface TopQueryPattern {
  fingerprint: string;
  source_db_type: string;
  source_db_host: string;
  execution_count: number;
  total_duration_ms?: number;
  avg_duration_ms?: number;
  max_duration_ms?: number;
  p95_duration_ms?: number;
  avg_efficiency_ratio?: number;
  improvement_level?: string;
  first_seen: string;
  last_seen: string;
  representative_query_id?: string;
}

interface EfficiencyBucket {
  range_label: string;
  count: number;
  percentage: number;
}

interface QueryDistribution {
  top_slowest: TopQueryPattern[];
  top_frequent: TopQueryPattern[];
  top_inefficient: TopQueryPattern[];
  efficiency_histogram: EfficiencyBucket[];
}

interface AIInsightQuery {
  fingerprint: string;
  source_db_type: string;
  source_db_host: string;
  execution_count: number;
  avg_duration_ms?: number;
  improvement_level?: string;
  first_seen: string;
  last_seen: string;
  representative_query_id?: string;
}

interface AIInsights {
  high_priority_queries: AIInsightQuery[];
  recently_analyzed: AIInsightQuery[];
  total_analyzed: number;
  analysis_distribution: Record<string, number>;
}

const Statistics: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [performanceTrends, setPerformanceTrends] = useState<PerformanceTrends | null>(null);
  const [queryDistribution, setQueryDistribution] = useState<QueryDistribution | null>(null);
  const [aiInsights, setAIInsights] = useState<AIInsights | null>(null);
  const [timeRange, setTimeRange] = useState(7);

  useEffect(() => {
    loadData();
  }, [timeRange]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [trends, distribution, insights] = await Promise.all([
        getPerformanceTrends({ days: timeRange }),
        getQueryDistribution({ limit: 10 }),
        getAIInsights({ limit: 10 }),
      ]);

      setPerformanceTrends(trends);
      setQueryDistribution(distribution);
      setAIInsights(insights);
    } catch (error) {
      console.error('Failed to load statistics:', error);
    } finally {
      setLoading(false);
    }
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
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center">
              <TrendingUp className="mr-3 text-primary-600" size={32} />
              Statistics & Trends
            </h1>
            <p className="mt-2 text-gray-600">
              Performance metrics and query analysis insights
            </p>
          </div>
          <div className="flex items-center space-x-4">
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(parseInt(e.target.value))}
              className="border border-gray-300 rounded-lg px-4 py-2 bg-white"
            >
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
            <button
              onClick={loadData}
              className="btn-secondary flex items-center space-x-2"
            >
              <RefreshCw size={18} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Performance Summary Cards */}
        {performanceTrends && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-sm font-medium text-gray-600">Total Queries</h3>
              <p className="text-3xl font-bold text-gray-900 mt-2">
                {performanceTrends.summary.total_queries.toLocaleString()}
              </p>
            </div>
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-sm font-medium text-gray-600">Avg Duration</h3>
              <p className="text-3xl font-bold text-gray-900 mt-2">
                {performanceTrends.summary.avg_duration_ms.toFixed(0)}ms
              </p>
            </div>
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-sm font-medium text-gray-600">Max P95 Duration</h3>
              <p className="text-3xl font-bold text-gray-900 mt-2">
                {performanceTrends.summary.max_p95_duration_ms.toFixed(0)}ms
              </p>
            </div>
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-sm font-medium text-gray-600">High Impact Queries</h3>
              <p className="text-3xl font-bold text-red-600 mt-2">
                {performanceTrends.summary.total_high_impact}
              </p>
            </div>
          </div>
        )}

        {/* Performance Trends Section */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <TrendingUp className="mr-2 text-primary-600" size={24} />
            Performance Trends
          </h2>

          {performanceTrends && performanceTrends.metrics && Array.isArray(performanceTrends.metrics) && performanceTrends.metrics.length > 0 ? (
            <div className="space-y-6">
              {/* Daily Query Volume Chart */}
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-3">Daily Query Volume</h3>
                <div className="flex items-end space-x-2 h-48">
                  {(performanceTrends.metrics || []).map((metric: DailyMetric, idx: number) => {
                    const maxQueries = Math.max(...(performanceTrends.metrics || []).map((m: DailyMetric) => m.total_queries || 0));
                    const heightPercent = maxQueries > 0 ? (metric.total_queries / maxQueries) * 100 : 0;

                    return (
                      <div key={idx} className="flex-1 flex flex-col items-center">
                        <div
                          className="w-full bg-primary-500 rounded-t hover:bg-primary-600 transition-colors cursor-pointer"
                          style={{ height: `${heightPercent}%` }}
                          title={`${metric.total_queries} queries`}
                        ></div>
                        <p className="text-xs text-gray-500 mt-2 transform -rotate-45 origin-top-left">
                          {new Date(metric.metric_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Average Duration Trend */}
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-3">Average Duration (ms)</h3>
                <div className="flex items-end space-x-2 h-48">
                  {(performanceTrends.metrics || []).map((metric: DailyMetric, idx: number) => {
                    const maxDuration = Math.max(...(performanceTrends.metrics || []).map((m: DailyMetric) => m.avg_duration_ms || 0), 1);
                    const heightPercent = maxDuration > 0 ? ((metric.avg_duration_ms || 0) / maxDuration) * 100 : 0;
                    const color = (metric.avg_duration_ms || 0) > 5000 ? 'bg-red-500' : (metric.avg_duration_ms || 0) > 1000 ? 'bg-yellow-500' : 'bg-green-500';

                    return (
                      <div key={idx} className="flex-1 flex flex-col items-center">
                        <div
                          className={`w-full ${color} rounded-t hover:opacity-80 transition-opacity cursor-pointer`}
                          style={{ height: `${heightPercent}%` }}
                          title={`${metric.avg_duration_ms?.toFixed(0)}ms avg`}
                        ></div>
                        <p className="text-xs text-gray-500 mt-2 transform -rotate-45 origin-top-left">
                          {new Date(metric.metric_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-gray-600 text-center py-8">
              No performance trend data available for the selected time range
            </div>
          )}
        </div>

        {/* Query Distribution Section */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <BarChart3 className="mr-2 text-primary-600" size={24} />
            Query Distribution
          </h2>

          {queryDistribution && (
            <div className="space-y-6">
              {/* Top Slowest Queries */}
              <div>
                <h3 className="text-lg font-medium mb-3 text-gray-900">Top 5 Slowest Queries</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Query Pattern</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Avg Duration</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Executions</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Impact</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {(queryDistribution.top_slowest || []).slice(0, 5).map((query: TopQueryPattern, idx: number) => (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm text-gray-900 max-w-md truncate">
                            {query.fingerprint.substring(0, 80)}...
                          </td>
                          <td className="px-4 py-3 text-sm">
                            <span className="font-semibold text-red-600">
                              {(query.avg_duration_ms || 0).toFixed(0)}ms
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600">
                            {query.execution_count}
                          </td>
                          <td className="px-4 py-3 text-sm">
                            <span className={`px-2 py-1 rounded text-xs font-semibold ${
                              query.improvement_level === 'HIGH' || query.improvement_level === 'CRITICAL'
                                ? 'bg-red-100 text-red-800'
                                : query.improvement_level === 'MEDIUM'
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-green-100 text-green-800'
                            }`}>
                              {query.improvement_level || 'N/A'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Efficiency Histogram */}
              {queryDistribution.efficiency_histogram && Array.isArray(queryDistribution.efficiency_histogram) && queryDistribution.efficiency_histogram.length > 0 && (
                <div>
                  <h3 className="text-lg font-medium mb-3 text-gray-900">Efficiency Distribution</h3>
                  <div className="grid grid-cols-5 gap-4">
                    {(queryDistribution.efficiency_histogram || []).map((bucket: EfficiencyBucket, idx: number) => (
                      <div key={idx} className="bg-gray-50 rounded-lg p-4 text-center">
                        <p className="text-sm font-medium text-gray-700">{bucket.range_label}</p>
                        <p className="text-2xl font-bold text-gray-900 mt-2">{bucket.count}</p>
                        <p className="text-xs text-gray-600 mt-1">{bucket.percentage.toFixed(1)}%</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* AI Insights Section */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <Brain className="mr-2 text-primary-600" size={24} />
            AI Insights
          </h2>

          {aiInsights && (
            <div className="space-y-6">
              {/* Summary Stats */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-blue-50 rounded-lg p-4 text-center">
                  <p className="text-sm font-medium text-blue-700">Total Analyzed</p>
                  <p className="text-2xl font-bold text-blue-900 mt-2">
                    {aiInsights.total_analyzed}
                  </p>
                </div>
                {Object.entries(aiInsights.analysis_distribution).map(([level, count]: [string, number]) => (
                  <div
                    key={level}
                    className={`rounded-lg p-4 text-center ${
                      level === 'HIGH' || level === 'CRITICAL'
                        ? 'bg-red-50'
                        : level === 'MEDIUM'
                        ? 'bg-yellow-50'
                        : 'bg-green-50'
                    }`}
                  >
                    <p className={`text-sm font-medium ${
                      level === 'HIGH' || level === 'CRITICAL'
                        ? 'text-red-700'
                        : level === 'MEDIUM'
                        ? 'text-yellow-700'
                        : 'text-green-700'
                    }`}>
                      {level} Impact
                    </p>
                    <p className={`text-2xl font-bold mt-2 ${
                      level === 'HIGH' || level === 'CRITICAL'
                        ? 'text-red-900'
                        : level === 'MEDIUM'
                        ? 'text-yellow-900'
                        : 'text-green-900'
                    }`}>
                      {count}
                    </p>
                  </div>
                ))}
              </div>

              {/* High Priority Queries */}
              {aiInsights.high_priority_queries && Array.isArray(aiInsights.high_priority_queries) && aiInsights.high_priority_queries.length > 0 && (
                <div>
                  <h3 className="text-lg font-medium mb-3 text-gray-900 flex items-center">
                    <AlertCircle className="mr-2 text-red-600" size={20} />
                    High Priority Queries
                  </h3>
                  <div className="space-y-3">
                    {(aiInsights.high_priority_queries || []).slice(0, 5).map((query: AIInsightQuery, idx: number) => (
                      <div key={idx} className="border-l-4 border-red-500 bg-red-50 p-4 rounded">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <p className="text-sm font-mono text-gray-800 mb-2">
                              {query.fingerprint.substring(0, 120)}...
                            </p>
                            <div className="flex items-center space-x-4 text-xs text-gray-600">
                              <span>Executions: {query.execution_count}</span>
                              <span>Avg: {query.avg_duration_ms?.toFixed(0)}ms</span>
                              <span className="font-semibold text-red-600">
                                {query.improvement_level} IMPACT
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Statistics;

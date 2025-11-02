/**
 * Slow Queries Page - List and detail view of slow queries
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Database,
  Clock,
  AlertCircle,
  ChevronRight,
  Filter,
  RefreshCw,
} from 'lucide-react';
import { getSlowQueries } from '../services/api';
import type { SlowQuery, PaginatedResponse } from '../types';
import { getErrorMessage } from '../utils/errorHandler';

const SlowQueries: React.FC = () => {
  const navigate = useNavigate();
  const [queries, setQueries] = useState<PaginatedResponse<SlowQuery> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [filterDbType, setFilterDbType] = useState<string>('');

  const loadQueries = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await getSlowQueries(page, pageSize, filterDbType || undefined);
      setQueries(data);
    } catch (err) {
      console.error('Failed to load queries:', err);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueries();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, filterDbType]);

  const formatDuration = (ms: number): string => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
    return `${(ms / 60000).toFixed(2)}m`;
  };

  const getImprovementLevelColor = (level?: string) => {
    switch (level) {
      case 'CRITICAL':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'HIGH':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'MEDIUM':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'LOW':
        return 'bg-green-100 text-green-800 border-green-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getEfficiencyRatioColor = (ratio?: number) => {
    if (!ratio) return 'bg-gray-100 text-gray-600';
    if (ratio > 100) return 'bg-red-100 text-red-800';
    if (ratio > 10) return 'bg-yellow-100 text-yellow-800';
    return 'bg-green-100 text-green-800';
  };

  const formatEfficiencyRatio = (ratio?: number) => {
    if (!ratio) return 'N/A';
    if (ratio < 10) return ratio.toFixed(1);
    return Math.round(ratio).toString();
  };

  if (loading && !queries) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          <p className="mt-4 text-gray-600">Loading queries...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center max-w-md">
          <div className="rounded-md bg-red-50 p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <AlertCircle className="h-5 w-5 text-red-400" />
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Failed to load slow queries</h3>
                <p className="mt-2 text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
          <button
            onClick={loadQueries}
            className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center">
            <Database className="mr-3 text-primary-600" size={32} />
            Slow Queries
          </h1>
          <p className="mt-2 text-gray-600">
            Analyze and optimize slow database queries
          </p>
        </div>

        {/* Filters and Actions */}
        <div className="bg-white rounded-lg shadow-md p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <Filter size={20} className="text-gray-500" />
                <select
                  value={filterDbType}
                  onChange={(e) => {
                    setFilterDbType(e.target.value);
                    setPage(1);
                  }}
                  className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">All Databases</option>
                  <option value="mysql">MySQL</option>
                  <option value="postgres">PostgreSQL</option>
                </select>
              </div>

              {queries && (
                <span className="text-sm text-gray-600">
                  Showing {queries.items.length} of {queries.total} queries
                </span>
              )}
            </div>

            <button
              onClick={loadQueries}
              disabled={loading}
              className="btn-secondary flex items-center space-x-2"
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Queries List */}
        <div className="space-y-4">
          {queries?.items.map((query) => (
            <div
              key={query.id}
              onClick={() => navigate(`/queries/${query.id}`)}
              className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow cursor-pointer"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  {/* Query Fingerprint */}
                  <div className="flex items-start space-x-3 mb-3">
                    <Database className="text-gray-400 mt-1" size={20} />
                    <div className="flex-1">
                      <code className="text-sm text-gray-800 font-mono bg-gray-50 px-2 py-1 rounded">
                        {query.fingerprint.length > 120
                          ? query.fingerprint.substring(0, 120) + '...'
                          : query.fingerprint}
                      </code>
                    </div>
                  </div>

                  {/* Metrics */}
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-4">
                    <div>
                      <p className="text-xs text-gray-500">Avg Duration</p>
                      <p className="text-lg font-semibold text-gray-900">
                        {formatDuration(query.avg_duration_ms)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">P95 Duration</p>
                      <p className="text-lg font-semibold text-orange-600">
                        {formatDuration(query.p95_duration_ms)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Executions</p>
                      <p className="text-lg font-semibold text-primary-600">
                        {query.execution_count.toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Efficiency Ratio</p>
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded text-sm font-semibold ${getEfficiencyRatioColor(query.avg_efficiency_ratio)}`}>
                        {formatEfficiencyRatio(query.avg_efficiency_ratio)}:1
                      </span>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Database</p>
                      <p className="text-lg font-semibold text-gray-900 uppercase">
                        {query.source_db_type}
                      </p>
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200">
                    <div className="flex items-center space-x-4 flex-wrap gap-y-2">
                      <span className="text-xs text-gray-500">
                        <Clock size={14} className="inline mr-1" />
                        First: {new Date(query.first_seen).toLocaleDateString()}
                      </span>
                      <span className="text-xs text-gray-500">
                        <Clock size={14} className="inline mr-1" />
                        Last: {new Date(query.last_seen).toLocaleString()}
                      </span>
                      {query.has_analysis && query.max_improvement_level && (
                        <span
                          className={`badge ${getImprovementLevelColor(
                            query.max_improvement_level
                          )}`}
                        >
                          {query.max_improvement_level} Impact
                        </span>
                      )}
                      {!query.has_analysis && (
                        <span className="badge bg-gray-100 text-gray-600 border border-gray-300">
                          Not Analyzed
                        </span>
                      )}
                    </div>

                    <ChevronRight className="text-gray-400" size={20} />
                  </div>
                </div>
              </div>
            </div>
          ))}

          {queries?.items.length === 0 && (
            <div className="bg-white rounded-lg shadow-md p-12 text-center">
              <AlertCircle className="mx-auto text-gray-400 mb-4" size={48} />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No queries found</h3>
              <p className="text-gray-600">
                {filterDbType
                  ? `No slow queries found for ${filterDbType.toUpperCase()}`
                  : 'No slow queries have been collected yet'}
              </p>
            </div>
          )}
        </div>

        {/* Pagination */}
        {queries && queries.total_pages > 1 && (
          <div className="mt-6 flex items-center justify-between">
            <div className="text-sm text-gray-600">
              Page {queries.page} of {queries.total_pages}
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={queries.page === 1}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                onClick={() => setPage((p) => Math.min(queries.total_pages, p + 1))}
                disabled={queries.page === queries.total_pages}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SlowQueries;

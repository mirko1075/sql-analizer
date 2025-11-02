/**
 * Collectors Page - Manage collectors and scheduler
 */
import React, { useState, useEffect } from 'react';
import {
  Activity,
  PlayCircle,
  PauseCircle,
  RefreshCw,
  Database,
} from 'lucide-react';
import {
  getCollectorStatus,
  getAnalyzerStatus,
  triggerMySQLCollection,
  triggerPostgreSQLCollection,
  triggerAnalysis,
  startScheduler,
  stopScheduler,
} from '../services/api';
import type { CollectorStatus, AnalyzerStatus } from '../types';

const Collectors: React.FC = () => {
  const [collectorStatus, setCollectorStatus] = useState<CollectorStatus | null>(null);
  const [analyzerStatus, setAnalyzerStatus] = useState<AnalyzerStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    loadStatus();
    // Refresh every 10 seconds
    const interval = setInterval(loadStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadStatus = async () => {
    try {
      const [collectorData, analyzerData] = await Promise.all([
        getCollectorStatus(),
        getAnalyzerStatus(),
      ]);

      setCollectorStatus(collectorData);
      setAnalyzerStatus(analyzerData);
    } catch (error) {
      console.error('Failed to load status:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (action: string, fn: () => Promise<void>) => {
    try {
      setActionLoading(action);
      await fn();
      await loadStatus();
    } catch (error) {
      console.error(`Failed to execute ${action}:`, error);
      alert(`Failed to execute ${action}. Check console for details.`);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          <p className="mt-4 text-gray-600">Loading collectors...</p>
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
            <Activity className="mr-3 text-primary-600" size={32} />
            Collectors & Scheduler
          </h1>
          <p className="mt-2 text-gray-600">
            Manage data collection and analysis scheduling
          </p>
        </div>

        {/* Scheduler Status */}
        {collectorStatus && (
          <div
            className={`mb-8 p-6 rounded-lg shadow-md ${
              collectorStatus.is_running
                ? 'bg-green-50 border-l-4 border-green-500'
                : 'bg-yellow-50 border-l-4 border-yellow-500'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                {collectorStatus.is_running ? (
                  <PlayCircle className="text-green-600" size={32} />
                ) : (
                  <PauseCircle className="text-yellow-600" size={32} />
                )}
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">
                    Scheduler Status:{' '}
                    {collectorStatus.is_running ? (
                      <span className="text-green-600">Running</span>
                    ) : (
                      <span className="text-yellow-600">Stopped</span>
                    )}
                  </h2>
                  <p className="text-sm text-gray-600">
                    {collectorStatus.is_running
                      ? 'Automated collection and analysis is active'
                      : 'Scheduler is not running - use manual triggers'}
                  </p>
                  <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm text-gray-600">
                    <div className="bg-white/70 rounded-md px-3 py-2 shadow-sm">
                      <p className="font-semibold text-gray-900">
                        {collectorStatus.mysql_total_collected.toLocaleString()}
                      </p>
                      <p>Total MySQL queries collected</p>
                    </div>
                    <div className="bg-white/70 rounded-md px-3 py-2 shadow-sm">
                      <p className="font-semibold text-gray-900">
                        {collectorStatus.postgres_total_collected.toLocaleString()}
                      </p>
                      <p>Total PostgreSQL queries collected</p>
                    </div>
                    <div className="bg-white/70 rounded-md px-3 py-2 shadow-sm">
                      <p className="font-semibold text-gray-900">
                        {collectorStatus.total_analyzed.toLocaleString()}
                      </p>
                      <p>Queries analyzed</p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="flex space-x-2">
                {!collectorStatus.is_running ? (
                  <button
                    onClick={() => handleAction('start-scheduler', () => startScheduler(5))}
                    disabled={actionLoading === 'start-scheduler'}
                    className="btn-primary flex items-center space-x-2"
                  >
                    <PlayCircle size={18} />
                    <span>{actionLoading === 'start-scheduler' ? 'Starting...' : 'Start'}</span>
                  </button>
                ) : (
                  <button
                    onClick={() => handleAction('stop-scheduler', stopScheduler)}
                    disabled={actionLoading === 'stop-scheduler'}
                    className="btn-secondary flex items-center space-x-2"
                  >
                    <PauseCircle size={18} />
                    <span>{actionLoading === 'stop-scheduler' ? 'Stopping...' : 'Stop'}</span>
                  </button>
                )}
                <button
                  onClick={loadStatus}
                  disabled={loading}
                  className="btn-secondary flex items-center space-x-2"
                >
                  <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
                  <span>Refresh</span>
                </button>
              </div>
            </div>

            {/* Scheduled Jobs */}
            {collectorStatus.is_running && collectorStatus.jobs.length > 0 && (
              <div className="mt-4 pt-4 border-t border-green-200">
                <h3 className="text-sm font-medium text-gray-700 mb-2">Scheduled Jobs:</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {collectorStatus.jobs.map((job) => (
                    <div key={job.id} className="bg-white rounded-lg p-3 shadow-sm">
                      <p className="text-sm font-medium text-gray-900">{job.name}</p>
                      <p className="text-xs text-gray-600">
                        Next run:{' '}
                        {job.next_run
                          ? new Date(job.next_run).toLocaleTimeString()
                          : 'Not scheduled'}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Manual Collection Triggers */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* MySQL Collector */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <Database className="text-blue-600" size={24} />
                <h3 className="text-lg font-semibold">MySQL Collector</h3>
              </div>
            </div>

            <div className="space-y-3 mb-4">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Total Collected:</span>
                <span className="font-semibold">
                  {collectorStatus?.mysql_total_collected || 0}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Last Run:</span>
                <span className="font-semibold">
                  {collectorStatus?.mysql_last_run
                    ? new Date(collectorStatus.mysql_last_run).toLocaleString()
                    : 'Never'}
                </span>
              </div>
            </div>

            <button
              onClick={() => handleAction('mysql-collect', triggerMySQLCollection)}
              disabled={actionLoading === 'mysql-collect'}
              className="w-full btn-primary flex items-center justify-center space-x-2"
            >
              <RefreshCw size={18} className={actionLoading === 'mysql-collect' ? 'animate-spin' : ''} />
              <span>
                {actionLoading === 'mysql-collect' ? 'Collecting...' : 'Trigger Collection'}
              </span>
            </button>
          </div>

          {/* PostgreSQL Collector */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <Database className="text-indigo-600" size={24} />
                <h3 className="text-lg font-semibold">PostgreSQL Collector</h3>
              </div>
            </div>

            <div className="space-y-3 mb-4">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Total Collected:</span>
                <span className="font-semibold">
                  {collectorStatus?.postgres_total_collected || 0}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Last Run:</span>
                <span className="font-semibold">
                  {collectorStatus?.postgres_last_run
                    ? new Date(collectorStatus.postgres_last_run).toLocaleString()
                    : 'Never'}
                </span>
              </div>
            </div>

            <button
              onClick={() => handleAction('pg-collect', () => triggerPostgreSQLCollection(500))}
              disabled={actionLoading === 'pg-collect'}
              className="w-full btn-primary flex items-center justify-center space-x-2"
            >
              <RefreshCw size={18} className={actionLoading === 'pg-collect' ? 'animate-spin' : ''} />
              <span>
                {actionLoading === 'pg-collect' ? 'Collecting...' : 'Trigger Collection'}
              </span>
            </button>
          </div>

          {/* Analyzer */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <Activity className="text-green-600" size={24} />
                <h3 className="text-lg font-semibold">Query Analyzer</h3>
              </div>
            </div>

            <div className="space-y-3 mb-4">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Total Analyzed:</span>
                <span className="font-semibold">
                  {collectorStatus?.total_analyzed || 0}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Last Run:</span>
                <span className="font-semibold">
                  {collectorStatus?.analyzer_last_run
                    ? new Date(collectorStatus.analyzer_last_run).toLocaleString()
                    : 'Never'}
                </span>
              </div>
            </div>

            <button
              onClick={() => handleAction('analyze', () => triggerAnalysis(50))}
              disabled={actionLoading === 'analyze'}
              className="w-full btn-primary flex items-center justify-center space-x-2"
            >
              <Activity size={18} className={actionLoading === 'analyze' ? 'animate-spin' : ''} />
              <span>{actionLoading === 'analyze' ? 'Analyzing...' : 'Trigger Analysis'}</span>
            </button>
          </div>
        </div>

        {/* Analyzer Status Details */}
        {analyzerStatus && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center">
              <Activity className="mr-2 text-primary-600" size={24} />
              Analyzer Status
            </h2>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-6">
              <div className="text-center">
                <p className="text-3xl font-bold text-yellow-600">
                  {analyzerStatus.queries.pending}
                </p>
                <p className="text-sm text-gray-600 mt-1">Pending Analysis</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-green-600">
                  {analyzerStatus.queries.analyzed}
                </p>
                <p className="text-sm text-gray-600 mt-1">Analyzed</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-red-600">
                  {analyzerStatus.queries.error}
                </p>
                <p className="text-sm text-gray-600 mt-1">Errors</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-gray-900">
                  {analyzerStatus.queries.total}
                </p>
                <p className="text-sm text-gray-600 mt-1">Total Queries</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-6 border-t border-gray-200">
              <div className="bg-red-50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-red-600">
                  {analyzerStatus.analyses.high_impact}
                </p>
                <p className="text-sm text-gray-700 mt-1">High Impact</p>
              </div>
              <div className="bg-orange-50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-orange-600">
                  {analyzerStatus.analyses.medium_impact}
                </p>
                <p className="text-sm text-gray-700 mt-1">Medium Impact</p>
              </div>
              <div className="bg-yellow-50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-yellow-600">
                  {analyzerStatus.analyses.low_impact}
                </p>
                <p className="text-sm text-gray-700 mt-1">Low Impact</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-gray-900">
                  {analyzerStatus.analyses.total}
                </p>
                <p className="text-sm text-gray-700 mt-1">Total Analyses</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Collectors;

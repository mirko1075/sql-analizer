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
  Trash2,
  StopCircle,
  Plus,
} from 'lucide-react';
import {
  getCollectorStatus,
  getAnalyzerStatus,
  triggerMySQLCollection,
  triggerPostgreSQLCollection,
  triggerAnalysis,
  startScheduler,
  stopScheduler,
  listCollectorAgents,
  registerCollectorAgent,
  startCollectorAgent,
  stopCollectorAgent,
  triggerCollectorAgentCollection,
  deleteCollectorAgent,
} from '../services/api';
import type { CollectorStatus, AnalyzerStatus, CollectorAgent } from '../types';

const Collectors: React.FC = () => {
  const [collectorStatus, setCollectorStatus] = useState<CollectorStatus | null>(null);
  const [analyzerStatus, setAnalyzerStatus] = useState<AnalyzerStatus | null>(null);
  const [collectors, setCollectors] = useState<CollectorAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [showRegisterForm, setShowRegisterForm] = useState(false);
  const [apiKeyDisplay, setApiKeyDisplay] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    type: 'mysql' as 'mysql' | 'postgres',
    team_id: 1,
    host: '',
    port: 3306,
    user: '',
    password: '',
    database: '',
    min_exec_time_ms: 1000,
    collection_interval_minutes: 5,
    auto_collect: true,
  });

  useEffect(() => {
    loadStatus();
    // Refresh every 10 seconds
    const interval = setInterval(loadStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadStatus = async () => {
    try {
      const [collectorData, analyzerData, agentsData] = await Promise.all([
        getCollectorStatus().catch(() => null),
        getAnalyzerStatus().catch(() => null),
        listCollectorAgents().catch(() => ({ collectors: [], total: 0 })),
      ]);

      setCollectorStatus(collectorData);
      setAnalyzerStatus(analyzerData);
      setCollectors(agentsData.collectors || []);
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
      // Wait a bit and reload status
      setTimeout(loadStatus, 1500);
    } catch (error) {
      console.error(`Failed to execute ${action}:`, error);
      alert(`Failed to execute ${action}. Check console for details.`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await registerCollectorAgent({
        name: formData.name,
        type: formData.type,
        team_id: formData.team_id,
        config: {
          host: formData.host,
          port: formData.port,
          user: formData.user,
          password: formData.password,
          database: formData.database || undefined,
          min_exec_time_ms: formData.min_exec_time_ms,
        },
        collection_interval_minutes: formData.collection_interval_minutes,
        auto_collect: formData.auto_collect,
      });
      setApiKeyDisplay(response.api_key);
      setShowRegisterForm(false);
      loadStatus();
    } catch (error) {
      console.error('Failed to register collector:', error);
      alert('Failed to register collector. Check console for details.');
    }
  };

  const getStatusBadge = (status: string, isOnline: boolean) => {
    if (!isOnline) return 'bg-gray-100 text-gray-700 border-gray-300';
    switch (status) {
      case 'online':
        return 'bg-green-100 text-green-700 border-green-300';
      case 'error':
        return 'bg-red-100 text-red-700 border-red-300';
      case 'stopped':
        return 'bg-yellow-100 text-yellow-700 border-yellow-300';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-300';
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  const formatUptime = (seconds?: number) => {
    if (!seconds) return 'N/A';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
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
                    ? new Date(collectorStatus.mysql_last_run).toLocaleTimeString()
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
                    ? new Date(collectorStatus.postgres_last_run).toLocaleTimeString()
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
                    ? new Date(collectorStatus.analyzer_last_run).toLocaleTimeString()
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

        {/* Collector Agents Section */}
        <div className="mt-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900 flex items-center">
              <Database className="mr-3 text-primary-600" size={28} />
              Collector Agents
            </h2>
            <button
              onClick={() => setShowRegisterForm(true)}
              className="btn-primary flex items-center space-x-2"
            >
              <Plus size={18} />
              <span>Register Agent</span>
            </button>
          </div>

          {/* Collector Agents Grid */}
          {collectors.length === 0 ? (
            <div className="bg-white rounded-lg shadow-md p-12 text-center">
              <Database className="mx-auto text-gray-400 mb-4" size={48} />
              <p className="text-gray-600 text-lg">No collector agents registered yet</p>
              <p className="text-gray-500 text-sm mt-2">
                Click "Register Agent" to add your first collector
              </p>
            </div>
          ) : (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {collectors.map((collector) => (
                <div
                  key={collector.id}
                  className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-lg transition-shadow"
                >
                  {/* Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <h3 className="font-bold text-lg text-gray-900 mb-1">{collector.name}</h3>
                      <p className="text-sm text-gray-600">
                        {collector.type.toUpperCase()} • {collector.config.host}:{collector.config.port}
                      </p>
                    </div>
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-semibold border ${getStatusBadge(
                        collector.status,
                        collector.is_online
                      )}`}
                    >
                      {collector.is_online ? '🟢' : '🔴'} {collector.status}
                    </span>
                  </div>

                  {/* Stats */}
                  <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
                    <div className="bg-blue-50 p-3 rounded">
                      <p className="text-gray-600 text-xs">Queries</p>
                      <p className="font-bold text-blue-700">
                        {collector.stats.queries_collected || 0}
                      </p>
                    </div>
                    <div className="bg-green-50 p-3 rounded">
                      <p className="text-gray-600 text-xs">Uptime</p>
                      <p className="font-bold text-green-700">
                        {formatUptime(collector.stats.uptime_seconds)}
                      </p>
                    </div>
                    <div className="bg-purple-50 p-3 rounded">
                      <p className="text-gray-600 text-xs">Interval</p>
                      <p className="font-bold text-purple-700">{collector.collection_interval_minutes}m</p>
                    </div>
                    <div className="bg-orange-50 p-3 rounded">
                      <p className="text-gray-600 text-xs">Errors</p>
                      <p className="font-bold text-orange-700">
                        {collector.stats.errors_count || 0}
                      </p>
                    </div>
                  </div>

                  {/* Last Activity */}
                  <div className="text-xs text-gray-500 mb-4 space-y-1">
                    <p>Last heartbeat: {formatDate(collector.last_heartbeat)}</p>
                    <p>Last collection: {formatDate(collector.last_collection)}</p>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    <button
                      onClick={() =>
                        handleAction(`start-${collector.id}`, () => startCollectorAgent(collector.id))
                      }
                      disabled={
                        actionLoading === `start-${collector.id}` ||
                        collector.status === 'online'
                      }
                      className="flex-1 px-3 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center"
                    >
                      <PlayCircle className="mr-1" size={16} />
                      Start
                    </button>
                    <button
                      onClick={() =>
                        handleAction(`stop-${collector.id}`, () => stopCollectorAgent(collector.id))
                      }
                      disabled={
                        actionLoading === `stop-${collector.id}` ||
                        collector.status === 'stopped'
                      }
                      className="flex-1 px-3 py-2 bg-yellow-600 text-white text-sm rounded-lg hover:bg-yellow-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center"
                    >
                      <StopCircle className="mr-1" size={16} />
                      Stop
                    </button>
                    <button
                      onClick={() =>
                        handleAction(`collect-${collector.id}`, () =>
                          triggerCollectorAgentCollection(collector.id)
                        )
                      }
                      disabled={actionLoading === `collect-${collector.id}`}
                      className="flex-1 px-3 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center"
                    >
                      <RefreshCw className="mr-1" size={16} />
                      Collect
                    </button>
                    <button
                      onClick={() => {
                        if (confirm(`Delete collector "${collector.name}"?`)) {
                          handleAction(`delete-${collector.id}`, () =>
                            deleteCollectorAgent(collector.id)
                          );
                        }
                      }}
                      disabled={actionLoading === `delete-${collector.id}`}
                      className="px-3 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Register Form Modal */}
        {showRegisterForm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-8 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
              <h2 className="text-2xl font-bold mb-6">Register New Collector Agent</h2>
              <form onSubmit={handleRegister} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Name *
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                      placeholder="My Prod DB Collector"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Type *</label>
                    <select
                      value={formData.type}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          type: e.target.value as 'mysql' | 'postgres',
                          port: e.target.value === 'mysql' ? 3306 : 5432,
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="mysql">MySQL</option>
                      <option value="postgres">PostgreSQL</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Host *</label>
                    <input
                      type="text"
                      required
                      value={formData.host}
                      onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                      placeholder="localhost"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Port *</label>
                    <input
                      type="number"
                      required
                      value={formData.port}
                      onChange={(e) =>
                        setFormData({ ...formData, port: parseInt(e.target.value) })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      User *
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.user}
                      onChange={(e) => setFormData({ ...formData, user: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Password *
                    </label>
                    <input
                      type="password"
                      required
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Database (optional)
                  </label>
                  <input
                    type="text"
                    value={formData.database}
                    onChange={(e) => setFormData({ ...formData, database: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    placeholder="Leave empty to collect from all databases"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Min Execution Time (ms)
                    </label>
                    <input
                      type="number"
                      value={formData.min_exec_time_ms}
                      onChange={(e) =>
                        setFormData({ ...formData, min_exec_time_ms: parseInt(e.target.value) })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Collection Interval (minutes)
                    </label>
                    <input
                      type="number"
                      value={formData.collection_interval_minutes}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          collection_interval_minutes: parseInt(e.target.value),
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                </div>

                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="auto_collect"
                    checked={formData.auto_collect}
                    onChange={(e) =>
                      setFormData({ ...formData, auto_collect: e.target.checked })
                    }
                    className="mr-2"
                  />
                  <label htmlFor="auto_collect" className="text-sm text-gray-700">
                    Enable automatic collection
                  </label>
                </div>

                <div className="flex justify-end space-x-3 mt-6">
                  <button
                    type="button"
                    onClick={() => setShowRegisterForm(false)}
                    className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button type="submit" className="btn-primary">
                    Register
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* API Key Display Modal */}
        {apiKeyDisplay && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-8 max-w-lg w-full mx-4">
              <h2 className="text-2xl font-bold mb-4 text-green-600">
                Collector Registered Successfully!
              </h2>
              <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 mb-4">
                <p className="font-bold text-yellow-800">⚠️ Important - Save this API Key!</p>
                <p className="text-sm text-yellow-700 mt-1">
                  This is the only time you'll see this API key. Save it securely.
                </p>
              </div>
              <div className="bg-gray-100 p-4 rounded-lg mb-4">
                <p className="text-sm text-gray-600 mb-2">API Key:</p>
                <p className="font-mono text-sm break-all bg-white p-3 rounded border border-gray-300">
                  {apiKeyDisplay}
                </p>
              </div>
              <button
                onClick={() => setApiKeyDisplay(null)}
                className="w-full btn-primary"
              >
                I've Saved the API Key
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Collectors;

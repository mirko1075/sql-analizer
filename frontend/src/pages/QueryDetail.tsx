/**
 * Query Detail Page - Detailed view of a single slow query
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Database,
  AlertCircle,
  Lightbulb,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import { getSlowQueryDetail, analyzeSpecificQuery } from '../services/api';
import type { SlowQueryDetail } from '../types';

const QueryDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [query, setQuery] = useState<SlowQueryDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    if (id) {
      loadQueryDetail(id);
    }
  }, [id]);

  const loadQueryDetail = async (queryId: string) => {
    try {
      setLoading(true);
      const data = await getSlowQueryDetail(queryId);
      setQuery(data);
    } catch (error) {
      console.error('Failed to load query detail:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!id) return;
    try {
      setAnalyzing(true);
      await analyzeSpecificQuery(id);
      // Reload after analysis
      setTimeout(() => loadQueryDetail(id), 2000);
    } catch (error) {
      console.error('Failed to trigger analysis:', error);
    } finally {
      setAnalyzing(false);
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

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'CRITICAL':
      case 'HIGH':
        return <AlertCircle className="text-red-600" size={20} />;
      case 'MEDIUM':
        return <AlertCircle className="text-yellow-600" size={20} />;
      case 'LOW':
        return <CheckCircle className="text-green-600" size={20} />;
      default:
        return <Lightbulb className="text-gray-600" size={20} />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          <p className="mt-4 text-gray-600">Loading query details...</p>
        </div>
      </div>
    );
  }

  if (!query) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="bg-white rounded-lg shadow-md p-12 text-center">
            <XCircle className="mx-auto text-red-400 mb-4" size={48} />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Query not found</h3>
            <p className="text-gray-600 mb-4">The requested query could not be loaded.</p>
            <button onClick={() => navigate('/queries')} className="btn-primary">
              Back to Queries
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => navigate('/queries')}
            className="flex items-center text-gray-600 hover:text-primary-600 mb-4"
          >
            <ArrowLeft size={20} className="mr-2" />
            Back to Queries
          </button>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            <Database className="mr-3 text-primary-600" size={28} />
            Query Details
          </h1>
        </div>

        {/* Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow-md p-4">
            <p className="text-sm text-gray-600">Duration</p>
            <p className="text-2xl font-bold text-gray-900">{parseFloat(String(query.duration_ms)).toFixed(2)}ms</p>
          </div>
          <div className="bg-white rounded-lg shadow-md p-4">
            <p className="text-sm text-gray-600">Rows Examined</p>
            <p className="text-2xl font-bold text-orange-600">
              {query.rows_examined?.toLocaleString() || 'N/A'}
            </p>
          </div>
          <div className="bg-white rounded-lg shadow-md p-4">
            <p className="text-sm text-gray-600">Rows Returned</p>
            <p className="text-2xl font-bold text-green-600">
              {query.rows_returned?.toLocaleString() || 'N/A'}
            </p>
          </div>
          <div className="bg-white rounded-lg shadow-md p-4">
            <p className="text-sm text-gray-600">Database</p>
            <p className="text-2xl font-bold text-primary-600">{query.source_db_type.toUpperCase()}</p>
          </div>
        </div>

        {/* SQL Query */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">SQL Query</h2>
          <div className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto">
            <pre className="text-sm font-mono whitespace-pre-wrap">{query.full_sql}</pre>
          </div>
          <div className="mt-4 flex items-center justify-between">
            <div className="text-sm text-gray-600">
              <span className="font-medium">Fingerprint:</span>
              <code className="ml-2 bg-gray-100 px-2 py-1 rounded">{query.sql_hash}</code>
            </div>
            <div className="text-sm text-gray-600">
              Captured: {new Date(query.captured_at).toLocaleString()}
            </div>
          </div>
        </div>

        {/* Analysis Results */}
        {query.analysis ? (
          <div className="space-y-6">
            {/* Problem & Root Cause */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-start justify-between mb-4">
                <h2 className="text-xl font-semibold">Analysis Results</h2>
                <span
                  className={`badge ${getImprovementLevelColor(
                    query.analysis.improvement_level
                  )}`}
                >
                  {query.analysis.improvement_level} Impact
                </span>
              </div>

              <div className="space-y-4">
                <div>
                  <h3 className="font-medium text-gray-900 mb-2 flex items-center">
                    <AlertCircle className="mr-2 text-orange-600" size={20} />
                    Problem
                  </h3>
                  <p className="text-gray-700 bg-orange-50 p-3 rounded-lg">
                    {query.analysis.problem}
                  </p>
                </div>

                <div>
                  <h3 className="font-medium text-gray-900 mb-2">Root Cause</h3>
                  <p className="text-gray-700 bg-gray-50 p-3 rounded-lg">
                    {query.analysis.root_cause}
                  </p>
                </div>

                <div className="pt-4 border-t border-gray-200">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">
                      Estimated Speedup: <strong>{query.analysis.estimated_speedup}</strong>
                    </span>
                    <span className="text-gray-600">
                      Confidence: <strong>{(parseFloat(String(query.analysis.confidence_score)) * 100).toFixed(0)}%</strong>
                    </span>
                    <span className="text-gray-600">
                      Method: <strong>{query.analysis.analysis_method}</strong>
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Suggestions */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4 flex items-center">
                <Lightbulb className="mr-2 text-yellow-600" size={24} />
                Optimization Suggestions
              </h2>

              <div className="space-y-4">
                {query.analysis.suggestions.map((suggestion, index) => (
                  <div
                    key={index}
                    className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 transition-colors"
                  >
                    <div className="flex items-start space-x-3">
                      {getPriorityIcon(suggestion.priority)}
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium text-gray-900">{suggestion.type}</span>
                          <span className={`badge ${getImprovementLevelColor(suggestion.priority)}`}>
                            {suggestion.priority}
                          </span>
                        </div>
                        <p className="text-gray-700 mb-2">{suggestion.description}</p>
                        {suggestion.sql && (
                          <div className="bg-gray-900 text-gray-100 p-3 rounded mt-2">
                            <pre className="text-xs font-mono">{suggestion.sql}</pre>
                          </div>
                        )}
                        {suggestion.estimated_impact && (
                          <p className="text-sm text-green-600 mt-2">
                            💡 {suggestion.estimated_impact}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* No Analysis Yet */
          <div className="bg-white rounded-lg shadow-md p-8 text-center">
            <AlertCircle className="mx-auto text-yellow-400 mb-4" size={48} />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Analysis Available</h3>
            <p className="text-gray-600 mb-4">
              This query hasn't been analyzed yet. Trigger an analysis to get optimization suggestions.
            </p>
            <button
              onClick={handleAnalyze}
              disabled={analyzing}
              className="btn-primary"
            >
              {analyzing ? 'Analyzing...' : 'Analyze Now'}
            </button>
          </div>
        )}

        {/* EXPLAIN Plan */}
        {query.plan_json && (
          <div className="bg-white rounded-lg shadow-md p-6 mt-6">
            <h2 className="text-xl font-semibold mb-4">EXPLAIN Plan</h2>
            <div className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto">
              <pre className="text-xs font-mono">
                {JSON.stringify(query.plan_json, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default QueryDetail;

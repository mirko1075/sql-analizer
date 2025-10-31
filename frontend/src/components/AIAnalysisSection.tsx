import React from 'react';
import { Sparkles, RefreshCw, BrainCircuit } from 'lucide-react';
import type { AIAnalysisResult } from '../types';

interface AIAnalysisSectionProps {
  analysis?: AIAnalysisResult | null;
  loading?: boolean;
  onAnalyze: (force?: boolean) => Promise<void> | void;
}

const getImprovementBadge = (level?: string | null): string => {
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

const formatConfidence = (value?: number | string | null): string | null => {
  if (value === null || value === undefined) return null;
  const numeric = typeof value === 'string' ? parseFloat(value) : value;
  if (Number.isNaN(numeric)) return null;
  return `${Math.round(numeric * 100)}%`;
};

const AIAnalysisSection: React.FC<AIAnalysisSectionProps> = ({
  analysis,
  loading = false,
  onAnalyze,
}) => {
  const confidence = formatConfidence(analysis?.confidence_score);

  const handleAnalyzeClick = () => {
    onAnalyze(!!analysis);
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="rounded-full bg-primary-100 p-2">
            <Sparkles className="text-primary-600" size={20} />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-gray-900 flex items-center space-x-2">
              <span>AI Analysis</span>
              {analysis?.improvement_level && (
                <span className={`badge ${getImprovementBadge(analysis.improvement_level)}`}>
                  {analysis.improvement_level} Impact
                </span>
              )}
            </h2>
            <p className="text-sm text-gray-600">
              On-demand recommendations generated with {analysis?.provider?.toUpperCase() || 'OpenAI'}.
            </p>
          </div>
        </div>
        <button
          onClick={handleAnalyzeClick}
          disabled={loading}
          className="btn-primary flex items-center space-x-2 self-start md:self-auto"
        >
          <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
          <span>{analysis ? (loading ? 'Re-running AI Analysis...' : 'Re-run AI Analysis') : loading ? 'Analyzing with AI...' : 'Analyze with AI'}</span>
        </button>
      </div>

      {analysis ? (
        <div className="space-y-4">
          <div className="bg-primary-50 border border-primary-100 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <BrainCircuit className="text-primary-600 mt-1" size={20} />
              <div>
                <p className="text-sm text-gray-500">
                  Model: <span className="font-medium text-gray-900">{analysis.model}</span>{' '}
                  • Confidence: <span className="font-medium text-gray-900">{confidence ?? 'N/A'}</span>{' '}
                  • Speedup: <span className="font-medium text-gray-900">{analysis.estimated_speedup || 'N/A'}</span>
                </p>
                <p className="text-sm text-gray-500">
                  Last run:{' '}
                  <span className="font-medium text-gray-900">
                    {new Date(analysis.analyzed_at).toLocaleString()}
                  </span>
                </p>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Summary</h3>
            <p className="text-gray-700 bg-gray-50 p-4 rounded-lg">{analysis.summary}</p>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Root Cause</h3>
            <p className="text-gray-700 bg-gray-50 p-4 rounded-lg">{analysis.root_cause}</p>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">AI Recommendations</h3>
            {analysis.recommendations && analysis.recommendations.length > 0 ? (
              <div className="space-y-3">
                {analysis.recommendations.map((rec, index) => (
                  <div key={index} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
                        {rec.type || 'Recommendation'}
                      </span>
                      {rec.priority && (
                        <span className={`badge ${getImprovementBadge(rec.priority)}`}>
                          {rec.priority}
                        </span>
                      )}
                    </div>
                    <p className="text-gray-700 mb-2">{rec.description || 'No description provided.'}</p>
                    {rec.sql && (
                      <div className="bg-gray-900 text-gray-100 p-3 rounded font-mono text-xs overflow-x-auto">
                        <pre>{rec.sql}</pre>
                      </div>
                    )}
                    {rec.estimated_impact && (
                      <p className="text-sm text-green-600 mt-2">Impact: {rec.estimated_impact}</p>
                    )}
                    {rec.rationale && (
                      <p className="text-xs text-gray-500 mt-2">Rationale: {rec.rationale}</p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 bg-gray-50 border border-dashed border-gray-200 rounded-lg p-4">
                No explicit recommendations were generated for this run.
              </p>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-gray-50 border border-dashed border-gray-200 rounded-lg p-6 text-center">
          <p className="text-gray-700 font-medium mb-1">No AI analysis available yet.</p>
          <p className="text-sm text-gray-500">
            Run an AI analysis to augment the heuristic findings with model-driven suggestions tailored to your database schema.
          </p>
        </div>
      )}
    </div>
  );
};

export default AIAnalysisSection;

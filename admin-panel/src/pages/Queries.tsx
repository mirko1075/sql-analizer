import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queriesAPI } from '../services/api';
import { SlowQuery } from '../types';
import { Database, Clock, Zap, AlertCircle, CheckCircle, Loader } from 'lucide-react';

export default function Queries() {
  const queryClient = useQueryClient();
  const [selectedQuery, setSelectedQuery] = useState<SlowQuery | null>(null);
  const [filter, setFilter] = useState<'all' | 'analyzed' | 'unanalyzed'>('all');

  const { data: queries = [], isLoading } = useQuery({
    queryKey: ['queries', filter],
    queryFn: async () => {
      const response = await queriesAPI.list();
      const allQueries = response.data;

      if (filter === 'analyzed') {
        return allQueries.filter((q: SlowQuery) => q.analysis_result);
      } else if (filter === 'unanalyzed') {
        return allQueries.filter((q: SlowQuery) => !q.analysis_result);
      }
      return allQueries;
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: (queryId: number) => queriesAPI.analyze(queryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queries'] });
      alert('Analysis completed successfully!');
    },
    onError: (error: any) => {
      alert(`Analysis failed: ${error.response?.data?.detail || error.message}`);
    },
  });

  const handleAnalyze = (queryId: number) => {
    if (confirm('Do you want to analyze this query using AI?')) {
      analyzeMutation.mutate(queryId);
    }
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const getSeverityColor = (severity?: string) => {
    switch (severity) {
      case 'critical': return '#ef4444';
      case 'high': return '#f97316';
      case 'medium': return '#eab308';
      case 'low': return '#22c55e';
      default: return '#6b7280';
    }
  };

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
        <Loader size={48} style={{ animation: 'spin 1s linear infinite' }} />
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 'bold', color: '#1f2937' }}>Slow Queries</h1>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setFilter('all')}
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              backgroundColor: filter === 'all' ? '#3b82f6' : '#f3f4f6',
              color: filter === 'all' ? 'white' : '#374151',
              fontWeight: '500',
            }}
          >
            All
          </button>
          <button
            onClick={() => setFilter('analyzed')}
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              backgroundColor: filter === 'analyzed' ? '#3b82f6' : '#f3f4f6',
              color: filter === 'analyzed' ? 'white' : '#374151',
              fontWeight: '500',
            }}
          >
            Analyzed
          </button>
          <button
            onClick={() => setFilter('unanalyzed')}
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              backgroundColor: filter === 'unanalyzed' ? '#3b82f6' : '#f3f4f6',
              color: filter === 'unanalyzed' ? 'white' : '#374151',
              fontWeight: '500',
            }}
          >
            Unanalyzed
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selectedQuery ? '1fr 1fr' : '1fr', gap: '24px' }}>
        {/* Queries List */}
        <div style={{ backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ backgroundColor: '#f9fafb', borderBottom: '1px solid #e5e7eb' }}>
                  <th style={{ padding: '12px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6b7280', textTransform: 'uppercase' }}>
                    Query
                  </th>
                  <th style={{ padding: '12px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6b7280', textTransform: 'uppercase' }}>
                    Duration
                  </th>
                  <th style={{ padding: '12px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6b7280', textTransform: 'uppercase' }}>
                    DB Type
                  </th>
                  <th style={{ padding: '12px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6b7280', textTransform: 'uppercase' }}>
                    Status
                  </th>
                  <th style={{ padding: '12px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6b7280', textTransform: 'uppercase' }}>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {queries.map((query: SlowQuery) => (
                  <tr
                    key={query.id}
                    style={{
                      borderBottom: '1px solid #e5e7eb',
                      backgroundColor: selectedQuery?.id === query.id ? '#eff6ff' : 'white',
                      cursor: 'pointer',
                    }}
                    onClick={() => setSelectedQuery(query)}
                  >
                    <td style={{ padding: '12px', maxWidth: '300px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Database size={16} color="#6b7280" />
                        <span style={{ fontSize: '14px', color: '#374151', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {query.original_query?.substring(0, 50) || 'N/A'}...
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Clock size={14} color="#6b7280" />
                        <span style={{ fontSize: '14px', color: '#374151', fontWeight: '500' }}>
                          {formatDuration(query.execution_time_ms)}
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span style={{
                        fontSize: '12px',
                        fontWeight: '500',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        backgroundColor: '#dbeafe',
                        color: '#1e40af',
                      }}>
                        {query.database_type}
                      </span>
                    </td>
                    <td style={{ padding: '12px' }}>
                      {query.analysis_result ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <CheckCircle size={16} color="#22c55e" />
                          <span style={{ fontSize: '12px', color: '#22c55e', fontWeight: '500' }}>Analyzed</span>
                        </div>
                      ) : (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <AlertCircle size={16} color="#f59e0b" />
                          <span style={{ fontSize: '12px', color: '#f59e0b', fontWeight: '500' }}>Pending</span>
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '12px' }}>
                      {!query.analysis_result && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleAnalyze(query.id);
                          }}
                          disabled={analyzeMutation.isPending}
                          style={{
                            padding: '6px 12px',
                            borderRadius: '6px',
                            border: 'none',
                            cursor: analyzeMutation.isPending ? 'not-allowed' : 'pointer',
                            backgroundColor: analyzeMutation.isPending ? '#9ca3af' : '#3b82f6',
                            color: 'white',
                            fontSize: '12px',
                            fontWeight: '500',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <Zap size={14} />
                          {analyzeMutation.isPending ? 'Analyzing...' : 'Analyze'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {queries.length === 0 && (
            <div style={{ padding: '48px', textAlign: 'center', color: '#6b7280' }}>
              <Database size={48} style={{ margin: '0 auto 16px', opacity: 0.3 }} />
              <p style={{ fontSize: '16px', fontWeight: '500' }}>No queries found</p>
              <p style={{ fontSize: '14px', marginTop: '8px' }}>Queries will appear here when captured by client agents.</p>
            </div>
          )}
        </div>

        {/* Query Detail Panel */}
        {selectedQuery && (
          <div style={{ backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <h2 style={{ fontSize: '18px', fontWeight: 'bold', color: '#1f2937' }}>Query Details</h2>
              <button
                onClick={() => setSelectedQuery(null)}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: '1px solid #e5e7eb',
                  backgroundColor: 'white',
                  cursor: 'pointer',
                  fontSize: '14px',
                  color: '#6b7280',
                }}
              >
                Close
              </button>
            </div>

            {/* Original Query */}
            <div style={{ marginBottom: '20px' }}>
              <h3 style={{ fontSize: '14px', fontWeight: '600', color: '#374151', marginBottom: '8px' }}>Original Query</h3>
              <pre style={{
                backgroundColor: '#f9fafb',
                padding: '12px',
                borderRadius: '6px',
                fontSize: '12px',
                color: '#1f2937',
                overflow: 'auto',
                maxHeight: '200px',
              }}>
                {selectedQuery.original_query || 'N/A'}
              </pre>
            </div>

            {/* Anonymized Query */}
            {selectedQuery.anonymized_query && (
              <div style={{ marginBottom: '20px' }}>
                <h3 style={{ fontSize: '14px', fontWeight: '600', color: '#374151', marginBottom: '8px' }}>Anonymized Query</h3>
                <pre style={{
                  backgroundColor: '#f9fafb',
                  padding: '12px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  color: '#1f2937',
                  overflow: 'auto',
                  maxHeight: '200px',
                }}>
                  {selectedQuery.anonymized_query}
                </pre>
              </div>
            )}

            {/* Metadata */}
            <div style={{ marginBottom: '20px' }}>
              <h3 style={{ fontSize: '14px', fontWeight: '600', color: '#374151', marginBottom: '12px' }}>Metadata</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Execution Time</p>
                  <p style={{ fontSize: '14px', color: '#1f2937', fontWeight: '500' }}>{formatDuration(selectedQuery.execution_time_ms)}</p>
                </div>
                <div>
                  <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Database Type</p>
                  <p style={{ fontSize: '14px', color: '#1f2937', fontWeight: '500' }}>{selectedQuery.database_type}</p>
                </div>
                <div>
                  <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Timestamp</p>
                  <p style={{ fontSize: '14px', color: '#1f2937', fontWeight: '500' }}>
                    {new Date(selectedQuery.created_at).toLocaleString()}
                  </p>
                </div>
                <div>
                  <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Organization ID</p>
                  <p style={{ fontSize: '14px', color: '#1f2937', fontWeight: '500' }}>{selectedQuery.organization_id}</p>
                </div>
              </div>
            </div>

            {/* Analysis Result */}
            {selectedQuery.analysis_result && (
              <div>
                <h3 style={{ fontSize: '14px', fontWeight: '600', color: '#374151', marginBottom: '12px' }}>AI Analysis</h3>

                {/* Severity */}
                <div style={{ marginBottom: '16px' }}>
                  <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '6px' }}>Severity</p>
                  <span style={{
                    display: 'inline-block',
                    fontSize: '14px',
                    fontWeight: '600',
                    padding: '6px 12px',
                    borderRadius: '6px',
                    backgroundColor: `${getSeverityColor(selectedQuery.analysis_result.severity)}20`,
                    color: getSeverityColor(selectedQuery.analysis_result.severity),
                    textTransform: 'uppercase',
                  }}>
                    {selectedQuery.analysis_result.severity}
                  </span>
                </div>

                {/* Summary */}
                <div style={{ marginBottom: '16px' }}>
                  <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '6px' }}>Summary</p>
                  <p style={{ fontSize: '14px', color: '#1f2937', lineHeight: '1.6' }}>
                    {selectedQuery.analysis_result.summary}
                  </p>
                </div>

                {/* Issues */}
                {selectedQuery.analysis_result.issues && selectedQuery.analysis_result.issues.length > 0 && (
                  <div style={{ marginBottom: '16px' }}>
                    <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px' }}>Issues Found</p>
                    <ul style={{ paddingLeft: '20px', margin: 0 }}>
                      {selectedQuery.analysis_result.issues.map((issue: string, idx: number) => (
                        <li key={idx} style={{ fontSize: '14px', color: '#1f2937', marginBottom: '6px' }}>
                          {issue}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Recommendations */}
                {selectedQuery.analysis_result.recommendations && selectedQuery.analysis_result.recommendations.length > 0 && (
                  <div>
                    <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px' }}>Recommendations</p>
                    <ul style={{ paddingLeft: '20px', margin: 0 }}>
                      {selectedQuery.analysis_result.recommendations.map((rec: string, idx: number) => (
                        <li key={idx} style={{ fontSize: '14px', color: '#22c55e', marginBottom: '6px', fontWeight: '500' }}>
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

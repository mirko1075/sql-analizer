import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  getSlowQuery, 
  getAIAnalysis, 
  updateQueryStatus, 
  analyzeWithAI,
  type SlowQuery, 
  type AnalysisResult 
} from '../services/api';
import StatusBadge from '../components/StatusBadge';

export default function QueryDetail() {
  const { id } = useParams<{ id: string }>();
  const queryId = parseInt(id || '0');

  const [query, setQuery] = useState<SlowQuery | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzingAI, setAnalyzingAI] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadQuery();
  }, [queryId]);

  const loadQuery = async () => {
    try {
      setLoading(true);
      setError(null);

      const queryRes = await getSlowQuery(queryId);
      setQuery(queryRes.data);

      // If already analyzed, load analysis
      if (queryRes.data.analyzed) {
        try {
          const analysisRes = await getAIAnalysis(queryId);
          setAnalysis(analysisRes.data);
        } catch (err) {
          console.error('Failed to load analysis:', err);
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load query');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    setAnalyzingAI(true);
    setError(null);
    try {
      console.log(`🤖 Starting AI analysis for query ${queryId}...`);
      await analyzeWithAI(queryId);
      await loadQuery(); // Reload to get analysis results
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'AI analysis failed');
    } finally {
      setAnalyzingAI(false);
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    try {
      await updateQueryStatus(queryId, newStatus);
      await loadQuery(); // Reload to update status
    } catch (err: any) {
      alert('Status update failed: ' + (err.response?.data?.detail || err.message));
    }
  };

  const formatTime = (seconds: number) => {
    if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
    return `${seconds.toFixed(2)}s`;
  };

  if (loading) {
    return (
      <div className="container">
        <div className="loading">Loading query details...</div>
      </div>
    );
  }

  if (error || !query) {
    return (
      <div className="container">
        <div className="error">{error || 'Query not found'}</div>
        <Link to="/">← Back to Dashboard</Link>
      </div>
    );
  }

  return (
    <div className="container">
      <header>
        <Link to="/" style={{ textDecoration: 'none', color: '#3498db' }}>← Back to Dashboard</Link>
        <h1>Query #{query.id}</h1>
      </header>

      {error && <div className="error">{error}</div>}

      {/* Query Information */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2>📊 Query Information</h2>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <StatusBadge status={query.status} />
            <select
              value={query.status}
              onChange={(e) => handleStatusChange(e.target.value)}
              style={{
                padding: '6px 10px',
                borderRadius: '4px',
                border: '1px solid #ddd',
                backgroundColor: 'white',
                cursor: 'pointer',
                fontSize: '13px'
              }}
            >
              <option value="pending">⏳ Pending</option>
              <option value="analyzed">🔍 Analyzed</option>
              <option value="archived">📦 Archived</option>
              <option value="resolved">✅ Resolved</option>
            </select>
          </div>
        </div>
        <table>
          <tbody>
            <tr>
              <th>Database</th>
              <td>{query.database_name}</td>
            </tr>
            <tr>
              <th>Query Time</th>
              <td>{formatTime(query.query_time)}</td>
            </tr>
            <tr>
              <th>Rows Examined</th>
              <td>{query.rows_examined.toLocaleString()}</td>
            </tr>
            <tr>
              <th>Rows Sent</th>
              <td>{query.rows_sent.toLocaleString()}</td>
            </tr>
            <tr>
              <th>Lock Time</th>
              <td>{formatTime(query.lock_time || 0)}</td>
            </tr>
            <tr>
              <th>Detected At</th>
              <td>{new Date(query.detected_at).toLocaleString()}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* SQL Query */}
      <div className="card">
        <h2>📝 SQL Query</h2>
        <pre>{query.sql_text}</pre>
      </div>

      {/* Analysis Section */}
      {!query.analyzed ? (
        <div className="card">
          <h2>🧠 AI Analysis</h2>
          <p>This query has not been analyzed with AI yet.</p>
          <p style={{ marginTop: '12px', fontSize: '0.9em', color: '#7f8c8d' }}>
            Click the button below to start an interactive AI analysis. 
            The AI will examine the query and may request additional data from the database to provide comprehensive optimization recommendations.
          </p>
          <button 
            onClick={handleAnalyze} 
            disabled={analyzingAI} 
            style={{ 
              marginTop: '16px',
              padding: '12px 24px',
              fontSize: '16px',
              backgroundColor: analyzingAI ? '#95a5a6' : '#3498db',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: analyzingAI ? 'not-allowed' : 'pointer'
            }}
          >
            {analyzingAI ? '⏳ Analyzing with AI... (This may take 30-60 seconds)' : '🤖 Analyze with AI'}
          </button>
          {analyzingAI && (
            <div style={{ marginTop: '16px', padding: '12px', background: '#f0f8ff', borderRadius: '6px', fontSize: '0.9em' }}>
              <div>🔄 Running enhanced rule-based analysis (20+ rules)...</div>
              <div>🤖 AI is analyzing the query and may request additional database information...</div>
              <div>💡 The AI can execute SELECT queries to gather statistics and schema details...</div>
            </div>
          )}
        </div>
      ) : analysis ? (
        <>
          {/* Issues Found */}
          <div className="card">
            <h2>⚠️ Issues Found</h2>
            {analysis.issues?.length === 0 ? (
              <p>No major issues detected. This query looks good!</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {analysis.issues.map((issue, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '12px',
                      border: '1px solid #e0e0e0',
                      borderRadius: '6px',
                      borderLeft: `4px solid ${
                        issue.severity === 'CRITICAL' ? '#e74c3c' :
                        issue.severity === 'HIGH' ? '#e67e22' :
                        issue.severity === 'MEDIUM' ? '#f39c12' : '#3498db'
                      }`
                    }}
                  >
                    <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                      <span className={`badge ${issue.severity.toLowerCase()}`}>
                        {issue.severity}
                      </span>
                      {' '}{issue.type}
                    </div>
                    <div>{issue.message}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Suggested Indexes */}
          {analysis.suggested_indexes?.length > 0 && (
            <div className="card">
              <h2>💡 Suggested Indexes</h2>
              {analysis.suggested_indexes.map((index, idx) => (
                <div key={idx} style={{ marginBottom: '16px' }}>
                  <div style={{ marginBottom: '4px' }}>
                    <strong>Table:</strong> <code>{index.table}</code> | 
                    <strong> Column:</strong> <code>{index.column}</code>
                  </div>
                  <pre>{index.statement}</pre>
                </div>
              ))}
            </div>
          )}

          {/* AI Analysis */}
          <div className="card">
            <h2>🧠 AI Analysis (LLaMA {analysis.analyzed_at && `- ${new Date(analysis.analyzed_at).toLocaleString()})`}</h2>
            <div style={{ 
              whiteSpace: 'pre-wrap',
              lineHeight: '1.6',
              padding: '16px',
              background: '#f8f9fa',
              borderRadius: '6px'
            }}>
              {analysis.ai_analysis}
            </div>
            <div style={{ marginTop: '16px', color: '#7f8c8d', fontSize: '0.9em' }}>
              Analysis completed in {analysis.analysis_duration?.toFixed(2)}s
            </div>
          </div>
        </>
      ) : (
        <div className="card">
          <h2>🧠 Analysis</h2>
          <div className="loading">Loading analysis results...</div>
        </div>
      )}
    </div>
  );
}

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getSlowQueries, getStats, triggerCollection, archiveQuery, resolveQuery, type SlowQuery, type Stats } from '../services/api';
import StatusBadge from '../components/StatusBadge';

export default function Dashboard() {
  const [queries, setQueries] = useState<SlowQuery[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [collecting, setCollecting] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const pageSize = 50;

  useEffect(() => {
    loadData();
  }, [page, statusFilter]); // Reload when status filter changes

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [queriesRes, statsRes] = await Promise.all([
        getSlowQueries(page * pageSize, pageSize, undefined, statusFilter || undefined),
        getStats()
      ]);

      setQueries(queriesRes.data.queries);
      setHasMore(queriesRes.data.has_more);
      setStats(statsRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleCollect = async () => {
    setCollecting(true);
    try {
      await triggerCollection();
      await loadData(); // Reload data after collection
    } catch (err: any) {
      alert('Collection failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setCollecting(false);
    }
  };

  const handleStatusChange = async (queryId: number, newStatus: 'archived' | 'resolved') => {
    try {
      if (newStatus === 'archived') {
        await archiveQuery(queryId);
      } else {
        await resolveQuery(queryId);
      }
      await loadData(); // Reload to update the list
    } catch (err: any) {
      alert('Status update failed: ' + (err.response?.data?.detail || err.message));
    }
  };

  const formatTime = (seconds: number) => {
    if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
    return `${seconds.toFixed(2)}s`;
  };

  const getPriorityBadge = (queryTime: number) => {
    if (queryTime > 5) return 'critical';
    if (queryTime > 2) return 'high';
    if (queryTime > 1) return 'medium';
    return 'low';
  };

  return (
    <div className="container">
      <header>
        <h1>🧠 DBPower Base - LLaMA Edition</h1>
        <p>AI-Powered MySQL Query Analyzer</p>
      </header>

      {error && <div className="error">Error: {error}</div>}

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">Total Queries</div>
            <div className="stat-value">{stats.total_queries}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Analyzed</div>
            <div className="stat-value" style={{ color: '#27ae60' }}>
              {stats.analyzed_queries}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Pending</div>
            <div className="stat-value" style={{ color: '#e67e22' }}>
              {stats.pending_queries}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Avg Query Time</div>
            <div className="stat-value">{formatTime(stats.average_query_time)}</div>
          </div>
        </div>
      )}

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '10px' }}>
          <h2>Slow Queries</h2>
          
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <select 
              value={statusFilter} 
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(0); // Reset to first page when filter changes
              }}
              style={{
                padding: '8px 12px',
                borderRadius: '4px',
                border: '1px solid #ddd',
                backgroundColor: 'white',
                cursor: 'pointer',
                fontSize: '14px'
              }}
            >
              <option value="">All Statuses</option>
              <option value="pending">⏳ Pending</option>
              <option value="analyzed">🔍 Analyzed</option>
              <option value="archived">📦 Archived</option>
              <option value="resolved">✅ Resolved</option>
            </select>
            
            <button onClick={handleCollect} disabled={collecting}>
              {collecting ? '🔄 Collecting...' : '🔄 Collect Now'}
            </button>
          </div>
        </div>

        {loading ? (
          <div className="loading">Loading queries...</div>
        ) : queries.length === 0 ? (
          <div className="loading">No slow queries found. Run the simulator to generate test data.</div>
        ) : (
          <>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>SQL Query</th>
                  <th>Query Time</th>
                  <th>Rows Examined</th>
                  <th>Database</th>
                  <th>Status</th>
                  <th>Priority</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {queries.map((query) => (
                  <tr key={query.id}>
                    <td>{query.id}</td>
                    <td 
                      onClick={() => window.location.href = `/query/${query.id}`}
                      style={{ cursor: 'pointer' }}
                    >
                      <code style={{ display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '400px' }}>
                        {query.sql_text}
                      </code>
                    </td>
                    <td>{formatTime(query.query_time)}</td>
                    <td>{query.rows_examined.toLocaleString()}</td>
                    <td>{query.database_name}</td>
                    <td>
                      <StatusBadge status={query.status} size="small" />
                    </td>
                    <td>
                      <span className={`badge ${getPriorityBadge(query.query_time)}`}>
                        {getPriorityBadge(query.query_time).toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '5px' }}>
                        {query.status !== 'archived' && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleStatusChange(query.id, 'archived');
                            }}
                            style={{
                              padding: '4px 8px',
                              fontSize: '11px',
                              backgroundColor: '#95a5a6',
                              color: 'white',
                              border: 'none',
                              borderRadius: '3px',
                              cursor: 'pointer'
                            }}
                            title="Archive query"
                          >
                            📦
                          </button>
                        )}
                        {query.status !== 'resolved' && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleStatusChange(query.id, 'resolved');
                            }}
                            style={{
                              padding: '4px 8px',
                              fontSize: '11px',
                              backgroundColor: '#27ae60',
                              color: 'white',
                              border: 'none',
                              borderRadius: '3px',
                              cursor: 'pointer'
                            }}
                            title="Mark as resolved"
                          >
                            ✅
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="pagination">
              <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}>
                ← Previous
              </button>
              <span>Page {page + 1}</span>
              <button onClick={() => setPage(p => p + 1)} disabled={!hasMore}>
                Next →
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

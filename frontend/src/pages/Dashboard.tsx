import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getSlowQueries, getStats, triggerCollection, type SlowQuery, type Stats } from '../services/api';

export default function Dashboard() {
  const [queries, setQueries] = useState<SlowQuery[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [collecting, setCollecting] = useState(false);

  const pageSize = 50;

  useEffect(() => {
    loadData();
  }, [page]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [queriesRes, statsRes] = await Promise.all([
        getSlowQueries(page * pageSize, pageSize),
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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2>Slow Queries</h2>
          <button onClick={handleCollect} disabled={collecting}>
            {collecting ? '🔄 Collecting...' : '🔄 Collect Now'}
          </button>
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
                </tr>
              </thead>
              <tbody>
                {queries.map((query) => (
                  <tr key={query.id} onClick={() => window.location.href = `/query/${query.id}`}>
                    <td>{query.id}</td>
                    <td>
                      <code style={{ display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '500px' }}>
                        {query.sql_text}
                      </code>
                    </td>
                    <td>{formatTime(query.query_time)}</td>
                    <td>{query.rows_examined.toLocaleString()}</td>
                    <td>{query.database_name}</td>
                    <td>
                      <span className={`badge ${query.analyzed ? 'analyzed' : 'pending'}`}>
                        {query.analyzed ? 'Analyzed' : 'Pending'}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${getPriorityBadge(query.query_time)}`}>
                        {getPriorityBadge(query.query_time).toUpperCase()}
                      </span>
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

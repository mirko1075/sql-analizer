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
  
  // Advanced filters
  const [sqlSearchFilter, setSqlSearchFilter] = useState('');
  const [minQueryTime, setMinQueryTime] = useState('');
  const [maxQueryTime, setMaxQueryTime] = useState('');
  const [minRowsExamined, setMinRowsExamined] = useState('');
  const [maxRowsExamined, setMaxRowsExamined] = useState('');
  const [databaseFilter, setDatabaseFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);

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

  // Filter queries based on all active filters
  const filteredQueries = queries.filter(query => {
    // SQL search filter
    if (sqlSearchFilter && !query.sql_text.toLowerCase().includes(sqlSearchFilter.toLowerCase())) {
      return false;
    }
    
    // Query time range filter
    if (minQueryTime && query.query_time < parseFloat(minQueryTime)) {
      return false;
    }
    if (maxQueryTime && query.query_time > parseFloat(maxQueryTime)) {
      return false;
    }
    
    // Rows examined range filter
    if (minRowsExamined && query.rows_examined < parseInt(minRowsExamined)) {
      return false;
    }
    if (maxRowsExamined && query.rows_examined > parseInt(maxRowsExamined)) {
      return false;
    }
    
    // Database filter
    if (databaseFilter && query.database_name !== databaseFilter) {
      return false;
    }
    
    // Priority filter
    if (priorityFilter && getPriorityBadge(query.query_time) !== priorityFilter) {
      return false;
    }
    
    return true;
  });

  // Get unique databases for filter dropdown
  const uniqueDatabases = Array.from(new Set(queries.map(q => q.database_name).filter(Boolean)));

  // Reset all filters
  const resetFilters = () => {
    setSqlSearchFilter('');
    setMinQueryTime('');
    setMaxQueryTime('');
    setMinRowsExamined('');
    setMaxRowsExamined('');
    setDatabaseFilter('');
    setPriorityFilter('');
  };

  // Check if any filter is active
  const hasActiveFilters = sqlSearchFilter || minQueryTime || maxQueryTime || 
    minRowsExamined || maxRowsExamined || databaseFilter || priorityFilter;

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
          
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
            <button 
              onClick={() => setShowFilters(!showFilters)}
              style={{
                padding: '8px 16px',
                borderRadius: '6px',
                border: showFilters ? '2px solid #3498db' : '1px solid #ddd',
                backgroundColor: showFilters ? '#ebf5fb' : 'white',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: '500',
                color: showFilters ? '#3498db' : '#333',
                transition: 'all 0.2s ease',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              🔍 Filters {hasActiveFilters && <span style={{ 
                backgroundColor: '#3498db', 
                color: 'white', 
                borderRadius: '10px', 
                padding: '2px 6px', 
                fontSize: '11px',
                fontWeight: 'bold'
              }}>ON</span>}
            </button>

            <select 
              value={statusFilter} 
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(0);
              }}
              style={{
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid #ddd',
                backgroundColor: 'white',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: '500'
              }}
            >
              <option value="">All Statuses</option>
              <option value="pending">⏳ Pending</option>
              <option value="analyzed">🔍 Analyzed</option>
              <option value="archived">📦 Archived</option>
              <option value="resolved">✅ Resolved</option>
            </select>
            
            <button 
              onClick={handleCollect} 
              disabled={collecting}
              style={{
                padding: '8px 16px',
                borderRadius: '6px',
                border: 'none',
                backgroundColor: collecting ? '#95a5a6' : '#3498db',
                color: 'white',
                cursor: collecting ? 'not-allowed' : 'pointer',
                fontSize: '14px',
                fontWeight: '500',
                transition: 'background-color 0.2s ease'
              }}
            >
              {collecting ? '🔄 Collecting...' : '🔄 Collect Now'}
            </button>
          </div>
        </div>

        {/* Advanced Filters Panel */}
        {showFilters && (
          <div style={{
            backgroundColor: '#f8f9fa',
            borderRadius: '8px',
            padding: '20px',
            marginBottom: '20px',
            border: '1px solid #e9ecef',
            boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
          }}>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              marginBottom: '16px'
            }}>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600', color: '#2c3e50' }}>
                🎯 Advanced Filters
              </h3>
              {hasActiveFilters && (
                <button
                  onClick={resetFilters}
                  style={{
                    padding: '6px 12px',
                    fontSize: '12px',
                    backgroundColor: '#e74c3c',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontWeight: '500'
                  }}
                >
                  ✖ Clear All
                </button>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '16px' }}>
              {/* SQL Search */}
              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: '500', color: '#555' }}>
                  🔎 SQL Query Search
                </label>
                <input
                  type="text"
                  placeholder="Search in SQL text..."
                  value={sqlSearchFilter}
                  onChange={(e) => setSqlSearchFilter(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid #ddd',
                    fontSize: '14px',
                    backgroundColor: 'white'
                  }}
                />
              </div>

              {/* Database Filter */}
              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: '500', color: '#555' }}>
                  🗄️ Database
                </label>
                <select
                  value={databaseFilter}
                  onChange={(e) => setDatabaseFilter(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid #ddd',
                    fontSize: '14px',
                    backgroundColor: 'white',
                    cursor: 'pointer'
                  }}
                >
                  <option value="">All Databases</option>
                  {uniqueDatabases.map(db => (
                    <option key={db} value={db}>{db}</option>
                  ))}
                </select>
              </div>

              {/* Priority Filter */}
              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: '500', color: '#555' }}>
                  ⚡ Priority
                </label>
                <select
                  value={priorityFilter}
                  onChange={(e) => setPriorityFilter(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid #ddd',
                    fontSize: '14px',
                    backgroundColor: 'white',
                    cursor: 'pointer'
                  }}
                >
                  <option value="">All Priorities</option>
                  <option value="critical">🔴 Critical</option>
                  <option value="high">🟠 High</option>
                  <option value="medium">🟡 Medium</option>
                  <option value="low">🟢 Low</option>
                </select>
              </div>

              {/* Query Time Min */}
              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: '500', color: '#555' }}>
                  ⏱️ Min Query Time (s)
                </label>
                <input
                  type="number"
                  placeholder="e.g., 1.5"
                  step="0.1"
                  value={minQueryTime}
                  onChange={(e) => setMinQueryTime(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid #ddd',
                    fontSize: '14px',
                    backgroundColor: 'white'
                  }}
                />
              </div>

              {/* Query Time Max */}
              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: '500', color: '#555' }}>
                  ⏱️ Max Query Time (s)
                </label>
                <input
                  type="number"
                  placeholder="e.g., 10"
                  step="0.1"
                  value={maxQueryTime}
                  onChange={(e) => setMaxQueryTime(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid #ddd',
                    fontSize: '14px',
                    backgroundColor: 'white'
                  }}
                />
              </div>

              {/* Rows Examined Min */}
              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: '500', color: '#555' }}>
                  📊 Min Rows Examined
                </label>
                <input
                  type="number"
                  placeholder="e.g., 1000"
                  value={minRowsExamined}
                  onChange={(e) => setMinRowsExamined(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid #ddd',
                    fontSize: '14px',
                    backgroundColor: 'white'
                  }}
                />
              </div>

              {/* Rows Examined Max */}
              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: '500', color: '#555' }}>
                  📊 Max Rows Examined
                </label>
                <input
                  type="number"
                  placeholder="e.g., 100000"
                  value={maxRowsExamined}
                  onChange={(e) => setMaxRowsExamined(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid #ddd',
                    fontSize: '14px',
                    backgroundColor: 'white'
                  }}
                />
              </div>
            </div>

            <div style={{ 
              marginTop: '16px', 
              padding: '12px', 
              backgroundColor: '#e8f4f8',
              borderRadius: '6px',
              fontSize: '13px',
              color: '#2c3e50'
            }}>
              <strong>📈 Results:</strong> Showing {filteredQueries.length} of {queries.length} queries
            </div>
          </div>
        )}

        {loading ? (
          <div className="loading">Loading queries...</div>
        ) : filteredQueries.length === 0 ? (
          <div className="loading">
            {queries.length === 0 
              ? 'No slow queries found. Run the simulator to generate test data.'
              : 'No queries match the current filters. Try adjusting your search criteria.'}
          </div>
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
                {filteredQueries.map((query) => (
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

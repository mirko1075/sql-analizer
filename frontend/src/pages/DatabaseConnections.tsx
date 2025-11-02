import React, { useState, useEffect } from 'react';
import { Plus, Database, Edit, Trash2, AlertCircle, CheckCircle } from 'lucide-react';
import { databaseConnectionService } from '../services/database.service';
import { teamService } from '../services/team.service';
import type { DatabaseConnection, Team } from '../types';
import { getErrorMessage } from '../utils/errorHandler';

export const DatabaseConnections: React.FC = () => {
  const [connections, setConnections] = useState<DatabaseConnection[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [testingConnId, setTestingConnId] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      const [connectionsData, teamsData] = await Promise.all([
        databaseConnectionService.list(),
        teamService.list(),
      ]);
      setConnections(connectionsData);
      setTeams(teamsData);
    } catch (err) {
      console.error('Failed to load data:', err);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async (id: string) => {
    try {
      setTestingConnId(id);
      const result = await databaseConnectionService.test(id);
      if (result.success) {
        alert(`✅ Connection successful!`);
      } else {
        alert(`❌ Connection failed: ${result.error || 'Unknown error'}`);
      }
    } catch (err) {
      alert(`❌ Connection test failed: ${getErrorMessage(err)}`);
    } finally {
      setTestingConnId(null);
    }
  };

  const getTeamName = (teamId: string) => {
    return teams.find(team => team.id === teamId)?.name || 'Unknown Team';
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading database connections...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center">
              <Database className="mr-3" size={32} />
              Database Connections
            </h1>
            <p className="mt-2 text-gray-600">Manage database connections for monitoring</p>
          </div>
          <button className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700">
            <Plus className="mr-2" size={18} />
            Add Connection
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-6 rounded-md bg-red-50 p-4">
          <div className="flex">
            <AlertCircle className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <p className="text-sm font-medium text-red-800">{error}</p>
            </div>
          </div>
        </div>
      )}

      {connections.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <Database className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No database connections</h3>
          <p className="mt-1 text-sm text-gray-500">Get started by adding a database connection.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {connections.map((conn) => (
            <div key={conn.id} className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                    <Database className="mr-2" size={20} />
                    {conn.name}
                  </h3>
                  <p className="mt-1 text-xs text-gray-500">Team: {getTeamName(conn.team_id)}</p>
                </div>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  conn.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                }`}>
                  {conn.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>

              <div className="space-y-2 text-sm text-gray-600">
                <div><span className="font-medium">Type:</span> {conn.db_type.toUpperCase()}</div>
                <div><span className="font-medium">Host:</span> {conn.host}:{conn.port}</div>
                <div><span className="font-medium">Database:</span> {conn.database}</div>
                <div><span className="font-medium">Username:</span> {conn.username}</div>
              </div>

              <div className="mt-6 flex items-center justify-between">
                <button
                  onClick={() => handleTest(conn.id)}
                  disabled={testingConnId === conn.id}
                  className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-green-700 hover:bg-green-50 rounded-md disabled:opacity-50"
                >
                  {testingConnId === conn.id ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-green-700 mr-2"></div>
                      Testing...
                    </>
                  ) : (
                    <>
                      <CheckCircle size={16} className="mr-1" />
                      Test Connection
                    </>
                  )}
                </button>
                
                <div className="flex items-center space-x-2">
                  <button className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-50 rounded-md">
                    <Edit size={16} className="mr-1" />
                    Edit
                  </button>
                  <button className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50 rounded-md">
                    <Trash2 size={16} className="mr-1" />
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default DatabaseConnections;

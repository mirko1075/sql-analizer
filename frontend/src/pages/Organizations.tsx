/**
 * Organizations Page - Manage organizations and multi-tenancy
 */
import React, { useState, useEffect } from 'react';
import {
  Building,
  Plus,
  Key,
  Trash2,
  RefreshCw,
  Calendar,
  CheckCircle,
} from 'lucide-react';
import {
  listOrganizations,
  createOrganization,
  regenerateOrgApiKey,
  deleteOrganization,
} from '../services/api';
import type { Organization } from '../types';

const Organizations: React.FC = () => {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [apiKeyDisplay, setApiKeyDisplay] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    settings: {},
  });

  useEffect(() => {
    loadOrganizations();
    // Refresh every 30 seconds
    const interval = setInterval(loadOrganizations, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadOrganizations = async () => {
    try {
      const data = await listOrganizations();
      setOrganizations(data);
    } catch (error) {
      console.error('Failed to load organizations:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setActionLoading('create');
      await createOrganization(formData);
      setShowCreateForm(false);
      setFormData({ name: '', settings: {} });
      loadOrganizations();
    } catch (error) {
      console.error('Failed to create organization:', error);
      alert('Failed to create organization. Check console for details.');
    } finally {
      setActionLoading(null);
    }
  };

  const handleRegenerateApiKey = async (id: number, name: string) => {
    if (!confirm(`Regenerate API key for "${name}"? The old key will stop working.`)) {
      return;
    }
    try {
      setActionLoading(`regenerate-${id}`);
      const response = await regenerateOrgApiKey(id);
      setApiKeyDisplay(response.api_key);
      loadOrganizations();
    } catch (error) {
      console.error('Failed to regenerate API key:', error);
      alert('Failed to regenerate API key. Check console for details.');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`Delete organization "${name}"? This action cannot be undone.`)) {
      return;
    }
    try {
      setActionLoading(`delete-${id}`);
      await deleteOrganization(id);
      loadOrganizations();
    } catch (error) {
      console.error('Failed to delete organization:', error);
      alert('Failed to delete organization. Check console for details.');
    } finally {
      setActionLoading(null);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  const getKeyStatus = (expiresAt?: string) => {
    if (!expiresAt) return { text: 'No key', color: 'text-gray-500' };
    const expiry = new Date(expiresAt);
    const now = new Date();
    if (expiry < now) return { text: 'Expired', color: 'text-red-600' };
    return { text: 'Active', color: 'text-green-600' };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          <p className="mt-4 text-gray-600">Loading organizations...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center">
              <Building className="mr-3 text-primary-600" size={32} />
              Organizations
            </h1>
            <p className="mt-2 text-gray-600">
              Manage multi-tenant organizations and API access
            </p>
          </div>
          <div className="flex space-x-3">
            <button
              onClick={loadOrganizations}
              disabled={loading}
              className="btn-secondary flex items-center space-x-2"
            >
              <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
              <span>Refresh</span>
            </button>
            <button
              onClick={() => setShowCreateForm(true)}
              className="btn-primary flex items-center space-x-2"
            >
              <Plus size={18} />
              <span>New Organization</span>
            </button>
          </div>
        </div>

        {/* Organizations Table */}
        {organizations.length === 0 ? (
          <div className="bg-white rounded-lg shadow-md p-12 text-center">
            <Building className="mx-auto text-gray-400 mb-4" size={48} />
            <p className="text-gray-600 text-lg">No organizations yet</p>
            <p className="text-gray-500 text-sm mt-2">
              Click "New Organization" to create your first one
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    API Key Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {organizations.map((org) => {
                  const keyStatus = getKeyStatus(org.api_key_expires_at);
                  return (
                    <tr key={org.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {org.id}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <Building size={20} className="text-primary-600 mr-2" />
                          <div>
                            <div className="text-sm font-medium text-gray-900">{org.name}</div>
                            <div className="text-xs text-gray-500">
                              Updated: {formatDate(org.updated_at)}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center text-sm text-gray-600">
                          <Calendar size={16} className="mr-1" />
                          {formatDate(org.created_at)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`text-sm font-medium ${keyStatus.color}`}>
                          {keyStatus.text}
                        </span>
                        {org.api_key_created_at && (
                          <div className="text-xs text-gray-500 mt-1">
                            Created: {formatDate(org.api_key_created_at)}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <div className="flex space-x-2">
                          <button
                            onClick={() => handleRegenerateApiKey(org.id, org.name)}
                            disabled={actionLoading === `regenerate-${org.id}`}
                            className="inline-flex items-center px-3 py-1 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                            title="Regenerate API Key"
                          >
                            <Key size={16} className="mr-1" />
                            {actionLoading === `regenerate-${org.id}` ? 'Generating...' : 'New Key'}
                          </button>
                          <button
                            onClick={() => handleDelete(org.id, org.name)}
                            disabled={actionLoading === `delete-${org.id}`}
                            className="inline-flex items-center px-3 py-1 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-red-600 hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                            title="Delete Organization"
                          >
                            <Trash2 size={16} className="mr-1" />
                            {actionLoading === `delete-${org.id}` ? 'Deleting...' : 'Delete'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Organization Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4">
            <h2 className="text-2xl font-bold mb-6 flex items-center">
              <Building className="mr-2 text-primary-600" />
              Create New Organization
            </h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Organization Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  placeholder="Acme Corporation"
                />
              </div>

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateForm(false);
                    setFormData({ name: '', settings: {} });
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading === 'create'}
                  className="btn-primary"
                >
                  {actionLoading === 'create' ? 'Creating...' : 'Create Organization'}
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
            <h2 className="text-2xl font-bold mb-4 text-green-600 flex items-center">
              <CheckCircle className="mr-2" />
              API Key Generated!
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
  );
};

export default Organizations;

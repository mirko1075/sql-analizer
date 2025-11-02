import React, { useState, useEffect } from 'react';
import { Plus, Users, Edit, Trash2, AlertCircle, UserPlus } from 'lucide-react';
import { teamService } from '../services/team.service';
import { organizationService } from '../services/organization.service';
import type { Team, Organization } from '../types';
import { getErrorMessage } from '../utils/errorHandler';

export const Teams: React.FC = () => {
  const [teams, setTeams] = useState<Team[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingTeam, setEditingTeam] = useState<Team | null>(null);
  const [deletingTeamId, setDeletingTeamId] = useState<string | null>(null);
  const [selectedTeamForMembers, setSelectedTeamForMembers] = useState<Team | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      const [teamsData, orgsData] = await Promise.all([
        teamService.list(),
        organizationService.list(),
      ]);
      setTeams(teamsData);
      setOrganizations(orgsData);
    } catch (err) {
      console.error('Failed to load data:', err);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingTeam(null);
    setShowCreateModal(true);
  };

  const handleEdit = (team: Team) => {
    setEditingTeam(team);
    setShowCreateModal(true);
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this team?')) {
      return;
    }

    try {
      setDeletingTeamId(id);
      await teamService.delete(id);
      await loadData();
    } catch (err) {
      console.error('Failed to delete team:', err);
      setError(getErrorMessage(err));
    } finally {
      setDeletingTeamId(null);
    }
  };

  const handleModalClose = (shouldRefresh: boolean) => {
    setShowCreateModal(false);
    setEditingTeam(null);
    if (shouldRefresh) {
      loadData();
    }
  };

  const handleManageMembers = (team: Team) => {
    setSelectedTeamForMembers(team);
  };

  const getOrganizationName = (orgId: string) => {
    return organizations.find(org => org.id === orgId)?.name || 'Unknown';
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading teams...</p>
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
              <Users className="mr-3" size={32} />
              Teams
            </h1>
            <p className="mt-2 text-gray-600">Manage teams and their members</p>
          </div>
          <button
            onClick={handleCreate}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
          >
            <Plus className="mr-2" size={18} />
            Create Team
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

      {teams.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <Users className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No teams</h3>
          <p className="mt-1 text-sm text-gray-500">Get started by creating a new team.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {teams.map((team) => (
            <div key={team.id} className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold text-gray-900">{team.name}</h3>
              <p className="mt-1 text-xs text-gray-500">{getOrganizationName(team.organization_id)}</p>
              <div className="mt-6 flex flex-col space-y-2">
                <button
                  onClick={() => handleManageMembers(team)}
                  className="inline-flex items-center justify-center px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-50 rounded-md"
                >
                  <UserPlus size={16} className="mr-1" />
                  Manage Members
                </button>
                <div className="flex space-x-2">
                  <button onClick={() => handleEdit(team)} className="flex-1 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 rounded-md">
                    <Edit size={16} className="inline mr-1" />
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(team.id)}
                    disabled={deletingTeamId === team.id}
                    className="flex-1 px-3 py-1.5 text-sm text-red-700 hover:bg-red-50 rounded-md disabled:opacity-50"
                  >
                    <Trash2 size={16} className="inline mr-1" />
                    {deletingTeamId === team.id ? 'Deleting...' : 'Delete'}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreateModal && <TeamModal team={editingTeam} organizations={organizations} onClose={handleModalClose} />}
      {selectedTeamForMembers && <TeamMembersModal team={selectedTeamForMembers} onClose={() => setSelectedTeamForMembers(null)} />}
    </div>
  );
};

// Note: TeamModal, TeamMembersModal, and AddMemberModal would need to be imported or defined separately
// For brevity, I'll include simplified placeholders

const TeamModal: React.FC<{ team: Team | null; organizations: Organization[]; onClose: (refresh: boolean) => void }> = ({ onClose }) => {
  return (
    <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg p-6">
        <p>Team Modal - Coming Soon</p>
        <button onClick={() => onClose(false)} className="mt-4 px-4 py-2 bg-gray-200 rounded">Close</button>
      </div>
    </div>
  );
};

const TeamMembersModal: React.FC<{ team: Team; onClose: () => void }> = ({ onClose }) => {
  return (
    <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg p-6">
        <p>Team Members Modal - Coming Soon</p>
        <button onClick={onClose} className="mt-4 px-4 py-2 bg-gray-200 rounded">Close</button>
      </div>
    </div>
  );
};

export default Teams;

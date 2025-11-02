/**
 * Onboarding Page - 3-step wizard for new customer setup
 *
 * Steps:
 * 1. Collector Setup - Create organization, team, and collector
 * 2. Database Configuration - Add databases to monitor
 * 3. Verification - Deploy agent and verify connection
 */
import React, { useState } from 'react';
import {
  Building2,
  Database,
  CheckCircle,
  ArrowRight,
  ArrowLeft,
  Copy,
  Check,
  AlertCircle,
  Loader2,
  Play,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import onboardingService, {
  type DatabaseConfig,
  type OnboardingStartResponse,
  type OnboardingStatusResponse,
} from '../services/onboarding.service';
import { getErrorMessage } from '../utils/errorHandler';

type Step = 1 | 2 | 3;

interface FormData {
  // Step 1
  organizationName: string;
  teamName: string;
  collectorName: string;
  collectorHostname: string;

  // Step 2
  databases: DatabaseConfig[];

  // Step 3 (set after step 1)
  collectorId?: string;
  agentToken?: string;
  dockerCommand?: string;
}

const Onboarding: React.FC = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState<Step>(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [copiedToken, setCopiedToken] = useState(false);
  const [copiedCommand, setCopiedCommand] = useState(false);

  const [formData, setFormData] = useState<FormData>({
    organizationName: '',
    teamName: 'Main Team',
    collectorName: 'Production Collector',
    collectorHostname: '',
    databases: [],
  });

  const [verificationStatus, setVerificationStatus] = useState<OnboardingStatusResponse | null>(null);
  const [verificationLoading, setVerificationLoading] = useState(false);

  // ==================== Step 1: Collector Setup ====================

  const handleStep1Submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await onboardingService.start({
        organization_name: formData.organizationName,
        team_name: formData.teamName,
        collector_name: formData.collectorName,
        collector_hostname: formData.collectorHostname || undefined,
      });

      setFormData({
        ...formData,
        collectorId: response.collector_id,
        agentToken: response.agent_token,
        dockerCommand: response.docker_command,
      });

      setCurrentStep(2);
    } catch (err) {
      console.error('Step 1 failed:', err);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  // ==================== Step 2: Database Configuration ====================

  const addDatabase = () => {
    setFormData({
      ...formData,
      databases: [
        ...formData.databases,
        {
          name: '',
          db_type: 'mysql',
          host: 'localhost',
          port: 3306,
          database_name: '',
          username: '',
          password: '',
          ssl_enabled: false,
        },
      ],
    });
  };

  const removeDatabase = (index: number) => {
    const newDatabases = formData.databases.filter((_, i) => i !== index);
    setFormData({ ...formData, databases: newDatabases });
  };

  const updateDatabase = (index: number, field: keyof DatabaseConfig, value: any) => {
    const newDatabases = [...formData.databases];
    (newDatabases[index] as any)[field] = value;
    setFormData({ ...formData, databases: newDatabases });
  };

  const handleStep2Submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    if (!formData.collectorId) {
      setError('No collector ID found. Please restart onboarding.');
      setLoading(false);
      return;
    }

    if (formData.databases.length === 0) {
      setError('Please add at least one database');
      setLoading(false);
      return;
    }

    try {
      await onboardingService.addDatabases({
        collector_id: formData.collectorId,
        databases: formData.databases,
      });

      setCurrentStep(3);
    } catch (err) {
      console.error('Step 2 failed:', err);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  // ==================== Step 3: Verification ====================

  const checkStatus = async () => {
    if (!formData.collectorId) return;

    setVerificationLoading(true);
    try {
      const status = await onboardingService.getStatus(formData.collectorId);
      setVerificationStatus(status);
    } catch (err) {
      console.error('Failed to check status:', err);
    } finally {
      setVerificationLoading(false);
    }
  };

  const completeOnboarding = async () => {
    if (!formData.collectorId) return;

    setLoading(true);
    setError('');

    try {
      await onboardingService.complete({ collector_id: formData.collectorId });
      navigate('/dashboard');
    } catch (err) {
      console.error('Complete onboarding failed:', err);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string, type: 'token' | 'command') => {
    navigator.clipboard.writeText(text);
    if (type === 'token') {
      setCopiedToken(true);
      setTimeout(() => setCopiedToken(false), 2000);
    } else {
      setCopiedCommand(true);
      setTimeout(() => setCopiedCommand(false), 2000);
    }
  };

  // ==================== Render ====================

  const renderStepIndicator = () => (
    <div className="flex items-center justify-center mb-8">
      {[1, 2, 3].map((step) => (
        <React.Fragment key={step}>
          <div className="flex items-center">
            <div
              className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${
                currentStep >= step
                  ? 'bg-blue-600 border-blue-600 text-white'
                  : 'bg-white border-gray-300 text-gray-400'
              }`}
            >
              {step}
            </div>
            <span className={`ml-2 text-sm font-medium ${currentStep >= step ? 'text-gray-900' : 'text-gray-400'}`}>
              {step === 1 ? 'Collector Setup' : step === 2 ? 'Databases' : 'Verification'}
            </span>
          </div>
          {step < 3 && (
            <div
              className={`w-16 h-1 mx-4 ${currentStep > step ? 'bg-blue-600' : 'bg-gray-300'}`}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );

  const renderStep1 = () => (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="flex items-center mb-6">
            <Building2 className="h-8 w-8 text-blue-600 mr-3" />
            <div>
              <h3 className="text-lg font-medium text-gray-900">Collector Setup</h3>
              <p className="mt-1 text-sm text-gray-500">
                Create your organization and set up your first collector
              </p>
            </div>
          </div>

          {error && (
            <div className="mb-4 rounded-md bg-red-50 p-4">
              <div className="flex">
                <AlertCircle className="h-5 w-5 text-red-400" />
                <div className="ml-3">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          <form onSubmit={handleStep1Submit}>
            <div className="space-y-4">
              <div>
                <label htmlFor="organizationName" className="block text-sm font-medium text-gray-700">
                  Organization Name *
                </label>
                <input
                  type="text"
                  id="organizationName"
                  required
                  value={formData.organizationName}
                  onChange={(e) => setFormData({ ...formData, organizationName: e.target.value })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  placeholder="Acme Corp"
                />
              </div>

              <div>
                <label htmlFor="teamName" className="block text-sm font-medium text-gray-700">
                  Team Name *
                </label>
                <input
                  type="text"
                  id="teamName"
                  required
                  value={formData.teamName}
                  onChange={(e) => setFormData({ ...formData, teamName: e.target.value })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  placeholder="Main Team"
                />
              </div>

              <div>
                <label htmlFor="collectorName" className="block text-sm font-medium text-gray-700">
                  Collector Name *
                </label>
                <input
                  type="text"
                  id="collectorName"
                  required
                  value={formData.collectorName}
                  onChange={(e) => setFormData({ ...formData, collectorName: e.target.value })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  placeholder="Production Collector"
                />
              </div>

              <div>
                <label htmlFor="collectorHostname" className="block text-sm font-medium text-gray-700">
                  Collector Hostname (optional)
                </label>
                <input
                  type="text"
                  id="collectorHostname"
                  value={formData.collectorHostname}
                  onChange={(e) => setFormData({ ...formData, collectorHostname: e.target.value })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  placeholder="collector-prod-01"
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                type="submit"
                disabled={loading}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Loader2 className="animate-spin -ml-1 mr-2 h-4 w-4" />
                    Creating...
                  </>
                ) : (
                  <>
                    Next
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="flex items-center mb-6">
            <Database className="h-8 w-8 text-blue-600 mr-3" />
            <div>
              <h3 className="text-lg font-medium text-gray-900">Database Configuration</h3>
              <p className="mt-1 text-sm text-gray-500">
                Add the databases you want to monitor for slow queries
              </p>
            </div>
          </div>

          {error && (
            <div className="mb-4 rounded-md bg-red-50 p-4">
              <div className="flex">
                <AlertCircle className="h-5 w-5 text-red-400" />
                <div className="ml-3">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          <form onSubmit={handleStep2Submit}>
            <div className="space-y-6">
              {formData.databases.map((db, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex justify-between items-center mb-4">
                    <h4 className="text-sm font-medium text-gray-900">Database {index + 1}</h4>
                    {formData.databases.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeDatabase(index)}
                        className="text-sm text-red-600 hover:text-red-700"
                      >
                        Remove
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Name *</label>
                      <input
                        type="text"
                        required
                        value={db.name}
                        onChange={(e) => updateDatabase(index, 'name', e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                        placeholder="Production MySQL"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700">Type *</label>
                      <select
                        value={db.db_type}
                        onChange={(e) => updateDatabase(index, 'db_type', e.target.value as 'mysql' | 'postgres')}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      >
                        <option value="mysql">MySQL</option>
                        <option value="postgres">PostgreSQL</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700">Host *</label>
                      <input
                        type="text"
                        required
                        value={db.host}
                        onChange={(e) => updateDatabase(index, 'host', e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                        placeholder="localhost"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700">Port *</label>
                      <input
                        type="number"
                        required
                        value={db.port}
                        onChange={(e) => updateDatabase(index, 'port', parseInt(e.target.value))}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700">Database Name *</label>
                      <input
                        type="text"
                        required
                        value={db.database_name}
                        onChange={(e) => updateDatabase(index, 'database_name', e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                        placeholder="myapp"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700">Username *</label>
                      <input
                        type="text"
                        required
                        value={db.username}
                        onChange={(e) => updateDatabase(index, 'username', e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                        placeholder="monitor_user"
                      />
                    </div>

                    <div className="col-span-2">
                      <label className="block text-sm font-medium text-gray-700">Password *</label>
                      <input
                        type="password"
                        required
                        value={db.password}
                        onChange={(e) => updateDatabase(index, 'password', e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      />
                    </div>
                  </div>
                </div>
              ))}

              <button
                type="button"
                onClick={addDatabase}
                className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Add Database
              </button>
            </div>

            <div className="mt-6 flex justify-between">
              <button
                type="button"
                onClick={() => setCurrentStep(1)}
                className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back
              </button>
              <button
                type="submit"
                disabled={loading || formData.databases.length === 0}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Loader2 className="animate-spin -ml-1 mr-2 h-4 w-4" />
                    Saving...
                  </>
                ) : (
                  <>
                    Next
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="flex items-center mb-6">
            <CheckCircle className="h-8 w-8 text-green-600 mr-3" />
            <div>
              <h3 className="text-lg font-medium text-gray-900">Deploy Collector Agent</h3>
              <p className="mt-1 text-sm text-gray-500">
                Run the Docker command on your server to start collecting metrics
              </p>
            </div>
          </div>

          {error && (
            <div className="mb-4 rounded-md bg-red-50 p-4">
              <div className="flex">
                <AlertCircle className="h-5 w-5 text-red-400" />
                <div className="ml-3">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Agent Token
              </label>
              <div className="flex items-center">
                <code className="flex-1 block px-3 py-2 bg-gray-50 border border-gray-300 rounded-md text-sm font-mono">
                  {formData.agentToken}
                </code>
                <button
                  type="button"
                  onClick={() => formData.agentToken && copyToClipboard(formData.agentToken, 'token')}
                  className="ml-2 inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  {copiedToken ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Docker Run Command
              </label>
              <div className="flex items-start">
                <code className="flex-1 block px-3 py-2 bg-gray-50 border border-gray-300 rounded-md text-xs font-mono whitespace-pre-wrap">
                  {formData.dockerCommand}
                </code>
                <button
                  type="button"
                  onClick={() => formData.dockerCommand && copyToClipboard(formData.dockerCommand, 'command')}
                  className="ml-2 inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  {copiedCommand ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div className="border-t border-gray-200 pt-6">
              <button
                type="button"
                onClick={checkStatus}
                disabled={verificationLoading}
                className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                {verificationLoading ? (
                  <>
                    <Loader2 className="animate-spin -ml-1 mr-2 h-4 w-4" />
                    Checking...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Check Status
                  </>
                )}
              </button>

              {verificationStatus && (
                <div className="mt-4 border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center mb-2">
                    <h4 className="text-sm font-medium text-gray-900">Collector Status</h4>
                    <span
                      className={`ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        verificationStatus.collector_status === 'ACTIVE'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}
                    >
                      {verificationStatus.collector_status}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600">
                    <p>
                      Databases: {verificationStatus.connected_databases} / {verificationStatus.total_databases} connected
                    </p>
                    {verificationStatus.last_heartbeat && (
                      <p className="mt-1">
                        Last heartbeat: {new Date(verificationStatus.last_heartbeat).toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="mt-6 flex justify-between">
            <button
              type="button"
              onClick={() => setCurrentStep(2)}
              className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </button>
            <button
              type="button"
              onClick={completeOnboarding}
              disabled={loading}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="animate-spin -ml-1 mr-2 h-4 w-4" />
                  Completing...
                </>
              ) : (
                <>
                  Complete Setup
                  <CheckCircle className="ml-2 h-4 w-4" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-extrabold text-gray-900 sm:text-4xl">
            Welcome to DBPower
          </h2>
          <p className="mt-4 text-lg text-gray-600">
            Let's get you set up in just 3 simple steps
          </p>
        </div>

        {renderStepIndicator()}

        {currentStep === 1 && renderStep1()}
        {currentStep === 2 && renderStep2()}
        {currentStep === 3 && renderStep3()}
      </div>
    </div>
  );
};

export default Onboarding;

/**
 * Main App Component with Routing
 */
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Home, Database, Activity, BarChart3, LogOut, User as UserIcon, Building2, Users, Server } from 'lucide-react';
import { AuthProvider } from './contexts/AuthContext';
import { useAuth } from './hooks/useAuth';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { Login, Register } from './pages/auth';
import Dashboard from './pages/Dashboard';
import SlowQueries from './pages/SlowQueries';
import QueryDetail from './pages/QueryDetail';
import Statistics from './pages/Statistics';
import Collectors from './pages/Collectors';
import Organizations from './pages/Organizations';
import Teams from './pages/Teams';
import DatabaseConnections from './pages/DatabaseConnections';
import './index.css';

// Create a React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000,
    },
  },
});

function Navigation() {
  const { user, logout, isAuthenticated } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <nav className="bg-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <Database className="h-8 w-8 text-primary-600" />
              <span className="ml-2 text-xl font-bold text-gray-900">
                AI Query Analyzer
              </span>
            </div>
            <div className="ml-10 flex space-x-4">
              <Link
                to="/"
                className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 hover:text-primary-600 hover:bg-gray-50 rounded-md transition-colors"
              >
                <Home className="mr-2" size={18} />
                Dashboard
              </Link>
              <Link
                to="/queries"
                className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 hover:text-primary-600 hover:bg-gray-50 rounded-md transition-colors"
              >
                <Database className="mr-2" size={18} />
                Slow Queries
              </Link>
              <Link
                to="/stats"
                className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 hover:text-primary-600 hover:bg-gray-50 rounded-md transition-colors"
              >
                <BarChart3 className="mr-2" size={18} />
                Statistics
              </Link>
              <Link
                to="/organizations"
                className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 hover:text-primary-600 hover:bg-gray-50 rounded-md transition-colors"
              >
                <Building2 className="mr-2" size={18} />
                Organizations
              </Link>
              <Link
                to="/teams"
                className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 hover:text-primary-600 hover:bg-gray-50 rounded-md transition-colors"
              >
                <Users className="mr-2" size={18} />
                Teams
              </Link>
              <Link
                to="/databases"
                className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 hover:text-primary-600 hover:bg-gray-50 rounded-md transition-colors"
              >
                <Server className="mr-2" size={18} />
                Databases
              </Link>
              {user?.is_superuser && (
                <Link
                  to="/collectors"
                  className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 hover:text-primary-600 hover:bg-gray-50 rounded-md transition-colors"
                >
                  <Activity className="mr-2" size={18} />
                  Collectors
                </Link>
              )}
            </div>
          </div>
          
          {/* User menu */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center text-sm text-gray-700">
              <UserIcon className="mr-2" size={18} />
              <span>{user?.full_name || user?.email}</span>
              {user?.is_superuser && (
                <span className="ml-2 px-2 py-1 text-xs font-semibold text-blue-800 bg-blue-100 rounded-full">
                  Superuser
                </span>
              )}
            </div>
            <button
              onClick={handleLogout}
              className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 hover:text-red-600 hover:bg-gray-50 rounded-md transition-colors"
            >
              <LogOut className="mr-2" size={18} />
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Router>
          <div className="min-h-screen bg-gray-50">
            <Navigation />

            {/* Main Content */}
            <Routes>
              {/* Public routes */}
              <Route
                path="/login"
                element={
                  <ProtectedRoute requireAuth={false}>
                    <Login />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/register"
                element={
                  <ProtectedRoute requireAuth={false}>
                    <Register />
                  </ProtectedRoute>
                }
              />

              {/* Protected routes */}
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <Dashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/queries"
                element={
                  <ProtectedRoute>
                    <SlowQueries />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/queries/:id"
                element={
                  <ProtectedRoute>
                    <QueryDetail />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/stats"
                element={
                  <ProtectedRoute>
                    <Statistics />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/organizations"
                element={
                  <ProtectedRoute>
                    <Organizations />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/teams"
                element={
                  <ProtectedRoute>
                    <Teams />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/databases"
                element={
                  <ProtectedRoute>
                    <DatabaseConnections />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/collectors"
                element={
                  <ProtectedRoute requireSuperuser>
                    <Collectors />
                  </ProtectedRoute>
                }
              />
            </Routes>
          </div>
        </Router>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;

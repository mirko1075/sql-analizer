/**
 * Main App Component with Routing and Authentication
 */
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Home, Database, Activity, BarChart3, LogOut, User } from 'lucide-react';
import { useAuthStore } from './store/authStore';
import axios from 'axios';
import Dashboard from './pages/Dashboard';
import SlowQueries from './pages/SlowQueries';
import QueryDetail from './pages/QueryDetail';
import Statistics from './pages/Statistics';
import Collectors from './pages/Collectors';
import Login from './pages/Login';
import './index.css';

// Configure axios interceptor for authentication
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token && config.url?.startsWith(API_URL)) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

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

// Private Route wrapper component
function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const token = useAuthStore((state) => state.token);

  if (!isAuthenticated || !token) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function App() {
  const { isAuthenticated, user, logout } = useAuthStore();

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="min-h-screen bg-gray-50">
          {isAuthenticated && (
            /* Navigation - only show when authenticated */
            <nav className="bg-white shadow-md">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between h-16">
                  <div className="flex">
                    <div className="flex-shrink-0 flex items-center">
                      <Database className="h-8 w-8 text-primary-600" />
                      <span className="ml-2 text-xl font-bold text-gray-900">
                        DBPower AI Cloud
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
                        to="/collectors"
                        className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 hover:text-primary-600 hover:bg-gray-50 rounded-md transition-colors"
                      >
                        <Activity className="mr-2" size={18} />
                        Collectors
                      </Link>
                    </div>
                  </div>

                  {/* User menu */}
                  <div className="flex items-center space-x-4">
                    <div className="flex items-center text-sm text-gray-700">
                      <User className="mr-2" size={18} />
                      <span className="font-medium">{user?.full_name || user?.email}</span>
                      <span className="ml-2 px-2 py-1 bg-primary-100 text-primary-700 rounded text-xs">
                        {user?.role}
                      </span>
                    </div>
                    <button
                      onClick={logout}
                      className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
                    >
                      <LogOut className="mr-2" size={18} />
                      Logout
                    </button>
                  </div>
                </div>
              </div>
            </nav>
          )}

          {/* Main Content */}
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/"
              element={
                <PrivateRoute>
                  <Dashboard />
                </PrivateRoute>
              }
            />
            <Route
              path="/queries"
              element={
                <PrivateRoute>
                  <SlowQueries />
                </PrivateRoute>
              }
            />
            <Route
              path="/queries/:id"
              element={
                <PrivateRoute>
                  <QueryDetail />
                </PrivateRoute>
              }
            />
            <Route
              path="/stats"
              element={
                <PrivateRoute>
                  <Statistics />
                </PrivateRoute>
              }
            />
            <Route
              path="/collectors"
              element={
                <PrivateRoute>
                  <Collectors />
                </PrivateRoute>
              }
            />
          </Routes>
        </div>
      </Router>
    </QueryClientProvider>
  );
}

export default App;

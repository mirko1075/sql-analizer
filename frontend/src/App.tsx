/**
 * Main App Component with Routing
 */
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Home, Database, Activity, BarChart3 } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import SlowQueries from './pages/SlowQueries';
import QueryDetail from './pages/QueryDetail';
import Statistics from './pages/Statistics';
import Collectors from './pages/Collectors';
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

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="min-h-screen bg-gray-50">
          {/* Navigation */}
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
                      to="/collectors"
                      className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 hover:text-primary-600 hover:bg-gray-50 rounded-md transition-colors"
                    >
                      <Activity className="mr-2" size={18} />
                      Collectors
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </nav>

          {/* Main Content */}
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/queries" element={<SlowQueries />} />
            <Route path="/queries/:id" element={<QueryDetail />} />
            <Route path="/stats" element={<Statistics />} />
            <Route path="/collectors" element={<Collectors />} />
          </Routes>
        </div>
      </Router>
    </QueryClientProvider>
  );
}

export default App;

import { Outlet, Link, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Building, FileSearch, LogOut } from 'lucide-react';
import { useAuthStore } from '../store/authStore';

export default function Layout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <aside style={{ width: '250px', background: '#1a1a2e', color: 'white', padding: '20px' }}>
        <h2 style={{ marginBottom: '30px' }}>DBPower Admin</h2>
        <nav>
          <Link to="/" style={{ display: 'flex', alignItems: 'center', padding: '10px', color: 'white', textDecoration: 'none' }}>
            <LayoutDashboard size={20} style={{ marginRight: '10px' }} /> Dashboard
          </Link>
          <Link to="/organizations" style={{ display: 'flex', alignItems: 'center', padding: '10px', color: 'white', textDecoration: 'none' }}>
            <Building size={20} style={{ marginRight: '10px' }} /> Organizations
          </Link>
          <Link to="/queries" style={{ display: 'flex', alignItems: 'center', padding: '10px', color: 'white', textDecoration: 'none' }}>
            <FileSearch size={20} style={{ marginRight: '10px' }} /> Queries
          </Link>
        </nav>
        <div style={{ position: 'absolute', bottom: '20px' }}>
          <p style={{ fontSize: '14px', marginBottom: '10px' }}>{user?.email}</p>
          <button onClick={handleLogout} style={{ display: 'flex', alignItems: 'center', background: 'transparent', border: 'none', color: 'white', cursor: 'pointer' }}>
            <LogOut size={20} style={{ marginRight: '10px' }} /> Logout
          </button>
        </div>
      </aside>
      <main style={{ flex: 1, padding: '20px', background: '#f5f5f5' }}>
        <Outlet />
      </main>
    </div>
  );
}

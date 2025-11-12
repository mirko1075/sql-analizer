import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { authAPI } from '../services/api';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      console.log('[Login] Attempting login...');
      const { data } = await authAPI.login(email, password);
      console.log('[Login] Login response:', { hasToken: !!data.access_token, user: data.user });

      login(data.access_token, data.user);

      // Verify token was saved
      const savedToken = localStorage.getItem('auth_token');
      console.log('[Login] Token saved in localStorage:', savedToken ? savedToken.substring(0, 20) + '...' : 'NOT SAVED');

      // Small delay to ensure state is updated
      setTimeout(() => {
        console.log('[Login] Navigating to dashboard');
        navigate('/', { replace: true });
      }, 100);
    } catch (err: any) {
      console.error('[Login] Login failed:', err);
      setError(err.response?.data?.detail || err.response?.data?.message || 'Login failed');
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#f5f5f5' }}>
      <div style={{ background: 'white', padding: '40px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', width: '400px' }}>
        <h1 style={{ marginBottom: '30px', textAlign: 'center' }}>DBPower Admin</h1>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '20px' }}>
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{ width: '100%', padding: '12px', border: '1px solid #ddd', borderRadius: '4px' }}
              required
            />
          </div>
          <div style={{ marginBottom: '20px' }}>
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{ width: '100%', padding: '12px', border: '1px solid #ddd', borderRadius: '4px' }}
              required
            />
          </div>
          {error && <p style={{ color: 'red', marginBottom: '20px' }}>{error}</p>}
          <button type="submit" style={{ width: '100%', padding: '12px', background: '#1a1a2e', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
            Login
          </button>
        </form>
      </div>
    </div>
  );
}

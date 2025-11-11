import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { statsAPI } from '../services/api';
import { Activity, Database, Users, TrendingUp } from 'lucide-react';

export default function Dashboard() {
  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: () => statsAPI.dashboard().then(r => r.data),
  });

  const cards = [
    { title: 'Total Queries', value: stats?.total_queries || 0, icon: Database, color: '#3b82f6' },
    { title: 'Total Issues', value: stats?.total_issues || 0, icon: Activity, color: '#ef4444' },
    { title: 'Organizations', value: stats?.organizations_count || 0, icon: Users, color: '#10b981' },
    { title: 'Avg Time (ms)', value: stats?.avg_execution_time || 0, icon: TrendingUp, color: '#f59e0b' },
  ];

  return (
    <div>
      <h1 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '30px' }}>Dashboard</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px', marginBottom: '40px' }}>
        {cards.map((card) => (
          <div key={card.title} style={{ background: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <p style={{ fontSize: '14px', color: '#666', marginBottom: '5px' }}>{card.title}</p>
                <p style={{ fontSize: '28px', fontWeight: 'bold' }}>{card.value}</p>
              </div>
              <card.icon size={40} style={{ color: card.color }} />
            </div>
          </div>
        ))}
      </div>
      <div style={{ background: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '20px' }}>Query Performance</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={stats?.chart_data || []}>
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="queries" fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

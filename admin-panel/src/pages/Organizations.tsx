import { useQuery } from '@tanstack/react-query';
import { organizationsAPI } from '../services/api';
import { Building } from 'lucide-react';

export default function Organizations() {
  const { data: orgs, isLoading } = useQuery({
    queryKey: ['organizations'],
    queryFn: () => organizationsAPI.list().then(r => r.data),
  });

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      <h1 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '30px' }}>Organizations</h1>
      <div style={{ background: 'white', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #eee' }}>
              <th style={{ padding: '15px', textAlign: 'left' }}>ID</th>
              <th style={{ padding: '15px', textAlign: 'left' }}>Name</th>
              <th style={{ padding: '15px', textAlign: 'left' }}>Created</th>
              <th style={{ padding: '15px', textAlign: 'left' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {orgs?.map((org: any) => (
              <tr key={org.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '15px' }}>{org.id}</td>
                <td style={{ padding: '15px' }}>
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <Building size={20} style={{ marginRight: '10px' }} />
                    {org.name}
                  </div>
                </td>
                <td style={{ padding: '15px' }}>{new Date(org.created_at).toLocaleDateString()}</td>
                <td style={{ padding: '15px' }}>
                  <span style={{ padding: '4px 12px', background: '#10b981', color: 'white', borderRadius: '12px', fontSize: '12px' }}>
                    Active
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

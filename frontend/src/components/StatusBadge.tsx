import React from 'react';

interface StatusBadgeProps {
  status: 'pending' | 'analyzed' | 'archived' | 'resolved';
  size?: 'small' | 'medium' | 'large';
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'medium' }) => {
  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'pending':
        return {
          label: 'Pending',
          color: '#f39c12',
          bgColor: '#fef5e7',
          icon: '⏳'
        };
      case 'analyzed':
        return {
          label: 'Analyzed',
          color: '#3498db',
          bgColor: '#ebf5fb',
          icon: '🔍'
        };
      case 'archived':
        return {
          label: 'Archived',
          color: '#95a5a6',
          bgColor: '#f2f3f4',
          icon: '📦'
        };
      case 'resolved':
        return {
          label: 'Resolved',
          color: '#27ae60',
          bgColor: '#eafaf1',
          icon: '✅'
        };
      default:
        return {
          label: status,
          color: '#7f8c8d',
          bgColor: '#ecf0f1',
          icon: '❓'
        };
    }
  };

  const config = getStatusConfig(status);
  
  const sizeStyles = {
    small: {
      fontSize: '11px',
      padding: '2px 6px',
    },
    medium: {
      fontSize: '12px',
      padding: '4px 8px',
    },
    large: {
      fontSize: '14px',
      padding: '6px 12px',
    }
  };

  const style: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    backgroundColor: config.bgColor,
    color: config.color,
    fontWeight: 600,
    borderRadius: '4px',
    border: `1px solid ${config.color}30`,
    ...sizeStyles[size],
    whiteSpace: 'nowrap',
  };

  return (
    <span style={style}>
      <span>{config.icon}</span>
      <span>{config.label}</span>
    </span>
  );
};

export default StatusBadge;

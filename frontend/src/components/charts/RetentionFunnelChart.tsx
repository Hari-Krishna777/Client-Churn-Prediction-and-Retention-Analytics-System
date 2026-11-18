import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

interface RetentionFunnelChartProps {
  statusBreakdown: Record<string, number>;
}

const STATUS_COLORS: Record<string, string> = {
  Pending: '#f59e0b',
  'In Progress': '#38bdf8',
  Contacted: '#6366f1',
  Retained: '#10b981',
  Escalated: '#a855f7',
  Closed: '#94a3b8',
};

export const RetentionFunnelChart: React.FC<RetentionFunnelChartProps> = ({ statusBreakdown }) => {
  const data = Object.entries(statusBreakdown).map(([status, count]) => ({
    status,
    count,
    color: STATUS_COLORS[status] || '#64748b',
  }));

  const total = data.reduce((acc, d) => acc + d.count, 0);

  return (
    <div className="w-full h-64">
      {total === 0 ? (
        <div className="flex items-center justify-center h-full text-sm text-slate-400">
          No retention workflow actions logged yet
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 15, right: 20, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis
              dataKey="status"
              tick={{ fontSize: 11, fill: '#475569' }}
              interval={0}
              angle={-15}
              textAnchor="end"
            />
            <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#64748b' }} />
            <Tooltip
              formatter={(val: any, _: any, item: any) => [
                `${val} actions (${total > 0 ? ((Number(val) / total) * 100).toFixed(1) : 0}%)`,
                item.payload.status,
              ]}
              contentStyle={{
                backgroundColor: '#ffffff',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                fontSize: '12px',
              }}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {data.map((entry, index) => (
                <Cell key={`funnel-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};

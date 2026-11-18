import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

interface RiskPieChartProps {
  distribution: {
    LOW: number;
    MEDIUM: number;
    HIGH: number;
  };
}

const COLORS = {
  LOW: '#10b981', // Emerald
  MEDIUM: '#f59e0b', // Amber
  HIGH: '#f43f5e', // Rose
};

export const RiskPieChart: React.FC<RiskPieChartProps> = ({ distribution }) => {
  const data = [
    { name: 'Low Risk (<30%)', key: 'LOW', value: distribution.LOW || 0, color: COLORS.LOW },
    { name: 'Medium Risk (30-69%)', key: 'MEDIUM', value: distribution.MEDIUM || 0, color: COLORS.MEDIUM },
    { name: 'High Risk (≥70%)', key: 'HIGH', value: distribution.HIGH || 0, color: COLORS.HIGH },
  ].filter((d) => d.value > 0);

  const total = (distribution.LOW || 0) + (distribution.MEDIUM || 0) + (distribution.HIGH || 0);

  return (
    <div className="w-full h-64 relative">
      {total === 0 ? (
        <div className="flex items-center justify-center h-full text-sm text-slate-400">
          No customer risk data available
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={80}
              paddingAngle={4}
              dataKey="value"
            >
              {data.map((entry) => (
                <Cell key={`cell-${entry.key}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: any, name: any) => [
                `${value} customers (${total > 0 ? ((Number(value) / total) * 100).toFixed(1) : 0}%)`,
                name,
              ]}
              contentStyle={{
                backgroundColor: '#ffffff',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                fontSize: '12px',
              }}
            />
            <Legend
              verticalAlign="bottom"
              height={36}
              iconType="circle"
              wrapperStyle={{ fontSize: '12px' }}
            />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};

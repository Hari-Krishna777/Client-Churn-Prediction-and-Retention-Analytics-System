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
  ReferenceLine,
} from 'recharts';
import { ShapExplanationItem } from '../../types';

interface ShapWaterfallChartProps {
  explanations: ShapExplanationItem[];
}

export const ShapWaterfallChart: React.FC<ShapWaterfallChartProps> = ({ explanations }) => {
  const chartData = explanations.map((e) => ({
    feature: e.feature_label || e.feature_name,
    rawFeature: e.feature_name,
    contribution: Number(e.contribution.toFixed(4)),
    direction: e.direction,
    isRisk: e.contribution > 0,
  }));

  return (
    <div className="w-full h-80">
      {chartData.length === 0 ? (
        <div className="flex items-center justify-center h-full text-sm text-slate-400">
          No SHAP feature contributions available
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 10, right: 30, left: 130, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
            <XAxis
              type="number"
              tickFormatter={(val) => (val > 0 ? `+${val}` : `${val}`)}
              tick={{ fontSize: 11, fill: '#64748b' }}
            />
            <YAxis
              type="category"
              dataKey="feature"
              tick={{ fontSize: 11, fill: '#334155' }}
              width={130}
            />
            <ReferenceLine x={0} stroke="#94a3b8" strokeWidth={1.5} />
            <Tooltip
              formatter={(val: any, _: any, item: any) => [
                `${val > 0 ? '+' : ''}${val} impact (${item.payload.isRisk ? 'Increases churn risk' : 'Protective / Retains'})`,
                item.payload.feature,
              ]}
              contentStyle={{
                backgroundColor: '#ffffff',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                fontSize: '12px',
              }}
            />
            <Bar dataKey="contribution" radius={[4, 4, 4, 4]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`shap-${index}`}
                  fill={entry.contribution > 0 ? '#f43f5e' : '#10b981'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};

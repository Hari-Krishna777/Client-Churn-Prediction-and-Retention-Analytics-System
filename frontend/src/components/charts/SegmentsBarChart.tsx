import React, { useState } from 'react';
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
import { SegmentMetric, CustomerSegmentsResponse } from '../../types';

interface SegmentsBarChartProps {
  segmentsData?: CustomerSegmentsResponse | null;
}

export const SegmentsBarChart: React.FC<SegmentsBarChartProps> = ({ segmentsData }) => {
  const [activeTab, setActiveTab] = useState<'highest' | 'contract' | 'internet' | 'payment'>('highest');

  let list: SegmentMetric[] = [];
  if (segmentsData) {
    if (activeTab === 'highest') {
      list = segmentsData.highest_risk_segments || segmentsData.by_contract || [];
    } else if (activeTab === 'contract') {
      list = segmentsData.by_contract || [];
    } else if (activeTab === 'internet') {
      list = segmentsData.by_internet_service || [];
    } else if (activeTab === 'payment') {
      list = segmentsData.by_payment_method || [];
    }
  }

  const chartData = (list || []).map((s) => ({
    name: s.segment_name,
    churnRate: s.churn_rate_percentage,
    churnCount: s.churn_count,
    total: s.customer_count,
    risk: s.dominant_risk_category,
    avgProb: s.avg_churn_probability,
  }));

  const getColor = (risk: string) => {
    const r = (risk || '').toUpperCase();
    if (r === 'HIGH') return '#f43f5e';
    if (r === 'MEDIUM') return '#f59e0b';
    return '#10b981';
  };

  return (
    <div className="space-y-3">
      {/* Category Tabs */}
      <div className="flex items-center gap-1.5 pb-1 border-b border-slate-100 overflow-x-auto text-xs">
        <button
          onClick={() => setActiveTab('highest')}
          className={`px-2.5 py-1 rounded-md font-medium transition ${
            activeTab === 'highest'
              ? 'bg-indigo-50 text-indigo-700 border border-indigo-200'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          Highest Risk Segments
        </button>
        <button
          onClick={() => setActiveTab('contract')}
          className={`px-2.5 py-1 rounded-md font-medium transition ${
            activeTab === 'contract'
              ? 'bg-indigo-50 text-indigo-700 border border-indigo-200'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          By Contract
        </button>
        <button
          onClick={() => setActiveTab('internet')}
          className={`px-2.5 py-1 rounded-md font-medium transition ${
            activeTab === 'internet'
              ? 'bg-indigo-50 text-indigo-700 border border-indigo-200'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          By Internet
        </button>
        <button
          onClick={() => setActiveTab('payment')}
          className={`px-2.5 py-1 rounded-md font-medium transition ${
            activeTab === 'payment'
              ? 'bg-indigo-50 text-indigo-700 border border-indigo-200'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          By Payment
        </button>
      </div>

      <div className="w-full h-64">
        {chartData.length === 0 ? (
          <div className="flex items-center justify-center h-full text-sm text-slate-400">
            No segment data available
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 110, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
              <XAxis
                type="number"
                domain={[0, 100]}
                tickFormatter={(val) => `${val}%`}
                tick={{ fontSize: 11, fill: '#64748b' }}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fontSize: 11, fill: '#334155' }}
                width={110}
              />
              <Tooltip
                formatter={(value: any, _: any, item: any) => [
                  `${Number(value).toFixed(1)}% churn rate (${item.payload.churnCount}/${item.payload.total} customers)`,
                  'Churn Rate',
                ]}
                contentStyle={{
                  backgroundColor: '#ffffff',
                  borderRadius: '8px',
                  border: '1px solid #e2e8f0',
                  boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                  fontSize: '12px',
                }}
              />
              <Bar dataKey="churnRate" radius={[0, 4, 4, 0]}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={getColor(entry.risk)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

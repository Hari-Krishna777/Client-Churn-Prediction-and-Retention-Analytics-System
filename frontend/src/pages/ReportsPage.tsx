import React, { useState, useEffect } from 'react';
import { batchApi } from '../api/batch';
import { analyticsApi } from '../api/analytics';
import { customersApi } from '../api/customers';
import { retentionApi } from '../api/retention';
import { BatchJobItem, AnalyticsOverview, RecommendationSummaryResponse } from '../types';
import { Card } from '../components/common/Card';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useNotification } from '../context/NotificationContext';
import {
  FileSpreadsheet,
  Download,
  FileText,
  ShieldAlert,
  Award,
  Users,
  CheckCircle2,
  Calendar,
  Layers,
  Sparkles,
} from 'lucide-react';

export const ReportsPage: React.FC = () => {
  const { notify } = useNotification();
  const [jobs, setJobs] = useState<BatchJobItem[]>([]);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [recsSummary, setRecsSummary] = useState<RecommendationSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      batchApi.listJobs(),
      analyticsApi.getOverview(),
      analyticsApi.getRecommendationsSummary(),
    ])
      .then(([jobsData, overviewData, recsData]) => {
        setJobs(jobsData);
        setOverview(overviewData);
        setRecsSummary(recsData);
      })
      .catch((err) => console.error('Failed to load reports data', err))
      .finally(() => setLoading(false));
  }, []);

  // Helper to trigger browser CSV download from arbitrary data
  const downloadCsvFile = (content: string, filename: string) => {
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // 1. Export High Risk Customers CSV
  const handleExportHighRiskCustomers = async () => {
    setExporting('high_risk');
    try {
      notify('info', 'Compiling High-Risk customer report...');
      const res = await customersApi.listCustomers({ risk_category: 'HIGH', limit: 200 });

      const headers = [
        'CustomerID',
        'ChurnProbability',
        'RiskCategory',
        'ActionUrgency',
        'Contract',
        'Tenure',
        'MonthlyCharges',
        'TotalCharges',
        'PaymentMethod',
      ];

      const rows = res.customers.map((c) => [
        c.customer_id,
        (c.churn_probability * 100).toFixed(2) + '%',
        c.risk_category,
        c.action_urgency,
        `"${c.contract}"`,
        c.tenure,
        c.monthly_charges,
        c.total_charges,
        `"${c.payment_method}"`,
      ]);

      const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
      downloadCsvFile(csvContent, `churniq_high_risk_customers_${new Date().toISOString().slice(0, 10)}.csv`);
      notify('success', `Exported ${res.customers.length} high-risk customer profiles!`);
    } catch (err: any) {
      notify('error', err.message || 'Failed to export customer report.');
    } finally {
      setExporting(null);
    }
  };

  // 2. Export Retention Actions CSV
  const handleExportRetentionReport = async () => {
    setExporting('retention');
    try {
      notify('info', 'Generating retention strategy actions CSV...');
      const res = await retentionApi.listActions({ limit: 200 });

      const headers = [
        'CustomerID',
        'Urgency',
        'Priority',
        'Status',
        'Reason',
        'SuggestedAction',
        'SupportingSHAP',
        'Notes',
      ];

      const rows = res.actions.map((a) => [
        a.customer_id,
        a.action_urgency,
        a.priority,
        a.status,
        `"${a.recommendation_reason.replace(/"/g, '""')}"`,
        `"${a.suggested_action.replace(/"/g, '""')}"`,
        a.supporting_shap_contribution ?? '',
        `"${(a.notes || '').replace(/"/g, '""')}"`,
      ]);

      const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
      downloadCsvFile(csvContent, `churniq_retention_actions_${new Date().toISOString().slice(0, 10)}.csv`);
      notify('success', `Exported ${res.actions.length} retention actions report!`);
    } catch (err: any) {
      notify('error', err.message || 'Failed to export retention report.');
    } finally {
      setExporting(null);
    }
  };

  if (loading) {
    return <LoadingSpinner size="lg" label="Compiling executive intelligence reports..." className="h-96" />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Reports & Analytical Exports</h1>
        <p className="text-sm text-slate-500">
          Download batch prediction runs, generate executive risk summaries, and export custom retention action lists to CSV.
        </p>
      </div>

      {/* Quick Export Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* High Risk Customer Report */}
        <Card
          title="High Risk Customer Export"
          subtitle="All accounts with churn probability ≥ 70%"
          icon={<ShieldAlert className="w-4 h-4 text-rose-600" />}
        >
          <div className="space-y-3">
            <p className="text-xs text-slate-600 leading-relaxed">
              Targeted list of accounts flagged for urgent retention contact with contract details and monthly spend.
            </p>
            <div className="flex items-center justify-between text-xs font-semibold py-2 border-y border-slate-100">
              <span className="text-slate-500">Identified Accounts</span>
              <span className="text-rose-600 font-bold">{overview?.risk_distribution.HIGH || 0} customers</span>
            </div>
            <button
              onClick={handleExportHighRiskCustomers}
              disabled={exporting === 'high_risk'}
              className="w-full py-2 px-3 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold shadow-xs transition flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <Download className="w-3.5 h-3.5" />
              <span>{exporting === 'high_risk' ? 'Exporting...' : 'Export High Risk CSV'}</span>
            </button>
          </div>
        </Card>

        {/* Retention Action Plan Report */}
        <Card
          title="Retention Actions Report"
          subtitle="Active interventions and follow-up status"
          icon={<Award className="w-4 h-4 text-indigo-600" />}
        >
          <div className="space-y-3">
            <p className="text-xs text-slate-600 leading-relaxed">
              Complete log of recommended retention strategies, rule justifications, supporting SHAP values, and logged notes.
            </p>
            <div className="flex items-center justify-between text-xs font-semibold py-2 border-y border-slate-100">
              <span className="text-slate-500">Total Interventions</span>
              <span className="text-indigo-600 font-bold">
                {recsSummary?.total_recommendations || 0} recommendations
              </span>
            </div>
            <button
              onClick={handleExportRetentionReport}
              disabled={exporting === 'retention'}
              className="w-full py-2 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <Download className="w-3.5 h-3.5" />
              <span>{exporting === 'retention' ? 'Exporting...' : 'Export Actions CSV'}</span>
            </button>
          </div>
        </Card>

        {/* Executive Portfolio Health Summary */}
        <Card
          title="Executive Risk Snapshot"
          subtitle="Core KPIs and risk breakdown"
          icon={<FileText className="w-4 h-4 text-slate-700" />}
        >
          <div className="space-y-3">
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Total Scored Base</span>
                <span className="font-bold text-slate-800">{overview?.total_customers || 0}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Projected Churn Rate</span>
                <span className="font-bold text-rose-600">{overview?.churn_rate_percentage.toFixed(1)}%</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Mean Churn Probability</span>
                <span className="font-bold font-mono text-slate-800">
                  {overview?.average_churn_probability ? (overview.average_churn_probability * 100).toFixed(1) + '%' : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Decision Threshold</span>
                <span className="font-mono font-semibold text-indigo-600">0.40</span>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Batch Processing Output Archives Table */}
      <Card
        title="Batch Predictions Archive & Raw CSV Downloads"
        subtitle="Download full machine learning prediction outputs directly generated by FastAPI backend"
        icon={<FileSpreadsheet className="w-4 h-4 text-emerald-600" />}
      >
        {jobs.length === 0 ? (
          <div className="text-center py-8 text-xs text-slate-400">
            No batch jobs recorded yet. Upload a dataset in Dataset Upload to generate batch reports.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-500 font-semibold uppercase text-[11px] border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3">Batch File</th>
                  <th className="px-4 py-3">Job ID</th>
                  <th className="px-4 py-3">Processed Records</th>
                  <th className="px-4 py-3">Risk Distribution</th>
                  <th className="px-4 py-3">Completed At</th>
                  <th className="px-4 py-3 text-right">Download</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {jobs.map((job) => (
                  <tr key={job.job_id} className="hover:bg-slate-50 transition">
                    <td className="px-4 py-3 font-semibold text-slate-800 flex items-center gap-2">
                      <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
                      {job.filename}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-500 text-[11px]">{job.job_id}</td>
                    <td className="px-4 py-3 font-semibold text-emerald-700">
                      {job.successfully_processed} predictions
                    </td>
                    <td className="px-4 py-3 text-[11px]">
                      {job.risk_distribution ? (
                        <div className="flex items-center gap-1.5">
                          <span className="text-emerald-700 font-medium">L: {job.risk_distribution.LOW}</span>
                          <span className="text-slate-300">•</span>
                          <span className="text-amber-700 font-medium">M: {job.risk_distribution.MEDIUM}</span>
                          <span className="text-slate-300">•</span>
                          <span className="text-rose-700 font-medium">H: {job.risk_distribution.HIGH}</span>
                        </div>
                      ) : (
                        <span className="text-slate-400">N/A</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      {job.completed_at ? new Date(job.completed_at).toLocaleString() : 'Recent'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <a
                        href={`/api/batch/${job.job_id}/download`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-800 font-semibold text-xs transition border border-emerald-200"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Download CSV</span>
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};

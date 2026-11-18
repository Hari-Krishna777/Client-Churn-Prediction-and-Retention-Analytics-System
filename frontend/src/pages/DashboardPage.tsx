import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { analyticsApi } from '../api/analytics';
import {
  AnalyticsOverview,
  CustomerSegmentsResponse,
  ChurnFactorsResponse,
  RecommendationSummaryResponse,
} from '../types';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { RiskPieChart } from '../components/charts/RiskPieChart';
import { SegmentsBarChart } from '../components/charts/SegmentsBarChart';
import {
  Users,
  UserX,
  TrendingDown,
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  Sparkles,
  RefreshCw,
  Award,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [segments, setSegments] = useState<CustomerSegmentsResponse | null>(null);
  const [factors, setFactors] = useState<ChurnFactorsResponse | null>(null);
  const [recsSummary, setRecsSummary] = useState<RecommendationSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    setError(null);
    try {
      const [overviewData, segmentsData, factorsData, recsData] = await Promise.all([
        analyticsApi.getOverview().catch((e) => {
          console.warn('Overview error', e);
          return null;
        }),
        analyticsApi.getSegments().catch((e) => {
          console.warn('Segments error', e);
          return null;
        }),
        analyticsApi.getChurnFactors(undefined, 5).catch((e) => {
          console.warn('Churn factors error', e);
          return null;
        }),
        analyticsApi.getRecommendationsSummary().catch((e) => {
          console.warn('Recommendations error', e);
          return null;
        }),
      ]);

      if (!overviewData && !segmentsData) {
        setError('Unable to connect to the ChurnIQ backend API. Please make sure the FastAPI server is running on port 8000.');
      } else {
        setOverview(overviewData);
        setSegments(segmentsData);
        setFactors(factorsData);
        setRecsSummary(recsData);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load dashboard data.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchDashboardData();
  };

  if (loading) {
    return <LoadingSpinner size="lg" label="Loading ChurnIQ Executive Dashboard..." className="h-96" />;
  }

  if (error) {
    return (
      <div className="bg-white p-8 rounded-2xl border border-rose-200 text-center max-w-lg mx-auto my-12 space-y-4 shadow-sm">
        <div className="w-12 h-12 mx-auto rounded-full bg-rose-50 text-rose-600 flex items-center justify-center">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <h3 className="text-lg font-bold text-slate-800">Dashboard Connection Notice</h3>
        <p className="text-xs text-slate-500 leading-relaxed">{error}</p>
        <div className="pt-2">
          <button
            onClick={fetchDashboardData}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Retry Connection
          </button>
        </div>
      </div>
    );
  }

  const riskDist = overview?.risk_distribution || { LOW: 0, MEDIUM: 0, HIGH: 0 };
  const highRiskCount = riskDist.HIGH || 0;
  const mediumRiskCount = riskDist.MEDIUM || 0;
  const lowRiskCount = riskDist.LOW || 0;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Main Dashboard</h1>
          <p className="text-sm text-slate-500">
            Real-time customer portfolio health, churn probability distribution, and predictive retention insights.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-medium text-slate-600 hover:bg-slate-50 transition shadow-xs disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <Link
            to="/upload"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-sm transition"
          >
            Upload New Batch CSV
          </Link>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Customers */}
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Customers</span>
            <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-slate-600">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-slate-900">{overview?.total_customers?.toLocaleString() || 0}</span>
            <span className="text-xs text-slate-400">active profiles</span>
          </div>
          <div className="mt-2 text-xs text-slate-500 flex items-center gap-1">
            <span>Threshold:</span>
            <strong className="text-slate-700 font-mono">0.40</strong>
          </div>
          <div className="absolute top-0 right-0 w-16 h-16 bg-slate-500/5 rounded-full -mr-4 -mt-4 pointer-events-none" />
        </div>

        {/* Predicted Churners */}
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Predicted Churners</span>
            <div className="w-8 h-8 rounded-lg bg-rose-50 flex items-center justify-center text-rose-600">
              <UserX className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-rose-600">{overview?.predicted_churners?.toLocaleString() || 0}</span>
            <span className="text-xs text-rose-500/80 font-medium">at-risk accounts</span>
          </div>
          <div className="mt-2 text-xs text-slate-500 flex items-center gap-1">
            <span>Retained:</span>
            <strong className="text-emerald-600 font-semibold">{overview?.predicted_retained || 0} safe</strong>
          </div>
          <div className="absolute top-0 right-0 w-16 h-16 bg-rose-500/5 rounded-full -mr-4 -mt-4 pointer-events-none" />
        </div>

        {/* Churn Percentage */}
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Churn Percentage</span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center text-amber-600">
              <TrendingDown className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-slate-900">{overview?.churn_rate_percentage?.toFixed(1) || '0.0'}%</span>
            <span className="text-xs text-slate-400">projected loss</span>
          </div>
          <div className="mt-2 text-xs text-slate-500 flex items-center gap-1">
            <span>Avg Probability:</span>
            <strong className="text-slate-700 font-mono">
              {overview?.average_churn_probability ? (overview.average_churn_probability * 100).toFixed(1) + '%' : 'N/A'}
            </strong>
          </div>
          <div className="absolute top-0 right-0 w-16 h-16 bg-amber-500/5 rounded-full -mr-4 -mt-4 pointer-events-none" />
        </div>

        {/* High Risk Urgency */}
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">High Risk Urgency</span>
            <div className="w-8 h-8 rounded-lg bg-red-100 flex items-center justify-center text-red-700">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-red-600">{highRiskCount}</span>
            <Badge label="URGENT ACTION" variant="urgency" size="sm" />
          </div>
          <div className="mt-2 text-xs text-slate-500">
            Probability <strong className="text-red-700">≥ 70%</strong> requires priority outreach
          </div>
          <div className="absolute top-0 right-0 w-16 h-16 bg-red-500/5 rounded-full -mr-4 -mt-4 pointer-events-none" />
        </div>
      </div>

      {/* Charts Section: Risk Distribution & Segment Churn Rates */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Risk Distribution Card */}
        <Card
          title="Customer Risk Distribution"
          subtitle="Proportion of accounts in Low (<30%), Medium (30-69%), and High (≥70%) tiers"
          icon={<ShieldAlert className="w-4 h-4 text-indigo-600" />}
          className="lg:col-span-1"
        >
          <RiskPieChart
            distribution={{
              LOW: lowRiskCount,
              MEDIUM: mediumRiskCount,
              HIGH: highRiskCount,
            }}
          />

          <div className="grid grid-cols-3 gap-2 mt-4 pt-4 border-t border-slate-100 text-center">
            <div className="p-2 rounded-lg bg-emerald-50/70 border border-emerald-100">
              <div className="text-[10px] font-semibold text-emerald-800 uppercase">Low Risk</div>
              <div className="text-base font-bold text-emerald-700">{lowRiskCount}</div>
            </div>
            <div className="p-2 rounded-lg bg-amber-50/70 border border-amber-100">
              <div className="text-[10px] font-semibold text-amber-800 uppercase">Medium</div>
              <div className="text-base font-bold text-amber-700">{mediumRiskCount}</div>
            </div>
            <div className="p-2 rounded-lg bg-rose-50/70 border border-rose-100">
              <div className="text-[10px] font-semibold text-rose-800 uppercase">High Risk</div>
              <div className="text-base font-bold text-rose-700">{highRiskCount}</div>
            </div>
          </div>
        </Card>

        {/* Segments Churn Rates */}
        <Card
          title="Segment Churn Rates"
          subtitle="Highest churn percentages grouped by contract length, tenure, and services"
          icon={<Users className="w-4 h-4 text-indigo-600" />}
          action={
            <Link to="/customers" className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1">
              Explore Segments <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          }
          className="lg:col-span-2"
        >
          <SegmentsBarChart segmentsData={segments} />
        </Card>
      </div>

      {/* Lower Section: SHAP Churn Drivers & Retention Recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Global SHAP Churn Drivers */}
        <Card
          title="Top Churn Drivers (SHAP Explainability)"
          subtitle="Machine learning feature importance driving churn likelihood across the portfolio"
          icon={<Sparkles className="w-4 h-4 text-violet-600" />}
        >
          <div className="space-y-3">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Primary Churn Catalysts (Increases Risk)
            </div>
            <div className="space-y-2">
              {(factors?.top_churn_drivers || []).slice(0, 4).map((f, i) => (
                <div key={i} className="flex items-center justify-between p-2.5 rounded-lg bg-rose-50/50 border border-rose-100/70">
                  <div className="flex items-center space-x-2.5">
                    <span className="w-5 h-5 rounded-full bg-rose-100 text-rose-700 text-xs font-bold flex items-center justify-center">
                      {i + 1}
                    </span>
                    <div>
                      <div className="text-xs font-semibold text-slate-800">{f.factor}</div>
                      <div className="text-[10px] font-mono text-slate-400">{f.feature_name}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-mono font-bold text-rose-600">
                      +{typeof f.impact_score === 'number' ? f.impact_score.toFixed(3) : f.impact_score}
                    </span>
                    <div className="text-[10px] text-rose-500">increases churn</div>
                  </div>
                </div>
              ))}
            </div>

            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider pt-2">
              Key Retention Drivers (Protective Factors)
            </div>
            <div className="space-y-2">
              {(factors?.top_protective_factors || []).slice(0, 2).map((f, i) => (
                <div key={i} className="flex items-center justify-between p-2.5 rounded-lg bg-emerald-50/50 border border-emerald-100/70">
                  <div className="flex items-center space-x-2.5">
                    <span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 text-xs font-bold flex items-center justify-center">
                      {i + 1}
                    </span>
                    <div>
                      <div className="text-xs font-semibold text-slate-800">{f.factor}</div>
                      <div className="text-[10px] font-mono text-slate-400">{f.feature_name}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-mono font-bold text-emerald-600">
                      {typeof f.impact_score === 'number' ? f.impact_score.toFixed(3) : f.impact_score}
                    </span>
                    <div className="text-[10px] text-emerald-600">retains customer</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Card>

        {/* Priority Retention Actions */}
        <Card
          title="Recommended Retention Interventions"
          subtitle="Top automated strategy recommendations prioritized by affected churners"
          icon={<Award className="w-4 h-4 text-indigo-600" />}
          action={
            <Link to="/retention" className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1">
              Action Tracker <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          }
        >
          <div className="space-y-3">
            {(recsSummary?.top_suggested_actions || []).slice(0, 4).map((r, i) => (
              <div key={i} className="p-3 rounded-xl border border-slate-200/80 bg-slate-50/50 hover:bg-slate-50 transition">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-bold text-slate-800">{r.reason}</span>
                      <Badge label={r.priority} size="sm" />
                    </div>
                    <p className="text-xs text-slate-600 leading-snug">{r.action}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="text-xs font-bold text-indigo-600">{r.customer_count} accounts</div>
                    <div className="text-[10px] text-slate-400">target outreach</div>
                  </div>
                </div>
              </div>
            ))}

            <div className="pt-2 text-center">
              <Link
                to="/retention"
                className="inline-flex items-center justify-center w-full py-2 px-3 rounded-lg border border-indigo-200 text-xs font-semibold text-indigo-700 hover:bg-indigo-50 transition"
              >
                View Full Retention Operations Suite ({recsSummary?.total_recommendations || 0} Total Recommendations)
              </Link>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};

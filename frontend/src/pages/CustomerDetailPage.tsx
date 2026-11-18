import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { customersApi } from '../api/customers';
import { CustomerDetailsResponse } from '../types';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ShapWaterfallChart } from '../components/charts/ShapWaterfallChart';
import {
  ArrowLeft,
  User,
  ShieldAlert,
  Sparkles,
  Award,
  Clock,
  CheckCircle2,
  AlertTriangle,
  CreditCard,
  Wifi,
  Phone,
  FileText,
} from 'lucide-react';

export const CustomerDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<CustomerDetailsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    customersApi
      .getCustomerDetails(id)
      .then((res) => {
        setData(res);
        setError(null);
      })
      .catch((err) => {
        setError(err.message || 'Customer not found.');
      })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return <LoadingSpinner size="lg" label="Computing SHAP feature contributions and customer profile..." className="h-96" />;
  }

  if (error || !data) {
    return (
      <div className="bg-white p-8 rounded-xl border border-rose-200 text-center max-w-lg mx-auto my-12 space-y-4">
        <div className="w-12 h-12 mx-auto rounded-full bg-rose-50 text-rose-600 flex items-center justify-center">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <h3 className="text-lg font-bold text-slate-800">Customer Lookup Failed</h3>
        <p className="text-xs text-slate-500">{error || 'Could not find details for requested customer ID.'}</p>
        <Link
          to="/customers"
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 text-white text-xs font-semibold"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Customer List
        </Link>
      </div>
    );
  }

  const { customer, prediction, shap_explanations, recommendations, history } = data;
  const prob = prediction.churn_probability;
  const probPercent = (prob * 100).toFixed(1);

  return (
    <div className="space-y-6">
      {/* Top Navigation & Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link
          to="/customers"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-indigo-600 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Customer Analytics
        </Link>

        <span className="text-xs font-mono text-slate-400">
          Created: {customer.created_at ? new Date(customer.created_at).toLocaleDateString() : 'N/A'}
        </span>
      </div>

      {/* Main Hero Header Card */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs bg-gradient-to-r from-slate-50 via-white to-indigo-50/20">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-center space-x-4">
            <div className="w-14 h-14 rounded-2xl bg-indigo-600 text-white flex items-center justify-center font-mono font-bold text-lg shadow-md shadow-indigo-600/20">
              {customer.customer_id.substring(0, 4)}
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-2xl font-bold text-slate-900 font-mono">{customer.customer_id}</h1>
                <Badge label={prediction.risk_category} variant="risk" size="md" />
                <Badge label={prediction.action_urgency} variant="urgency" size="md" />
              </div>
              <p className="text-xs text-slate-500 mt-1 flex items-center gap-3">
                <span>Contract: <strong className="text-slate-700">{customer.contract}</strong></span>
                <span>•</span>
                <span>Tenure: <strong className="text-slate-700">{customer.tenure} months</strong></span>
                <span>•</span>
                <span>Monthly: <strong className="text-slate-700">${Number(customer.monthly_charges).toFixed(2)}</strong></span>
              </p>
            </div>
          </div>

          {/* Churn Probability Gauge Box */}
          <div className="flex items-center gap-4 p-4 rounded-xl bg-white border border-slate-200/80 shadow-xs">
            <div className="text-right">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Churn Probability</div>
              <div
                className={`text-3xl font-extrabold font-mono ${
                  prob >= 0.7 ? 'text-rose-600' : prob >= 0.3 ? 'text-amber-600' : 'text-emerald-600'
                }`}
              >
                {probPercent}%
              </div>
              <div className="text-[10px] text-slate-400">Decision Threshold: 0.40</div>
            </div>

            <div className="w-12 h-12 rounded-xl flex items-center justify-center bg-slate-50 border border-slate-100">
              <ShieldAlert
                className={`w-6 h-6 ${
                  prob >= 0.7 ? 'text-rose-600' : prob >= 0.3 ? 'text-amber-500' : 'text-emerald-500'
                }`}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Grid: Demographics, Account Profile, and Key Churn Drivers */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Customer Demographics & Contract */}
        <Card title="Customer Profile & Subscription" icon={<User className="w-4 h-4 text-indigo-600" />}>
          <div className="space-y-3 text-xs">
            <div className="flex justify-between py-1.5 border-b border-slate-100">
              <span className="text-slate-500">Gender</span>
              <span className="font-semibold text-slate-800">{customer.gender || 'Not specified'}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-100">
              <span className="text-slate-500">Senior Citizen</span>
              <span className="font-semibold text-slate-800">{customer.senior_citizen ? 'Yes' : 'No'}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-100">
              <span className="text-slate-500">Partner & Dependents</span>
              <span className="font-semibold text-slate-800">
                Partner: {customer.partner || 'No'}, Dependents: {customer.dependents || 'No'}
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-100">
              <span className="text-slate-500">Internet Service</span>
              <span className="font-semibold text-slate-800 flex items-center gap-1">
                <Wifi className="w-3 h-3 text-slate-400" />
                {customer.internet_service || 'None'}
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-100">
              <span className="text-slate-500">Phone Service</span>
              <span className="font-semibold text-slate-800 flex items-center gap-1">
                <Phone className="w-3 h-3 text-slate-400" />
                {customer.phone_service} ({customer.multiple_lines || 'Single line'})
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-100">
              <span className="text-slate-500">Payment Method</span>
              <span className="font-semibold text-slate-800 flex items-center gap-1">
                <CreditCard className="w-3 h-3 text-slate-400" />
                {customer.payment_method || 'Electronic check'}
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-100">
              <span className="text-slate-500">Paperless Billing</span>
              <span className="font-semibold text-slate-800">{customer.paperless_billing || 'Yes'}</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-slate-500">Total Lifetime Charges</span>
              <span className="font-semibold font-mono text-slate-800">
                ${Number(customer.total_charges).toFixed(2)}
              </span>
            </div>
          </div>
        </Card>

        {/* Top Contributing Churn & Protective Factors */}
        <Card
          title="Top Contributing Factors"
          subtitle="Key indicators influencing the AI churn prediction"
          icon={<Sparkles className="w-4 h-4 text-violet-600" />}
          className="lg:col-span-2"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Risk Drivers */}
            <div className="p-3.5 rounded-xl bg-rose-50/60 border border-rose-100 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-bold text-rose-800 uppercase tracking-wider">
                <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                Top Churn Catalysts (Increases Risk)
              </div>
              <ul className="space-y-1.5">
                {prediction.top_churn_factors.map((f, i) => (
                  <li key={i} className="text-xs text-rose-900 flex items-start gap-2">
                    <span className="w-4 h-4 rounded-full bg-rose-200 text-rose-800 text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Protective Factors */}
            <div className="p-3.5 rounded-xl bg-emerald-50/60 border border-emerald-100 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-800 uppercase tracking-wider">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                Protective Retention Factors
              </div>
              <ul className="space-y-1.5">
                {prediction.top_protective_factors.map((f, i) => (
                  <li key={i} className="text-xs text-emerald-900 flex items-start gap-2">
                    <span className="w-4 h-4 rounded-full bg-emerald-200 text-emerald-800 text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Model: XGBoost Classifier Pipeline</span>
            <span className="font-mono text-indigo-600 font-medium">Explainable AI (TreeSHAP)</span>
          </div>
        </Card>
      </div>

      {/* SHAP Feature Contribution Waterfall Bar Chart */}
      <Card
        title="SHAP Feature Contribution Waterfall"
        subtitle="Decomposition of features pushing probability up (red) vs pulling down (green)"
        icon={<Sparkles className="w-4 h-4 text-indigo-600" />}
      >
        <ShapWaterfallChart explanations={shap_explanations} />
      </Card>

      {/* Retention Recommendations Grid */}
      <Card
        title="Automated Retention Strategies"
        subtitle="Actionable rule-based and SHAP-supported interventions"
        icon={<Award className="w-4 h-4 text-indigo-600" />}
      >
        {recommendations.length === 0 ? (
          <div className="text-center py-6 text-xs text-slate-400">
            No specific retention actions required for this account.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {recommendations.map((rec, i) => (
              <div
                key={rec.id || i}
                className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800">{rec.recommendation_reason}</span>
                  <div className="flex items-center gap-1.5">
                    <Badge label={rec.priority} size="sm" />
                    <Badge label={rec.action_urgency} variant="urgency" size="sm" />
                  </div>
                </div>

                <p className="text-xs text-slate-600 leading-snug">{rec.suggested_action}</p>

                {rec.supporting_shap_contribution !== undefined && rec.supporting_shap_contribution !== null && (
                  <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between text-[11px] text-slate-500">
                    <span className="font-mono text-slate-400 truncate max-w-xs">{rec.shap_feature}</span>
                    <span className="font-mono font-bold text-indigo-600">
                      SHAP: +{Number(rec.supporting_shap_contribution).toFixed(3)}
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Temporal History Snapshots */}
      {history.length > 0 && (
        <Card
          title="Historical Prediction Snapshots"
          subtitle="Prediction timeline tracking churn probability changes over time"
          icon={<Clock className="w-4 h-4 text-slate-600" />}
        >
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-500 font-semibold uppercase text-[11px]">
                <tr>
                  <th className="px-3 py-2">Timestamp</th>
                  <th className="px-3 py-2">Probability</th>
                  <th className="px-3 py-2">Prediction</th>
                  <th className="px-3 py-2">Risk Category</th>
                  <th className="px-3 py-2">Urgency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {history.map((h, i) => (
                  <tr key={h.prediction_id || i} className="hover:bg-slate-50">
                    <td className="px-3 py-2 font-mono text-slate-500">
                      {h.created_at ? new Date(h.created_at).toLocaleString() : 'Recent'}
                    </td>
                    <td className="px-3 py-2 font-mono font-bold text-slate-800">
                      {(h.churn_probability * 100).toFixed(1)}%
                    </td>
                    <td className="px-3 py-2">
                      <span className={h.churn_prediction === 'Yes' ? 'text-rose-600 font-semibold' : 'text-emerald-600'}>
                        {h.churn_prediction}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <Badge label={h.risk_category} variant="risk" />
                    </td>
                    <td className="px-3 py-2">
                      <Badge label={h.action_urgency} variant="urgency" size="sm" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
};

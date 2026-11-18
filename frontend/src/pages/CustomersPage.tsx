import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { customersApi, CustomerFilterParams } from '../api/customers';
import { CustomerListItem } from '../types';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Pagination } from '../components/common/Pagination';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { EmptyState } from '../components/common/EmptyState';
import {
  Users,
  Search,
  Filter,
  ArrowUpDown,
  ExternalLink,
  ShieldAlert,
  Sparkles,
  RefreshCw,
} from 'lucide-react';

export const CustomersPage: React.FC = () => {
  const [customers, setCustomers] = useState<CustomerListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // Filters and pagination state
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [contractFilter, setContractFilter] = useState('');
  const [internetFilter, setInternetFilter] = useState('');
  const [sortBy, setSortBy] = useState('probability_desc');
  const [limit, setLimit] = useState(25);
  const [offset, setOffset] = useState(0);

  // Debounce search input
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(search);
      setOffset(0);
    }, 300);
    return () => clearTimeout(handler);
  }, [search]);

  const fetchCustomers = async () => {
    setLoading(true);
    try {
      const params: CustomerFilterParams = {
        search: debouncedSearch || undefined,
        risk_category: riskFilter || undefined,
        contract: contractFilter || undefined,
        internet_service: internetFilter || undefined,
        sort_by: sortBy,
        limit,
        offset,
      };

      const res = await customersApi.listCustomers(params);
      setCustomers(res.customers);
      setTotal(res.total);
    } catch (err) {
      console.error('Failed to load customers', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomers();
  }, [debouncedSearch, riskFilter, contractFilter, internetFilter, sortBy, limit, offset]);

  const handleResetFilters = () => {
    setSearch('');
    setRiskFilter('');
    setContractFilter('');
    setInternetFilter('');
    setSortBy('probability_desc');
    setOffset(0);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Customer Analytics & Risk Explorer</h1>
          <p className="text-sm text-slate-500">
            Interactive customer intelligence: filter by predictive risk category, contract segment, and sort by churn probability.
          </p>
        </div>

        <button
          onClick={fetchCustomers}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-medium text-slate-600 hover:bg-slate-50 transition shadow-xs"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh Records
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Search Input */}
          <div className="lg:col-span-2 relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by customer ID or payment method..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-slate-200 text-xs bg-slate-50/50 text-slate-800 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:bg-white transition"
            />
          </div>

          {/* Risk Filter */}
          <div>
            <select
              value={riskFilter}
              onChange={(e) => {
                setRiskFilter(e.target.value);
                setOffset(0);
              }}
              className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs bg-slate-50/50 text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="">All Risk Tiers</option>
              <option value="HIGH">High Risk (≥ 70%)</option>
              <option value="MEDIUM">Medium Risk (30-69%)</option>
              <option value="LOW">Low Risk (&lt; 30%)</option>
            </select>
          </div>

          {/* Contract Segment */}
          <div>
            <select
              value={contractFilter}
              onChange={(e) => {
                setContractFilter(e.target.value);
                setOffset(0);
              }}
              className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs bg-slate-50/50 text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="">All Contracts</option>
              <option value="Month-to-month">Month-to-month</option>
              <option value="One year">One year</option>
              <option value="Two year">Two year</option>
            </select>
          </div>

          {/* Sort By */}
          <div>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs bg-slate-50/50 text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="probability_desc">Churn Probability (High → Low)</option>
              <option value="probability_asc">Churn Probability (Low → High)</option>
              <option value="tenure_desc">Tenure (Longest first)</option>
              <option value="charges_desc">Monthly Spend (Highest first)</option>
            </select>
          </div>
        </div>

        {/* Quick Filter Badges */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-medium">Quick Segment:</span>
            <button
              onClick={() => {
                setRiskFilter('HIGH');
                setOffset(0);
              }}
              className={`px-2 py-0.5 rounded text-[11px] font-medium border transition ${
                riskFilter === 'HIGH'
                  ? 'bg-rose-100 text-rose-800 border-rose-300 font-bold'
                  : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
              }`}
            >
              High Risk Accounts
            </button>
            <button
              onClick={() => {
                setContractFilter('Month-to-month');
                setOffset(0);
              }}
              className={`px-2 py-0.5 rounded text-[11px] font-medium border transition ${
                contractFilter === 'Month-to-month'
                  ? 'bg-indigo-100 text-indigo-800 border-indigo-300 font-bold'
                  : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
              }`}
            >
              Month-to-Month
            </button>
          </div>

          {(riskFilter || contractFilter || internetFilter || search) && (
            <button
              onClick={handleResetFilters}
              className="text-xs text-rose-600 hover:text-rose-700 font-medium"
            >
              Reset All Filters
            </button>
          )}
        </div>
      </div>

      {/* Customer Listing Table */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        {loading ? (
          <LoadingSpinner size="lg" label="Querying customer intelligence database..." className="h-64" />
        ) : customers.length === 0 ? (
          <EmptyState
            title="No customers match current filter criteria"
            description="Try modifying search keywords or clearing risk and contract filters."
            action={
              <button
                onClick={handleResetFilters}
                className="px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 text-xs font-medium hover:bg-indigo-100 transition"
              >
                Clear Filters
              </button>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50/80 text-slate-600 font-semibold uppercase tracking-wider text-[11px] border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3">Customer ID</th>
                  <th className="px-4 py-3">Churn Probability</th>
                  <th className="px-4 py-3">Risk Tier</th>
                  <th className="px-4 py-3">Action Urgency</th>
                  <th className="px-4 py-3">Contract</th>
                  <th className="px-4 py-3">Tenure</th>
                  <th className="px-4 py-3">Monthly Charges</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {customers.map((c) => {
                  const prob = c.churn_probability;
                  const probPercent = (prob * 100).toFixed(1);

                  return (
                    <tr
                      key={c.id}
                      className="hover:bg-slate-50/80 transition group cursor-pointer"
                    >
                      <td className="px-4 py-3 font-mono font-bold text-slate-900 flex items-center gap-2">
                        <Link
                          to={`/customers/${c.customer_id}`}
                          className="hover:text-indigo-600 flex items-center gap-1.5"
                        >
                          {c.customer_id}
                          <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition text-indigo-500" />
                        </Link>
                      </td>

                      {/* Churn Probability Bar */}
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-slate-100 rounded-full h-2 overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                prob >= 0.7
                                  ? 'bg-rose-500'
                                  : prob >= 0.3
                                  ? 'bg-amber-400'
                                  : 'bg-emerald-500'
                              }`}
                              style={{ width: `${Math.min(100, Math.max(5, prob * 100))}%` }}
                            />
                          </div>
                          <span
                            className={`font-mono font-semibold ${
                              prob >= 0.7
                                ? 'text-rose-600'
                                : prob >= 0.3
                                ? 'text-amber-600'
                                : 'text-emerald-600'
                            }`}
                          >
                            {probPercent}%
                          </span>
                        </div>
                      </td>

                      <td className="px-4 py-3">
                        <Badge label={c.risk_category} variant="risk" />
                      </td>

                      <td className="px-4 py-3">
                        <Badge label={c.action_urgency} variant="urgency" size="sm" />
                      </td>

                      <td className="px-4 py-3 text-slate-700">{c.contract}</td>

                      <td className="px-4 py-3 text-slate-600 font-mono">
                        {c.tenure} mo{c.tenure !== 1 ? 's' : ''}
                      </td>

                      <td className="px-4 py-3 font-mono text-slate-700">
                        ${Number(c.monthly_charges).toFixed(2)}
                      </td>

                      <td className="px-4 py-3 text-right">
                        <Link
                          to={`/customers/${c.customer_id}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 font-semibold text-xs transition"
                        >
                          <span>Inspect SHAP</span>
                          <ExternalLink className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        <Pagination
          total={total}
          limit={limit}
          offset={offset}
          onPageChange={(newOffset) => setOffset(newOffset)}
          onLimitChange={(newLimit) => {
            setLimit(newLimit);
            setOffset(0);
          }}
        />
      </div>
    </div>
  );
};

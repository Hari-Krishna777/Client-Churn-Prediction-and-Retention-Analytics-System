import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { apiClient } from '../../api/client';
import { ChevronDown, Sparkles } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  useEffect(() => {
    apiClient.get('/health')
      .then((res) => {
        setBackendOnline(res.status === 200);
      })
      .catch(() => setBackendOnline(false));
  }, []);

  const getRoleBadge = (role: string) => {
    if (role === 'admin') return 'bg-purple-100 text-purple-800 border-purple-200';
    if (role === 'analyst') return 'bg-indigo-100 text-indigo-800 border-indigo-200';
    return 'bg-slate-100 text-slate-700 border-slate-200';
  };

  return (
    <header className="sticky top-0 z-30 bg-white/95 backdrop-blur-md border-b border-slate-200/80 px-6 py-3 flex items-center justify-between shadow-xs">
      <div className="flex items-center space-x-3">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-mono">v3.0.0</span>
          <span className="hidden sm:inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
            <span className={`w-1.5 h-1.5 rounded-full ${backendOnline ? 'bg-emerald-500 animate-pulse' : 'bg-amber-400'}`} />
            {backendOnline === null ? 'Connecting...' : backendOnline ? 'FastAPI Connected' : 'Backend Offline'}
          </span>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {/* ML Engine Badge */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-medium">
          <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
          <span>XGBoost + SHAP Explainer Active</span>
        </div>

        {/* Authenticated user menu */}
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center space-x-2.5 p-1.5 pr-2.5 rounded-xl border border-slate-200 hover:bg-slate-50 transition focus:outline-none"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-violet-600 text-white flex items-center justify-center font-bold text-xs shadow-xs">
              {user?.username?.substring(0, 2).toUpperCase() || 'AN'}
            </div>
            <div className="text-left hidden sm:block">
              <div className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
                {user?.username || 'Analyst'}
                <span className={`px-1.5 py-0.2 rounded text-[10px] border ${getRoleBadge(user?.role || 'analyst')}`}>
                  {user?.role?.toUpperCase() || 'ANALYST'}
                </span>
              </div>
              <div className="text-[11px] text-slate-400 leading-none">{user?.email || 'analyst@churniq.io'}</div>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 mt-2 w-64 bg-white rounded-xl shadow-xl border border-slate-200 py-2 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
              <div className="px-3 py-2 border-b border-slate-100">
                <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Signed in</p>
                <p className="mt-1 text-xs font-medium text-slate-800">{user?.email}</p>
              </div>
              <div className="mt-1 border-t border-slate-100 pt-1 px-2">
                <button
                  onClick={() => {
                    logout();
                    setDropdownOpen(false);
                  }}
                  className="w-full text-left px-2 py-1.5 text-xs text-rose-600 hover:bg-rose-50 rounded-lg transition"
                >
                  Sign Out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

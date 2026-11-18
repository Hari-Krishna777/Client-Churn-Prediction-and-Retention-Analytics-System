import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  UploadCloud,
  Users,
  HeartHandshake,
  FileSpreadsheet,
  BrainCircuit,
  TrendingDown,
  Layers,
} from 'lucide-react';

interface SidebarProps {
  collapsed?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = () => {
  const navItems = [
    {
      to: '/',
      label: 'Main Dashboard',
      icon: LayoutDashboard,
      badge: null,
      desc: 'KPIs, Risk & Segment Charts',
    },
    {
      to: '/upload',
      label: 'Dataset Upload',
      icon: UploadCloud,
      badge: 'Batch',
      desc: 'CSV validation & pipeline',
    },
    {
      to: '/customers',
      label: 'Customer Analytics',
      icon: Users,
      badge: null,
      desc: 'Risk filters & probability sort',
    },
    {
      to: '/retention',
      label: 'Retention Management',
      icon: HeartHandshake,
      badge: 'Urgent',
      desc: 'Action tracker & follow-up',
    },
    {
      to: '/reports',
      label: 'Reports & Exports',
      icon: FileSpreadsheet,
      badge: null,
      desc: 'CSV downloads & summaries',
    },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col border-r border-slate-800 flex-shrink-0 select-none">
      {/* Brand Header */}
      <div className="h-16 px-6 flex items-center border-b border-slate-800 bg-slate-950/40">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
            <BrainCircuit className="w-5 h-5" />
          </div>
          <div>
            <div className="font-bold text-white text-base tracking-tight flex items-center gap-1.5">
              ChurnIQ
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                PRO
              </span>
            </div>
            <div className="text-[11px] text-slate-400">Retention & SHAP AI</div>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-6 space-y-1.5 overflow-y-auto">
        <div className="px-3 pb-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          Intelligence Suite
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 group ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                }`
              }
            >
              <div className="flex items-center space-x-3">
                <Icon className="w-4 h-4 flex-shrink-0 transition-transform group-hover:scale-110" />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-md font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  {item.badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer System Status */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/20 text-xs text-slate-400 space-y-2">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            Model Pipeline
          </span>
          <span className="font-mono text-slate-300">XGBoost 3.4</span>
        </div>
        <div className="text-[11px] text-slate-400">
          Threshold: <span className="font-mono text-slate-300 font-semibold">0.40</span> (Optimized Recall)
        </div>
      </div>
    </aside>
  );
};

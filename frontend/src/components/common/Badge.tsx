import React from 'react';

interface BadgeProps {
  label: string;
  variant?: 'risk' | 'urgency' | 'status' | 'default';
  size?: 'sm' | 'md';
}

export const Badge: React.FC<BadgeProps> = ({ label, variant = 'default', size = 'sm' }) => {
  const norm = label.toUpperCase();

  let colorClasses = 'bg-slate-100 text-slate-700 border-slate-200';

  if (variant === 'risk') {
    if (norm === 'HIGH') {
      colorClasses = 'bg-rose-50 text-rose-700 border-rose-200 font-semibold';
    } else if (norm === 'MEDIUM') {
      colorClasses = 'bg-amber-50 text-amber-700 border-amber-200 font-medium';
    } else if (norm === 'LOW') {
      colorClasses = 'bg-emerald-50 text-emerald-700 border-emerald-200 font-medium';
    }
  } else if (variant === 'urgency') {
    if (norm === 'URGENT') {
      colorClasses = 'bg-red-100 text-red-800 border-red-300 font-semibold animate-pulse';
    } else if (norm === 'PLANNED') {
      colorClasses = 'bg-blue-50 text-blue-700 border-blue-200 font-medium';
    } else if (norm === 'MONITOR') {
      colorClasses = 'bg-slate-100 text-slate-600 border-slate-200 font-medium';
    }
  } else if (variant === 'status') {
    if (norm === 'RETAINED') {
      colorClasses = 'bg-emerald-100 text-emerald-800 border-emerald-300 font-semibold';
    } else if (norm === 'CONTACTED' || norm === 'IN PROGRESS') {
      colorClasses = 'bg-sky-100 text-sky-800 border-sky-300 font-medium';
    } else if (norm === 'PENDING') {
      colorClasses = 'bg-amber-100 text-amber-800 border-amber-300 font-medium';
    } else if (norm === 'ESCALATED') {
      colorClasses = 'bg-purple-100 text-purple-800 border-purple-300 font-semibold';
    } else if (norm === 'CLOSED') {
      colorClasses = 'bg-slate-100 text-slate-600 border-slate-200';
    }
  }

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm';

  return (
    <span
      className={`inline-flex items-center justify-center rounded-full border ${sizeClasses} ${colorClasses} tracking-wide transition-colors`}
    >
      {label}
    </span>
  );
};

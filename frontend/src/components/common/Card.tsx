import React from 'react';

interface CardProps {
  title?: string;
  subtitle?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  icon,
  action,
  children,
  className = '',
}) => {
  return (
    <div
      className={`bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden transition-all duration-200 hover:shadow-md ${className}`}
    >
      {(title || action || icon) && (
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {icon && <div className="text-slate-500">{icon}</div>}
            <div>
              {title && <h3 className="font-semibold text-slate-800 text-base">{title}</h3>}
              {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
            </div>
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
};

import React from 'react';
import { useNotification } from '../../context/NotificationContext';
import { CheckCircle2, AlertCircle, Info, AlertTriangle, X } from 'lucide-react';

export const ToastContainer: React.FC = () => {
  const { notifications, removeNotification } = useNotification();

  if (notifications.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col space-y-2 max-w-sm w-full pointer-events-none">
      {notifications.map((n) => {
        let bgClass = 'bg-slate-900 text-white border-slate-700';
        let Icon = Info;

        if (n.type === 'success') {
          bgClass = 'bg-emerald-800/95 text-white border-emerald-600 shadow-emerald-900/20';
          Icon = CheckCircle2;
        } else if (n.type === 'error') {
          bgClass = 'bg-rose-800/95 text-white border-rose-600 shadow-rose-900/20';
          Icon = AlertCircle;
        } else if (n.type === 'warning') {
          bgClass = 'bg-amber-800/95 text-white border-amber-600 shadow-amber-900/20';
          Icon = AlertTriangle;
        }

        return (
          <div
            key={n.id}
            className={`pointer-events-auto flex items-start gap-3 p-3.5 rounded-xl border shadow-lg backdrop-blur-sm transition-all duration-300 transform translate-y-0 ${bgClass}`}
          >
            <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div className="flex-1 text-sm">
              {n.title && <div className="font-semibold text-white mb-0.5">{n.title}</div>}
              <div className="text-white/90 leading-snug">{n.message}</div>
            </div>
            <button
              onClick={() => removeNotification(n.id)}
              className="text-white/60 hover:text-white transition flex-shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
};

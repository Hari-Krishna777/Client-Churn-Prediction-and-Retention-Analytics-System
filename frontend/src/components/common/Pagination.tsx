import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  total: number;
  limit: number;
  offset: number;
  onPageChange: (newOffset: number) => void;
  onLimitChange?: (newLimit: number) => void;
}

export const Pagination: React.FC<PaginationProps> = ({
  total,
  limit,
  offset,
  onPageChange,
  onLimitChange,
}) => {
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  const startRecord = total === 0 ? 0 : offset + 1;
  const endRecord = Math.min(offset + limit, total);

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 py-3 px-4 bg-white border-t border-slate-200 text-sm text-slate-600">
      <div className="flex items-center gap-2">
        <span>
          Showing <strong className="text-slate-800">{startRecord}</strong> to{' '}
          <strong className="text-slate-800">{endRecord}</strong> of{' '}
          <strong className="text-slate-800">{total}</strong> records
        </span>
        {onLimitChange && (
          <div className="flex items-center gap-1 ml-4 text-xs">
            <span>Per page:</span>
            <select
              value={limit}
              onChange={(e) => onLimitChange(Number(e.target.value))}
              className="border border-slate-200 rounded px-1.5 py-0.5 bg-slate-50 text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        )}
      </div>

      <div className="flex items-center space-x-1">
        <button
          onClick={() => onPageChange(Math.max(0, offset - limit))}
          disabled={currentPage <= 1}
          className="inline-flex items-center px-2.5 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition"
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          Previous
        </button>

        <span className="px-3 py-1 text-xs font-medium text-slate-500">
          Page {currentPage} of {totalPages}
        </span>

        <button
          onClick={() => onPageChange(offset + limit)}
          disabled={currentPage >= totalPages}
          className="inline-flex items-center px-2.5 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition"
        >
          Next
          <ChevronRight className="w-4 h-4 ml-1" />
        </button>
      </div>
    </div>
  );
};

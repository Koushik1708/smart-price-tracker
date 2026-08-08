import React from 'react';

export function ProductCardSkeleton() {
  return (
    <div className="flex flex-col p-3.5 rounded-xl border border-slate-200/70 dark:border-slate-800 bg-white dark:bg-slate-800/80 animate-pulse gap-2 shrink-0 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 bg-slate-200 dark:bg-slate-700 rounded-lg shrink-0" />
        <div className="flex-1 flex flex-col gap-1.5 min-w-0">
          <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded-md w-3/4" />
          <div className="h-3 bg-slate-100 dark:bg-slate-700/60 rounded-md w-1/2" />
        </div>
      </div>
      <div className="flex gap-2 ml-6">
        <div className="h-4 w-12 bg-slate-200 dark:bg-slate-700 rounded-full" />
        <div className="h-4 w-14 bg-slate-200 dark:bg-slate-700 rounded-full" />
      </div>
    </div>
  );
}

export function ProductDetailsSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="bg-white dark:bg-slate-800/90 rounded-2xl border border-slate-200 dark:border-slate-700/80 p-6 flex flex-col gap-4 shadow-sm">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2 flex-1">
            <div className="h-6 bg-slate-200 dark:bg-slate-700 rounded-md w-2/3" />
            <div className="h-4 bg-slate-100 dark:bg-slate-700/60 rounded-md w-1/3" />
          </div>
          <div className="h-10 w-28 bg-slate-200 dark:bg-slate-700 rounded-xl" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-slate-100 dark:border-slate-700/50">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-16 bg-slate-100 dark:bg-slate-700/40 rounded-xl p-3" />
          ))}
        </div>
      </div>
      <div className="bg-white dark:bg-slate-800/90 rounded-2xl border border-slate-200 dark:border-slate-700/80 p-6 h-80 flex items-center justify-center">
        <div className="w-full h-full bg-slate-100 dark:bg-slate-700/40 rounded-xl flex items-center justify-center text-slate-400 dark:text-slate-500 font-medium text-sm">
          Loading Price History Chart...
        </div>
      </div>
    </div>
  );
}

export function DashboardCardsSkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {[1, 2, 3, 4].map(i => (
        <div key={i} className="bg-white dark:bg-slate-800/90 p-5 rounded-2xl border border-slate-200/80 dark:border-slate-700/80 shadow-sm animate-pulse space-y-3">
          <div className="flex justify-between items-center">
            <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-1/2" />
            <div className="w-8 h-8 bg-slate-100 dark:bg-slate-700/50 rounded-lg" />
          </div>
          <div className="h-8 bg-slate-200 dark:bg-slate-700 rounded w-1/3" />
        </div>
      ))}
    </div>
  );
}

export function TableSkeleton({ rows = 5 }) {
  return (
    <div className="space-y-3 animate-pulse">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-12 bg-slate-100 dark:bg-slate-800 rounded-xl w-full" />
      ))}
    </div>
  );
}

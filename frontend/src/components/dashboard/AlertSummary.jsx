import React from 'react';

const AlertSummary = ({ summary, loading }) => {
  if (loading) {
    return (
      <div className="bg-white dark:bg-slate-800/90 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700/80 p-5 h-full">
        <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-4">Alert Summary</h3>
        <div className="flex gap-4 animate-pulse">
          <div className="w-16 h-16 bg-slate-200 dark:bg-slate-700 rounded-full"></div>
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-full"></div>
            <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-3/4"></div>
          </div>
        </div>
      </div>
    );
  }

  const active = summary?.active_alerts || 0;
  const triggered = summary?.triggered_alerts || 0;
  const total = active + triggered;

  return (
    <div className="bg-white dark:bg-slate-800/90 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700/80 p-5 h-full flex flex-col">
      <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-4">Alert Summary</h3>
      
      <div className="flex items-center gap-6 mt-2">
        <div className="relative w-24 h-24 shrink-0 flex items-center justify-center">
          <svg viewBox="0 0 36 36" className="w-full h-full transform -rotate-90">
            <circle cx="18" cy="18" r="16" fill="none" className="stroke-slate-100 dark:stroke-slate-700" strokeWidth="4"></circle>
            {total > 0 && (
              <>
                <circle 
                  cx="18" cy="18" r="16" fill="none" 
                  className="stroke-emerald-500 dark:stroke-emerald-400" strokeWidth="4" 
                  strokeDasharray={`${(active / total) * 100} 100`}
                ></circle>
                <circle 
                  cx="18" cy="18" r="16" fill="none" 
                  className="stroke-rose-500 dark:stroke-rose-400" strokeWidth="4" 
                  strokeDasharray={`${(triggered / total) * 100} 100`}
                  strokeDashoffset={`-${(active / total) * 100}`}
                ></circle>
              </>
            )}
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-xl font-extrabold text-slate-800 dark:text-slate-100">{total}</span>
            <span className="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-bold">Total</span>
          </div>
        </div>
        
        <div className="flex flex-col gap-3 flex-1">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-emerald-500 dark:bg-emerald-400"></span>
              <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">Active</span>
            </div>
            <span className="font-bold text-slate-900 dark:text-slate-100">{active}</span>
          </div>
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-rose-500 dark:bg-rose-400"></span>
              <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">Triggered</span>
            </div>
            <span className="font-bold text-slate-900 dark:text-slate-100">{triggered}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AlertSummary;

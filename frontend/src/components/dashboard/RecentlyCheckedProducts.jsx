import React from 'react';

const timeAgo = (dateStr) => {
  if (!dateStr) return 'Never';
  const seconds = Math.floor((new Date() - new Date(dateStr)) / 1000);
  let interval = seconds / 31536000;
  if (interval > 1) return Math.floor(interval) + ' years ago';
  interval = seconds / 2592000;
  if (interval > 1) return Math.floor(interval) + ' months ago';
  interval = seconds / 86400;
  if (interval > 1) return Math.floor(interval) + ' days ago';
  interval = seconds / 3600;
  if (interval > 1) return Math.floor(interval) + ' hours ago';
  interval = seconds / 60;
  if (interval > 1) return Math.floor(interval) + ' minutes ago';
  return 'just now';
};

const formatCurrency = (val) => {
  if (!val) return '-';
  return '₹' + parseFloat(val).toLocaleString('en-IN', { maximumFractionDigits: 0 });
};

const RecentlyCheckedProducts = ({ products, loading }) => {
  if (loading) {
    return (
      <div className="bg-white dark:bg-slate-800/90 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700/80 p-5 h-full">
        <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-4">Recently Checked</h3>
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="flex gap-3 animate-pulse">
              <div className="w-12 h-12 bg-slate-200 dark:bg-slate-700 rounded-md shrink-0"></div>
              <div className="flex-1 space-y-2 py-1">
                <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-full"></div>
                <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-1/2"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800/90 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700/80 p-5 h-full flex flex-col">
      <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-4">Recently Checked</h3>
      
      {!products || products.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center py-10 opacity-75">
          <div className="w-16 h-16 bg-slate-50 dark:bg-slate-700/50 text-slate-300 dark:text-slate-500 rounded-full flex items-center justify-center mb-4">
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
          </div>
          <p className="text-sm font-semibold text-slate-500 dark:text-slate-400">No recent checks</p>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">Background scans will populate this soon.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-3 overflow-y-auto pr-2 custom-scrollbar max-h-[300px]">
          {products.map((p, idx) => {
            const formattedTime = timeAgo(p.last_checked);
            return (
              <div key={idx} className="flex items-start gap-3 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/40 transition-colors border border-transparent hover:border-slate-100 dark:hover:border-slate-700/60">
                {p.image && (
                  <div className="w-12 h-12 shrink-0 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded p-1 flex items-center justify-center">
                    <img src={p.image} alt={p.title} className="max-w-full max-h-full object-contain" />
                  </div>
                )}
                <div className="flex flex-col min-w-0 flex-1">
                  <span className="font-semibold text-slate-800 dark:text-slate-100 text-sm truncate" title={p.title}>{p.title}</span>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="font-bold text-slate-700 dark:text-slate-200 text-sm">{formatCurrency(p.current_price)}</span>
                    <span className="text-slate-300 dark:text-slate-600">•</span>
                    <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded-sm ${p.status === 'SUCCESS' ? 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50' : p.status === 'FAILED' ? 'text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/50' : 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/50'}`}>
                      {p.status}
                    </span>
                  </div>
                </div>
                <div className="text-xs text-slate-400 dark:text-slate-500 whitespace-nowrap pt-1">
                  {formattedTime}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default React.memo(RecentlyCheckedProducts);

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

const ActivityIcon = ({ type }) => {
  switch (type) {
    case 'PRICE_DROPPED': return <span className="flex items-center justify-center w-8 h-8 bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 rounded-full text-sm">▼</span>;
    case 'PRICE_INCREASED': return <span className="flex items-center justify-center w-8 h-8 bg-rose-100 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 rounded-full text-sm">▲</span>;
    case 'PRICE_UPDATED': return <span className="flex items-center justify-center w-8 h-8 bg-blue-100 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 rounded-full text-sm">ℹ️</span>;
    case 'SCRAPE_FAILED': return <span className="flex items-center justify-center w-8 h-8 bg-amber-100 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 rounded-full text-sm">⚠️</span>;
    case 'ALERT_TRIGGERED': return <span className="flex items-center justify-center w-8 h-8 bg-purple-100 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400 rounded-full text-sm">🔔</span>;
    default: return <span className="flex items-center justify-center w-8 h-8 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 rounded-full text-sm">•</span>;
  }
};

const formatCurrency = (val) => {
  if (val === undefined || val === null) return '-';
  return '₹' + parseFloat(val).toLocaleString('en-IN', { maximumFractionDigits: 0 });
};

const RecentActivity = ({ activity, loading }) => {
  if (loading) {
    return (
      <div className="bg-white dark:bg-slate-800/90 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700/80 p-5 h-full">
        <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-4">Recent Activity</h3>
        <div className="space-y-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="flex gap-4 animate-pulse">
              <div className="w-8 h-8 bg-slate-200 dark:bg-slate-700 rounded-full shrink-0"></div>
              <div className="flex-1 space-y-2 py-1">
                <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-full"></div>
                <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded w-1/4"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800/90 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700/80 p-5 h-full flex flex-col">
      <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-4">Recent Activity</h3>
      
      {!activity || activity.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center py-10 opacity-75">
          <div className="w-16 h-16 bg-slate-50 dark:bg-slate-700/50 text-slate-300 dark:text-slate-500 rounded-full flex items-center justify-center mb-4">
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
          </div>
          <p className="text-sm font-semibold text-slate-500 dark:text-slate-400">No recent activity</p>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">Events will appear here as we track products.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-4 overflow-y-auto pr-2 custom-scrollbar max-h-[400px]">
          {activity.map((item, idx) => (
            <div key={idx} className="flex items-start gap-3 relative">
              {idx !== activity.length - 1 && (
                <div className="absolute left-4 top-8 bottom-[-16px] w-[2px] bg-slate-100 dark:bg-slate-700/60"></div>
              )}
              <div className="shrink-0 z-10">
                <ActivityIcon type={item.type} />
              </div>
              <div className="flex flex-col min-w-0 pb-1">
                <span className="text-sm text-slate-800 dark:text-slate-200">
                  {item.type === 'PRICE_DROPPED' && <span>Price dropped to <span className="font-bold text-emerald-600 dark:text-emerald-400">{formatCurrency(item.current_price)}</span> on </span>}
                  {item.type === 'PRICE_INCREASED' && <span>Price increased to <span className="font-bold text-rose-600 dark:text-rose-400">{formatCurrency(item.current_price)}</span> on </span>}
                  {item.type === 'PRICE_UPDATED' && <span>Price checked at <span className="font-bold text-slate-700 dark:text-slate-200">{formatCurrency(item.current_price)}</span> for </span>}
                  {item.type === 'SCRAPE_FAILED' && <span>Scrape failed for </span>}
                  {item.type === 'ALERT_TRIGGERED' && <span>Alert triggered for </span>}
                  <span className="font-semibold">{item.product_title}</span>
                </span>
                <span className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">{timeAgo(item.timestamp)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default React.memo(RecentActivity);

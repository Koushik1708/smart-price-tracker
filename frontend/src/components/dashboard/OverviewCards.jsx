import React from 'react';

const OverviewCards = ({ summary }) => {
  if (!summary) return <CardsSkeleton />;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <Card 
        title="Total Products" 
        value={summary.total_tracked_products} 
        icon="📦" 
        color="indigo" 
      />
      <Card 
        title="Active Alerts" 
        value={summary.active_alerts} 
        icon="🔔" 
        color="emerald" 
      />
      <Card 
        title="Triggered Alerts" 
        value={summary.triggered_alerts} 
        icon="⚡" 
        color="rose" 
      />
      <Card 
        title="Checked Today" 
        value={summary.products_checked_today} 
        icon="✅" 
        color="blue" 
      />
    </div>
  );
};

const Card = ({ title, value, icon, color }) => {
  const colorMap = {
    indigo: 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/60 border-indigo-100 dark:border-indigo-900/50',
    emerald: 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 border-emerald-100 dark:border-emerald-900/50',
    rose: 'text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/60 border-rose-100 dark:border-rose-900/50',
    blue: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/60 border-blue-100 dark:border-blue-900/50',
  };

  const selectedColor = colorMap[color] || colorMap.indigo;

  return (
    <div className="p-5 rounded-xl border bg-white dark:bg-slate-800/90 border-slate-200/80 dark:border-slate-700/80 shadow-sm flex items-center gap-4 transition-all hover:-translate-y-1">
      <div className={`w-12 h-12 rounded-full flex items-center justify-center text-xl shrink-0 border ${selectedColor}`}>
        {icon}
      </div>
      <div>
        <div className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{title}</div>
        <div className="text-2xl font-extrabold text-slate-800 dark:text-slate-100">{value}</div>
      </div>
    </div>
  );
};

const CardsSkeleton = () => (
  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
    {[1, 2, 3, 4].map(i => (
      <div key={i} className="p-5 rounded-xl border border-slate-100 dark:border-slate-700/80 bg-white dark:bg-slate-800/90 shadow-sm flex items-center gap-4 animate-pulse">
        <div className="w-12 h-12 rounded-full bg-slate-200 dark:bg-slate-700 shrink-0"></div>
        <div className="space-y-2 flex-1">
          <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-1/2"></div>
          <div className="h-6 bg-slate-200 dark:bg-slate-700 rounded w-1/3"></div>
        </div>
      </div>
    ))}
  </div>
);

export default OverviewCards;

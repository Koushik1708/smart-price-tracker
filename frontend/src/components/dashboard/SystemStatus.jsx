import React, { useState, useEffect } from 'react';
import apiClient from '../../apiClient';

const StatusPill = ({ name, status, loading }) => {
  if (loading) {
    return (
      <div className="flex justify-between items-center py-2 animate-pulse">
        <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/3"></div>
        <div className="h-6 w-16 bg-slate-200 dark:bg-slate-700 rounded-full"></div>
      </div>
    );
  }

  let colorClass = 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400';
  let statusText = 'Unknown';

  if (name === 'API Backend') {
    if (status === 'healthy') {
      colorClass = 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/50';
      statusText = 'Backend Healthy';
    } else if (status === 'degraded') {
      colorClass = 'bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-900/50';
      statusText = 'Backend Degraded';
    } else {
      colorClass = 'bg-rose-100 dark:bg-rose-950/60 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-900/50';
      statusText = 'Backend Offline';
    }
  } else {
    if (status === 'healthy') {
      colorClass = 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/50';
      statusText = 'Healthy';
    } else if (status === 'warning' || status === 'no_workers' || status === 'not_configured') {
      colorClass = 'bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-900/50';
      statusText = 'Warning';
    } else {
      colorClass = 'bg-rose-100 dark:bg-rose-950/60 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-900/50';
      statusText = 'Offline';
    }
  }

  return (
    <div className="flex justify-between items-center py-2 border-b border-slate-50 dark:border-slate-700/40 last:border-0">
      <span className="font-semibold text-slate-700 dark:text-slate-300 text-sm">{name}</span>
      <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${colorClass}`}>
        {statusText}
      </span>
    </div>
  );
};

const SystemStatus = () => {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchHealth = () => {
    setLoading(true);
    apiClient.get(`/health`)
      .then(res => setHealth(res.data))
      .catch(err => {
        setHealth({
          status: 'unhealthy',
          summary: 'Connection to backend failed.',
          database: 'offline',
          redis: 'offline',
          celery: 'offline',
          notifications: 'offline'
        });
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  useEffect(() => {
    const isUnhealthy = health?.status === 'unhealthy' || health?.status === 'offline';
    const intervalMs = isUnhealthy ? 5000 : 30000;
    
    const interval = setInterval(fetchHealth, intervalMs);
    return () => clearInterval(interval);
  }, [health?.status]);

  return (
    <div className="bg-white dark:bg-slate-800/90 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700/80 p-5 h-full flex flex-col relative">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100">System Status</h3>
        <button onClick={fetchHealth} disabled={loading} className="text-slate-400 dark:text-slate-500 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors" title="Refresh Status">
          <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
          </svg>
        </button>
      </div>

      <div className="flex flex-col flex-1">
        <StatusPill name="API Backend" status={health?.status} loading={loading} />
        <StatusPill name="Database" status={health?.database} loading={loading} />
        <StatusPill name="Redis Cache" status={health?.redis} loading={loading} />
        <StatusPill name="Celery Workers" status={health?.celery} loading={loading} />
      </div>

      {health?.summary && (
        <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700/60 text-[11px] text-slate-500 dark:text-slate-400 font-medium">
          {health.summary}
        </div>
      )}
    </div>
  );
};

export default React.memo(SystemStatus);

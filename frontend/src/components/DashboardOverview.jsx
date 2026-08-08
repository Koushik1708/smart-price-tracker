import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import apiClient from '../apiClient';

const OverviewCards = React.lazy(() => import('./dashboard/OverviewCards'));
const PriceDrops = React.lazy(() => import('./dashboard/PriceDrops'));
const RecentlyCheckedProducts = React.lazy(() => import('./dashboard/RecentlyCheckedProducts'));
const RecentActivity = React.lazy(() => import('./dashboard/RecentActivity'));
const AlertSummary = React.lazy(() => import('./dashboard/AlertSummary'));
const SystemStatus = React.lazy(() => import('./dashboard/SystemStatus'));

// Suspense fallbacks with exact component heights to prevent Layout Shift (CLS)
const OverviewCardsFallback = () => <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"><div className="h-[108px] rounded-xl bg-slate-100 dark:bg-slate-800 animate-pulse border border-slate-100 dark:border-slate-700/80 shadow-sm" /><div className="h-[108px] rounded-xl bg-slate-100 dark:bg-slate-800 animate-pulse border border-slate-100 dark:border-slate-700/80 shadow-sm" /><div className="h-[108px] rounded-xl bg-slate-100 dark:bg-slate-800 animate-pulse border border-slate-100 dark:border-slate-700/80 shadow-sm" /><div className="h-[108px] rounded-xl bg-slate-100 dark:bg-slate-800 animate-pulse border border-slate-100 dark:border-slate-700/80 shadow-sm" /></div>;
const PriceDropsFallback = () => <div className="bg-white dark:bg-slate-800/90 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700/80 p-5 h-[340px] animate-pulse"><div className="h-6 bg-slate-100 dark:bg-slate-700 rounded w-1/3 mb-4"></div><div className="space-y-3"><div className="h-10 bg-slate-100 dark:bg-slate-700 rounded"></div><div className="h-10 bg-slate-100 dark:bg-slate-700 rounded"></div><div className="h-10 bg-slate-100 dark:bg-slate-700 rounded"></div></div></div>;
const RecentlyCheckedFallback = () => <div className="bg-white dark:bg-slate-800/90 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700/80 p-5 h-[280px] animate-pulse"><div className="h-6 bg-slate-100 dark:bg-slate-700 rounded w-1/3 mb-4"></div><div className="space-y-3"><div className="h-10 bg-slate-100 dark:bg-slate-700 rounded"></div><div className="h-10 bg-slate-100 dark:bg-slate-700 rounded"></div></div></div>;
const RecentActivityFallback = () => <div className="bg-white dark:bg-slate-800/90 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700/80 p-5 h-[350px] animate-pulse"><div className="h-6 bg-slate-100 dark:bg-slate-700 rounded w-1/3 mb-4"></div><div className="space-y-4"><div className="h-12 bg-slate-100 dark:bg-slate-700 rounded"></div><div className="h-12 bg-slate-100 dark:bg-slate-700 rounded"></div><div className="h-12 bg-slate-100 dark:bg-slate-700 rounded"></div></div></div>;
const AlertSummaryFallback = () => <div className="bg-white dark:bg-slate-800/90 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700/80 p-5 h-[240px] animate-pulse"><div className="h-6 bg-slate-100 dark:bg-slate-700 rounded w-1/3 mb-4"></div><div className="space-y-3"><div className="h-8 bg-slate-100 dark:bg-slate-700 rounded"></div><div className="h-8 bg-slate-100 dark:bg-slate-700 rounded"></div></div></div>;
const SystemStatusFallback = () => <div className="bg-white dark:bg-slate-800/90 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700/80 p-5 h-[160px] animate-pulse"><div className="h-6 bg-slate-100 dark:bg-slate-700 rounded w-1/3 mb-4"></div><div className="h-12 bg-slate-100 dark:bg-slate-700 rounded"></div></div>;

const DashboardOverview = ({ onNavigate }) => {
  const [summary, setSummary] = useState(null);
  const [activity, setActivity] = useState(null);
  const [priceDrops, setPriceDrops] = useState(null);
  const [recentProducts, setRecentProducts] = useState(null);
  const [loading, setLoading] = useState(true);
  
  const [lastUpdated, setLastUpdated] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('Refreshing...'); // 'Connected', 'Refreshing...', 'Offline', 'Backend unavailable'
  const [isRefreshing, setIsRefreshing] = useState(false);
  
  const abortControllerRef = useRef(null);
  const retryTimeoutRef = useRef(null);
  const retryCountRef = useRef(0);
  const isComponentMounted = useRef(true);
  const totalTrackedRef = useRef(0);
  const visibilityChangeHandlerRef = useRef(null);

  // Sync summary total tracked products in a Ref to avoid breaking useEffect dependency chains
  if (summary) {
    totalTrackedRef.current = summary.total_tracked_products || 0;
  }

  const getRetryDelay = (attempt) => {
    const delays = [3000, 6000, 12000, 24000, 48000];
    return delays[Math.min(attempt, delays.length - 1)];
  };

  const fetchDashboardData = useCallback(async (isAutoRefresh = false) => {
    if (!isComponentMounted.current) return;
    
    // Cancel previous in-flight request to prevent race conditions
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    if (!isAutoRefresh) setLoading(true);
    setIsRefreshing(true);
    
    if (!isAutoRefresh) {
      setConnectionStatus('Refreshing...');
    } else {
      setConnectionStatus(prev => prev !== 'Connected' ? 'Refreshing...' : prev);
    }

    try {
      const [summaryRes, activityRes, dropsRes, productsRes] = await Promise.all([
        apiClient.get(`/dashboard/summary`, { signal: abortControllerRef.current.signal }),
        apiClient.get(`/dashboard/activity`, { signal: abortControllerRef.current.signal }),
        apiClient.get(`/dashboard/price-drops`, { signal: abortControllerRef.current.signal }),
        apiClient.get(`/dashboard/recent-products`, { signal: abortControllerRef.current.signal })
      ]);
      
      if (!isComponentMounted.current) return;

      setSummary(summaryRes.data);
      setActivity(activityRes.data);
      setPriceDrops(dropsRes.data);
      setRecentProducts(productsRes.data);
      setLastUpdated(new Date());
      setConnectionStatus('Connected');
      
      // Reset retry count on success
      retryCountRef.current = 0;
      if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
      
    } catch (error) {
      if (axios.isCancel(error)) {
        // Ignored, stale request cancelled
        return;
      }
      
      if (!isComponentMounted.current) return;
      
      console.error("Failed to load dashboard data:", error);
      
      // Handle backend unavailability with exponential backoff
      if (error.customType === 'network' || error.customType === 'timeout') {
        setConnectionStatus('Backend unavailable');
        
        if (retryCountRef.current < 5) {
          const delay = getRetryDelay(retryCountRef.current);
          retryCountRef.current += 1;
          
          if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
          retryTimeoutRef.current = setTimeout(() => {
            fetchDashboardData(true);
          }, delay);
        } else {
          setConnectionStatus('Offline');
        }
      } else {
        setConnectionStatus('Offline');
      }
    } finally {
      if (isComponentMounted.current) {
        setLoading(false);
        setIsRefreshing(false);
      }
    }
  }, []);

  useEffect(() => {
    isComponentMounted.current = true;
    fetchDashboardData(false);

    // Single polling timer management
    let intervalId = null;

    const startPolling = () => {
      if (intervalId) clearInterval(intervalId);
      // Only poll if we have products, to save resources
      intervalId = setInterval(() => {
        // Intelligent polling: if zero products, don't poll
        if (totalTrackedRef.current === 0) {
           return;
        }
        if (document.visibilityState === 'visible') {
          fetchDashboardData(true);
        }
      }, 15000);
    };

    startPolling();

    // Visibility change handler to immediately fetch if returning and stale
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchDashboardData(true);
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    visibilityChangeHandlerRef.current = handleVisibilityChange;

    return () => {
      isComponentMounted.current = false;
      if (intervalId) clearInterval(intervalId);
      if (abortControllerRef.current) abortControllerRef.current.abort();
      if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
      document.removeEventListener('visibilitychange', visibilityChangeHandlerRef.current);
    };
  }, [fetchDashboardData]);

  // Last Updated display logic
  const [timeAgoStr, setTimeAgoStr] = useState('');
  useEffect(() => {
    if (!lastUpdated) return;
    const updateTimeAgo = () => {
      const diff = Math.floor((new Date() - lastUpdated) / 1000);
      if (diff < 5) setTimeAgoStr('Updated just now');
      else if (diff < 60) setTimeAgoStr(`Updated ${diff} seconds ago`);
      else setTimeAgoStr(`Updated ${Math.floor(diff/60)} minutes ago`);
    };
    updateTimeAgo();
    const id = setInterval(updateTimeAgo, 5000);
    return () => clearInterval(id);
  }, [lastUpdated]);

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto w-full">
      {/* Quick Actions & Title */}
      <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
        <div className="flex flex-col gap-1 w-full sm:w-auto">
          <h2 className="text-2xl font-extrabold text-slate-800 dark:text-slate-100">Dashboard</h2>
          <div className="flex items-center gap-2 text-xs font-semibold">
            {connectionStatus === 'Connected' ? (
              <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500 dark:bg-emerald-400 animate-pulse"></span> {connectionStatus}</span>
            ) : connectionStatus === 'Refreshing...' ? (
              <span className="text-indigo-600 dark:text-indigo-400 flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-indigo-500 dark:bg-indigo-400 animate-bounce"></span> {connectionStatus}</span>
            ) : (
              <span className="text-rose-600 dark:text-rose-400 flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-rose-500 dark:bg-rose-400"></span> {connectionStatus}</span>
            )}
            {lastUpdated && <span className="text-slate-500 dark:text-slate-400 ml-2 border-l border-slate-300 dark:border-slate-600 pl-2">{timeAgoStr}</span>}
          </div>
        </div>
        <div className="flex gap-2 w-full sm:w-auto">
          <button onClick={() => onNavigate('products')} className="flex-1 sm:flex-none px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-semibold rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1 dark:focus:ring-offset-slate-900">
            View Products
          </button>
          <button onClick={() => onNavigate('alerts')} className="flex-1 sm:flex-none px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-semibold rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1 dark:focus:ring-offset-slate-900">
            View Alerts
          </button>
          <button onClick={() => fetchDashboardData(false)} disabled={isRefreshing} className="px-4 py-2 bg-indigo-600 dark:bg-indigo-500 text-white font-semibold rounded-lg hover:bg-indigo-700 dark:hover:bg-indigo-600 transition-colors shadow-sm text-sm flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1 dark:focus:ring-offset-slate-900">
            {isRefreshing ? (
              <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
              </svg>
            )}
            <span className="hidden sm:inline">{isRefreshing ? 'Refreshing...' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      {/* Row 1: Overview Cards */}
      <React.Suspense fallback={<OverviewCardsFallback />}>
        <OverviewCards summary={summary} loading={loading && !summary} />
      </React.Suspense>

      {/* Row 2: Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column (Spans 2 columns on large screens) */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <React.Suspense fallback={<PriceDropsFallback />}>
            <PriceDrops drops={priceDrops} loading={loading && !priceDrops} />
          </React.Suspense>
          <React.Suspense fallback={<RecentlyCheckedFallback />}>
            <RecentlyCheckedProducts products={recentProducts} loading={loading && !recentProducts} />
          </React.Suspense>
        </div>

        {/* Right Column */}
        <div className="flex flex-col gap-6">
          <React.Suspense fallback={<RecentActivityFallback />}>
            <RecentActivity activity={activity} loading={loading && !activity} />
          </React.Suspense>
          <React.Suspense fallback={<AlertSummaryFallback />}>
            <AlertSummary summary={summary} loading={loading && !summary} />
          </React.Suspense>
          <React.Suspense fallback={<SystemStatusFallback />}>
            <SystemStatus />
          </React.Suspense>
        </div>

      </div>
    </div>
  );
};

export default React.memo(DashboardOverview);

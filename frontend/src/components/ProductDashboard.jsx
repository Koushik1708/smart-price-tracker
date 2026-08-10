import React, { useEffect, useState, useRef, useCallback } from 'react';
import axios from 'axios';
import apiClient from '../apiClient';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer, ReferenceDot } from 'recharts';
import ProductActionsMenu from './common/ProductActionsMenu';
import EmptyState from './common/EmptyState';
import { ProductDetailsSkeleton } from './common/Skeletons';
import { useTheme } from '../ThemeContext';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const currentPrice = payload[0].value;
    const mrp = payload[1]?.value;
    const diff = mrp ? mrp - currentPrice : 0;
    const percentage = mrp && diff > 0 ? ((diff / mrp) * 100).toFixed(1) : 0;

    return (
      <div className="bg-white dark:bg-slate-800 p-3 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xl text-sm">
        <p className="font-bold text-slate-800 dark:text-slate-100 mb-2 border-b border-slate-100 dark:border-slate-700/60 pb-1">{label}</p>
        <p className="text-indigo-600 dark:text-indigo-400 font-extrabold flex justify-between gap-4">
          <span>Price:</span> <span>₹{currentPrice}</span>
        </p>
        {mrp && (
          <p className="text-slate-500 dark:text-slate-400 font-medium flex justify-between gap-4 mt-1">
            <span>MRP:</span> <span>₹{mrp}</span>
          </p>
        )}
        {percentage > 0 && (
          <p className="text-emerald-600 dark:text-emerald-400 font-bold flex justify-between gap-4 mt-1 bg-emerald-50 dark:bg-emerald-950/50 px-2 py-0.5 rounded">
            <span>Discount:</span> <span>{percentage}% Off</span>
          </p>
        )}
      </div>
    );
  }
  return null;
};

export default function ProductDashboard({ productId, onProductDeleted, onProductUpdated, showToast }) {
  const { theme } = useTheme();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  
  const [alerts, setAlerts] = useState([]);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [thresholdPrice, setThresholdPrice] = useState('');
  const [notificationChannel, setNotificationChannel] = useState('whatsapp');
  const [telegramChatId, setTelegramChatId] = useState('');
  const [isSettingAlert, setIsSettingAlert] = useState(false);

  const [preferences, setPreferences] = useState(null);
  const [testChannel, setTestChannel] = useState('telegram');
  const [testDestination, setTestDestination] = useState('');
  const [testMessage, setTestMessage] = useState('');
  const [isSendingTest, setIsSendingTest] = useState(false);
  const [isSavingPrefs, setIsSavingPrefs] = useState(false);

  const abortControllerRef = useRef(null);
  const pollingTimerRef = useRef(null);
  const isComponentMounted = useRef(true);

  const fetchPreferences = useCallback(async () => {
    try {
      const res = await apiClient.get('/notification-preferences');
      if (res.data && isComponentMounted.current) {
        setPreferences(res.data);
        const defaultCh = res.data.default_notification_channel || 'whatsapp';
        setNotificationChannel(defaultCh);
        setTestChannel(defaultCh);
        const phone = res.data.default_phone_number || res.data.whatsapp_phone_number || '';
        const tgId = res.data.default_telegram_chat_id || res.data.telegram_chat_id || '';
        setPhoneNumber(phone);
        setTelegramChatId(tgId);
        setTestDestination(defaultCh === 'telegram' ? tgId : phone);
      }
    } catch (err) {
      console.warn("Failed to load notification preferences", err);
    }
  }, []);

  useEffect(() => {
    fetchPreferences();
  }, [productId, fetchPreferences]);

  const handleChannelChange = (ch) => {
    setNotificationChannel(ch);
    const phone = preferences?.default_phone_number || preferences?.whatsapp_phone_number || '';
    const tgId = preferences?.default_telegram_chat_id || preferences?.telegram_chat_id || '';
    if (ch === 'telegram' && tgId) {
      setTelegramChatId(tgId);
    } else if (ch === 'whatsapp' && phone) {
      setPhoneNumber(phone);
    }
  };

  const handleSavePreferences = async (e) => {
    e.preventDefault();
    setIsSavingPrefs(true);
    try {
      const res = await apiClient.put('/notification-preferences', {
        default_phone_number: phoneNumber,
        whatsapp_phone_number: phoneNumber,
        default_telegram_chat_id: telegramChatId,
        telegram_chat_id: telegramChatId,
        default_notification_channel: notificationChannel
      });
      setPreferences(res.data);
      if (showToast) showToast('Global notification preferences saved successfully!', 'success');
    } catch (err) {
      if (showToast) showToast(err.customMessage || 'Failed to save preferences', 'error');
    } finally {
      if (isComponentMounted.current) setIsSavingPrefs(false);
    }
  };

  const handleSendTestNotification = async (e) => {
    e.preventDefault();
    setIsSendingTest(true);
    try {
      const payload = {
        channel: testChannel,
        destination: testDestination || undefined,
        message: testMessage || undefined
      };
      const res = await apiClient.post('/notifications/test', payload);
      if (res.data.success) {
        if (showToast) showToast(`✓ ${res.data.message}`, 'success');
      } else {
        if (showToast) showToast(`✗ ${res.data.message}`, 'error');
      }
    } catch (err) {
      if (showToast) showToast(err.response?.data?.detail || err.customMessage || 'Test notification failed', 'error');
    } finally {
      if (isComponentMounted.current) setIsSendingTest(false);
    }
  };

  const fetchProductData = useCallback(async (isSilentRefresh = false) => {
    if (!productId || !isComponentMounted.current) return;
    
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    if (!isSilentRefresh) setLoading(true);

    try {
      const [productRes, alertsRes] = await Promise.all([
        apiClient.get(`/products/${productId}`, { signal: abortControllerRef.current.signal }),
        apiClient.get(`/products/${productId}/alerts`, { signal: abortControllerRef.current.signal })
      ]);
      
      if (!isComponentMounted.current) return;

      const productInfo = productRes.data.product;
      setData(productRes.data);
      setAlerts(alertsRes.data || []);
      
      // Notify parent App component for synchronized state across sidebar & metrics
      if (onProductUpdated && productInfo) {
        onProductUpdated(productInfo);
      }
      
      // Handle Intelligent Polling for PENDING or SCRAPING statuses
      const status = productInfo?.status;
      if (status === 'PENDING' || status === 'SCRAPING') {
        if (pollingTimerRef.current) clearTimeout(pollingTimerRef.current);
        const pollInterval = status === 'PENDING' ? 3000 : 5000;
        pollingTimerRef.current = setTimeout(() => {
          if (document.visibilityState === 'visible') {
            fetchProductData(true);
          } else {
            const resumePolling = () => {
              if (document.visibilityState === 'visible') {
                document.removeEventListener('visibilitychange', resumePolling);
                fetchProductData(true);
              }
            };
            document.addEventListener('visibilitychange', resumePolling);
          }
        }, pollInterval);
      }
      
    } catch (err) {
      if (axios.isCancel(err)) return;
      if (!isComponentMounted.current) return;
      console.error("Error loading product dashboard:", err);
      if (!isSilentRefresh && (err.customType === 'network' || err.customType === 'timeout')) {
        if (showToast) showToast(err.customMessage, 'error');
      }
    } finally {
      if (isComponentMounted.current && !isSilentRefresh) setLoading(false);
    }
  }, [productId, onProductUpdated, showToast]);

  useEffect(() => {
    isComponentMounted.current = true;
    fetchProductData();

    return () => {
      isComponentMounted.current = false;
      if (abortControllerRef.current) abortControllerRef.current.abort();
      if (pollingTimerRef.current) clearTimeout(pollingTimerRef.current);
    };
  }, [fetchProductData]);

  const handleAddAlert = (e) => {
    e.preventDefault();
    if (!thresholdPrice) return;
    if (notificationChannel === 'whatsapp' && !phoneNumber) return;
    if (notificationChannel === 'telegram' && !telegramChatId) return;
    
    const payload = {
      threshold_price: parseFloat(thresholdPrice),
      notification_channel: notificationChannel
    };
    if (notificationChannel === 'whatsapp') {
      payload.phone_number = phoneNumber;
    } else if (notificationChannel === 'telegram') {
      payload.telegram_chat_id = telegramChatId;
    }
    
    setIsSettingAlert(true);
    apiClient.post(`/products/${productId}/alerts`, payload).then(res => {
      setAlerts(prev => [...prev, res.data]);
      setThresholdPrice('');
      if (showToast) {
        if (res.data.confirmation_sent) {
          showToast('Price alert active & confirmation message sent!', 'success');
        } else {
          showToast('Price alert active in database. (Confirmation delivery pending or provider unconfigured)', 'info');
        }
      }
    }).catch(err => {
      if (showToast) showToast(err.customMessage || 'Failed to set alert', 'error');
    }).finally(() => {
      if (isComponentMounted.current) setIsSettingAlert(false);
    });
  };

  const handleDeleteAlert = async (alertId) => {
    try {
      await apiClient.delete(`/alerts/${alertId}`);
      setAlerts(prev => prev.filter(a => a.id !== alertId));
      if (showToast) showToast('Alert removed.', 'info');
    } catch (err) {
      if (showToast) showToast('Failed to delete alert', 'error');
    }
  };

  const handlePauseToggleStatus = (newStatus) => {
    if (data && data.product) {
      const updatedProduct = { ...data.product, status: newStatus };
      setData(prev => ({ ...prev, product: updatedProduct }));
      if (onProductUpdated) onProductUpdated(updatedProduct);
    }
  };

  // Dark mode chart colors
  const isDark = theme === 'dark';
  const gridColor = isDark ? '#334155' : '#f1f5f9';
  const axisColor = isDark ? '#64748b' : '#94a3b8';
  const lineColor = isDark ? '#818cf8' : '#4f46e5';
  const mrpLineColor = isDark ? '#64748b' : '#94a3b8';

  if (!productId) {
    return (
      <EmptyState
        title="No Product Selected"
        description="Select a product from the sidebar list or track a new product URL above."
        className="bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700/80 min-h-[400px]"
      />
    );
  }

  if (loading) {
    return <ProductDetailsSkeleton />;
  }

  if (!data || !data.product) {
    return (
      <EmptyState
        title="Product Not Found"
        description="The requested product could not be loaded or was removed."
        className="bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700/80 min-h-[400px]"
      />
    );
  }

  const { product, statistics } = data;
  const snapshots = data.snapshots || data.history || [];
  const isFakeDiscount = product.fake_discount_detected;

  const latestSnapshot = snapshots.length > 0 ? snapshots[snapshots.length - 1] : null;
  const currentSellingPrice = product.current_price ?? statistics?.current_price ?? (latestSnapshot ? latestSnapshot.price : null);
  const listedMrp = product.mrp ?? (latestSnapshot ? latestSnapshot.mrp_shown : null);

  return (
    <div className="space-y-6">
      {/* Top Details Card */}
      <div className="bg-white dark:bg-slate-800/90 rounded-2xl border border-slate-200/80 dark:border-slate-700/80 p-6 shadow-sm transition-colors">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-100 dark:border-slate-700/60 pb-5">
          <div className="flex items-start gap-4 flex-1">
            {product.image_url && (
              <div className="w-16 h-16 rounded-xl border border-slate-200 dark:border-slate-700 p-1 shrink-0 bg-white dark:bg-slate-900 flex items-center justify-center">
                <img src={product.image_url} alt={product.title} className="w-full h-full object-contain" />
              </div>
            )}
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-bold px-2.5 py-0.5 rounded-md uppercase tracking-wider">
                  {product.platform}
                </span>
                <span className={`text-xs font-bold px-2.5 py-0.5 rounded-md uppercase tracking-wider ${
                  product.status === 'SUCCESS' ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-900/50' :
                  product.status === 'PAUSED' ? 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-600' :
                  product.status === 'FAILED' ? 'bg-rose-50 dark:bg-rose-950/50 text-rose-700 dark:text-rose-400 border border-rose-100 dark:border-rose-900/50' :
                  'bg-amber-50 dark:bg-amber-950/50 text-amber-700 dark:text-amber-400 border border-amber-100 dark:border-amber-900/50'
                }`}>
                  {product.status}
                </span>
              </div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-slate-50 leading-snug">{product.title}</h2>
              {product.brand && <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">Brand: {product.brand}</p>}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <a 
              href={product.url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="px-4 py-2 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-950/80 font-bold rounded-xl text-sm transition-colors flex items-center gap-1.5"
            >
              <span>Store Link</span>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
            </a>

            <ProductActionsMenu
              product={product}
              onRefresh={fetchProductData}
              onDelete={onProductDeleted}
              onPauseToggle={handlePauseToggleStatus}
              showToast={showToast}
            />
          </div>
        </div>

        {/* Price & Fake Discount Banner */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-5">
          <div className="bg-slate-50 dark:bg-slate-700/30 p-4 rounded-xl border border-slate-100 dark:border-slate-700/50">
            <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Current Selling Price</div>
            <div className="text-2xl font-black text-slate-900 dark:text-slate-50">
              {currentSellingPrice ? `₹${currentSellingPrice.toLocaleString()}` : 'N/A'}
            </div>
          </div>
          <div className="bg-slate-50 dark:bg-slate-700/30 p-4 rounded-xl border border-slate-100 dark:border-slate-700/50">
            <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Listed MRP</div>
            <div className="text-2xl font-black text-slate-600 dark:text-slate-400 line-through">
              {listedMrp ? `₹${listedMrp.toLocaleString()}` : 'N/A'}
            </div>
          </div>
          <div className="bg-slate-50 dark:bg-slate-700/30 p-4 rounded-xl border border-slate-100 dark:border-slate-700/50">
            <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Lowest Historical Price</div>
            <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400">
              {statistics?.lowest_price ? `₹${statistics.lowest_price.toLocaleString()}` : 'N/A'}
            </div>
          </div>
          <div className="bg-slate-50 dark:bg-slate-700/30 p-4 rounded-xl border border-slate-100 dark:border-slate-700/50">
            <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Highest Historical Price</div>
            <div className="text-2xl font-black text-slate-700 dark:text-slate-200">
              {statistics?.highest_price ? `₹${statistics.highest_price.toLocaleString()}` : 'N/A'}
            </div>
          </div>
        </div>

        {/* Failed Scrape Warning Banner */}
        {product.status === 'FAILED' && (
          <div className="mt-5 p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/50 text-rose-800 dark:text-rose-300 flex items-start gap-3">
            <div className="p-1 bg-rose-200 dark:bg-rose-900/60 rounded-lg text-rose-900 dark:text-rose-300 shrink-0 mt-0.5">⚠️</div>
            <div>
              <h4 className="font-bold text-sm">Product Scrape Failed</h4>
              <p className="text-xs text-rose-700 dark:text-rose-400 mt-0.5 leading-relaxed">
                {product.last_failure_reason || "Retailer automated access blocked or extraction failed. Retry tracking from the actions menu."}
              </p>
            </div>
          </div>
        )}

        {/* Fake Discount Warning Badge */}
        {isFakeDiscount && (
          <div className="mt-5 p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/50 text-amber-800 dark:text-amber-300 flex items-start gap-3">
            <div className="p-1 bg-amber-200 dark:bg-amber-900/60 rounded-lg text-amber-900 dark:text-amber-300 shrink-0 mt-0.5">⚠️</div>
            <div>
              <h4 className="font-bold text-sm">Potential Artificial MRP Inflation Detected</h4>
              <p className="text-xs text-amber-700 dark:text-amber-400 mt-0.5 leading-relaxed">
                The displayed MRP appears inflated relative to historical baseline pricing to fabricate a steeper discount percentage.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Chart Section */}
      <div className="bg-white dark:bg-slate-800/90 rounded-2xl border border-slate-200/80 dark:border-slate-700/80 p-6 shadow-sm transition-colors">
        <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-4">Historical Price Trend</h3>
        {snapshots && snapshots.length > 0 ? (
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={snapshots} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                <XAxis dataKey="timestamp" stroke={axisColor} fontSize={11} tickFormatter={(str) => str?.split('T')[0]} />
                <YAxis stroke={axisColor} fontSize={11} domain={['auto', 'auto']} />
                <RechartsTooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ color: isDark ? '#cbd5e1' : '#334155' }} />
                <Line type="monotone" dataKey="price" name="Selling Price" stroke={lineColor} strokeWidth={3} dot={{ r: 3 }} activeDot={{ r: 6 }} />
                <Line type="monotone" dataKey="mrp" name="MRP" stroke={mrpLineColor} strokeWidth={2} strokeDasharray="4 4" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <EmptyState
            title="No Price Snapshots Yet"
            description="Historical snapshots will populate automatically as scraping tasks complete."
            className="py-12"
          />
        )}
      </div>

      {/* Alert Configuration & Active Thresholds */}
      <div className="bg-white dark:bg-slate-800/90 rounded-2xl border border-slate-200/80 dark:border-slate-700/80 p-6 shadow-sm space-y-5 transition-colors">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100">Price Drop Alert Setup</h3>
          {((notificationChannel === 'telegram' && preferences?.telegram_chat_id) || (notificationChannel === 'whatsapp' && preferences?.whatsapp_phone_number)) && (
            <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-2.5 py-1 rounded-full border border-emerald-200 dark:border-emerald-900/50">
              ✓ Saved Destination Auto-filled
            </span>
          )}
        </div>
        
        <form onSubmit={handleAddAlert} className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <select
              value={notificationChannel}
              onChange={(e) => handleChannelChange(e.target.value)}
              className="p-3 border border-slate-200 dark:border-slate-700 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-900/80 text-slate-800 dark:text-slate-100 transition-colors"
            >
              <option value="whatsapp">📱 WhatsApp</option>
              <option value="telegram">✈️ Telegram</option>
            </select>
            {notificationChannel === 'whatsapp' ? (
              <input
                type="text"
                placeholder="WhatsApp Phone (+91...)"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                className="p-3 border border-slate-200 dark:border-slate-700 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-900/80 text-slate-800 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 transition-colors"
                required
              />
            ) : (
              <input
                type="text"
                placeholder="Telegram Chat ID"
                value={telegramChatId}
                onChange={(e) => setTelegramChatId(e.target.value)}
                className="p-3 border border-slate-200 dark:border-slate-700 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-900/80 text-slate-800 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 transition-colors"
                required
              />
            )}
            <input
              type="number"
              placeholder="Target Price Threshold (₹)"
              value={thresholdPrice}
              onChange={(e) => setThresholdPrice(e.target.value)}
              className="p-3 border border-slate-200 dark:border-slate-700 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-900/80 text-slate-800 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 transition-colors"
              required
            />
          </div>
          {notificationChannel === 'telegram' && (
            <p className="text-xs text-slate-500 dark:text-slate-400">
              To get your Chat ID: message your bot on Telegram, then visit <code className="bg-slate-100 dark:bg-slate-700 px-1 rounded">https://api.telegram.org/bot&lt;TOKEN&gt;/getUpdates</code> to find it.
            </p>
          )}
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="submit"
              disabled={isSettingAlert}
              className="bg-indigo-600 dark:bg-indigo-500 hover:bg-indigo-700 dark:hover:bg-indigo-600 text-white font-bold py-3 px-6 rounded-xl text-sm transition-colors disabled:opacity-50 shadow-md shadow-indigo-200 dark:shadow-none flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {isSettingAlert ? (
                <>
                  <svg className="w-4 h-4 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <span>Setting Alert...</span>
                </>
              ) : (
                <span>🔔 Create Alert</span>
              )}
            </button>
            <button
              type="button"
              onClick={handleSavePreferences}
              disabled={isSavingPrefs}
              className="bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 font-bold py-3 px-4 rounded-xl text-sm transition-colors disabled:opacity-50"
            >
              {isSavingPrefs ? 'Saving...' : '💾 Save as Default Preference'}
            </button>
          </div>
        </form>

        {/* Existing Alerts Table */}
        <div className="pt-3">
          <h4 className="text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">Configured Alerts</h4>
          {alerts.length === 0 ? (
            <EmptyState
              title="No Active Alerts"
              description="Create a price threshold alert to receive WhatsApp notifications when prices drop."
              className="py-8"
            />
          ) : (
             <div className="overflow-x-auto border border-slate-100 dark:border-slate-700/60 rounded-xl">
              <table className="w-full text-left text-sm text-slate-700 dark:text-slate-300">
                <thead className="bg-slate-50 dark:bg-slate-700/40 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase border-b border-slate-100 dark:border-slate-700/60">
                  <tr>
                    <th className="p-3">Channel</th>
                    <th className="p-3">Destination</th>
                    <th className="p-3">Target Price</th>
                    <th className="p-3">Status</th>
                    <th className="p-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700/40">
                  {alerts.map(alert => (
                    <tr key={alert.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors">
                      <td className="p-3">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                          (alert.notification_channel || 'whatsapp') === 'telegram'
                            ? 'bg-sky-50 dark:bg-sky-950/50 text-sky-700 dark:text-sky-400 border border-sky-100 dark:border-sky-900/50'
                            : 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-900/50'
                        }`}>
                          {(alert.notification_channel || 'whatsapp') === 'telegram' ? '✈️ Telegram' : '📱 WhatsApp'}
                        </span>
                      </td>
                      <td className="p-3 font-semibold text-slate-800 dark:text-slate-100">
                        {(alert.notification_channel || 'whatsapp') === 'telegram'
                          ? (alert.telegram_chat_id || '—')
                          : (alert.phone_number || '—')}
                      </td>
                      <td className="p-3 font-bold text-indigo-600 dark:text-indigo-400">₹{alert.threshold_price?.toLocaleString()}</td>
                      <td className="p-3">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                          alert.is_triggered ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-900/50' : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400'
                        }`}>
                          {alert.is_triggered ? 'Triggered' : 'Active'}
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        <button
                          onClick={() => handleDeleteAlert(alert.id)}
                          className="text-xs font-bold text-rose-600 dark:text-rose-400 hover:text-rose-800 dark:hover:text-rose-300 hover:bg-rose-50 dark:hover:bg-rose-950/50 px-2.5 py-1 rounded-lg transition-colors"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Direct Test Notification */}
      <div className="bg-white dark:bg-slate-800/90 rounded-2xl border border-slate-200/80 dark:border-slate-700/80 p-6 shadow-sm space-y-4 transition-colors">
        <div>
          <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
            <span>⚡ Direct Notification</span>
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Send an immediate test notification. This does not depend on a product price drop.
          </p>
        </div>

        <form onSubmit={handleSendTestNotification} className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Channel</label>
              <select
                value={testChannel}
                onChange={(e) => {
                  const ch = e.target.value;
                  setTestChannel(ch);
                  if (ch === 'telegram') {
                    setTestDestination(preferences?.telegram_chat_id || '');
                  } else {
                    setTestDestination(preferences?.whatsapp_phone_number || '');
                  }
                }}
                className="w-full p-3 border border-slate-200 dark:border-slate-700 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-900/80 text-slate-800 dark:text-slate-100 transition-colors"
              >
                <option value="telegram">✈️ Telegram</option>
                <option value="whatsapp">📱 WhatsApp</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Destination</label>
              <input
                type="text"
                placeholder={testChannel === 'telegram' ? "Telegram Chat ID" : "WhatsApp (+91...)"}
                value={testDestination}
                onChange={(e) => setTestDestination(e.target.value)}
                className="w-full p-3 border border-slate-200 dark:border-slate-700 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-900/80 text-slate-800 dark:text-slate-100 transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Custom Message (Optional)</label>
              <input
                type="text"
                placeholder="Test message text..."
                value={testMessage}
                onChange={(e) => setTestMessage(e.target.value)}
                className="w-full p-3 border border-slate-200 dark:border-slate-700 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500 bg-white dark:bg-slate-900/80 text-slate-800 dark:text-slate-100 transition-colors"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSendingTest}
            className="bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-500 dark:hover:bg-emerald-600 text-white font-bold py-3 px-6 rounded-xl text-sm transition-colors shadow-md disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isSendingTest ? 'Sending Test...' : '🔔 Send Test Notification'}
          </button>
        </form>
      </div>

    </div>
  );
}

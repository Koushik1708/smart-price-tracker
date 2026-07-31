import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { API_BASE_URL } from '../config';

export default function ProductDashboard({ productId, onProductDeleted, showToast }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isDeleting, setIsDeleting] = useState(false);
  
  const [alerts, setAlerts] = useState([]);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [thresholdPrice, setThresholdPrice] = useState('');
  const [isSettingAlert, setIsSettingAlert] = useState(false);

  useEffect(() => {
    if (!productId) return;
    setLoading(true);
    axios.get(`${API_BASE_URL}/products/${productId}`)
      .then(res => {
        setData(res.data);
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));

    axios.get(`${API_BASE_URL}/products/${productId}/alerts`)
      .then(res => setAlerts(res.data))
      .catch(err => console.error(err));
  }, [productId]);

  const handleAddAlert = (e) => {
    e.preventDefault();
    setIsSettingAlert(true);
    axios.post(`${API_BASE_URL}/products/${productId}/alerts`, {
      phone_number: phoneNumber,
      threshold_price: parseFloat(thresholdPrice)
    }).then(res => {
      setAlerts([...alerts, res.data]);
      setPhoneNumber('');
      setThresholdPrice('');
      setPhoneNumber('');
      setThresholdPrice('');
      if (showToast) showToast('Alert set successfully!', 'success');
    }).catch(err => {
      if (showToast) showToast(err.response?.data?.detail || 'Failed to set alert', 'error');
    }).finally(() => {
      setIsSettingAlert(false);
    });
  };

  const handleDelete = () => {
    if (!window.confirm("Are you sure you want to delete this product?")) return;
    setIsDeleting(true);
    axios.delete(`${API_BASE_URL}/products/${productId}`)
      .then(() => {
        if (onProductDeleted) onProductDeleted();
      })
      .catch(err => {
        console.error("Failed to delete product:", err);
        if (showToast) showToast("Failed to delete product", 'error');
        setIsDeleting(false);
      });
  };

  const handleRetry = () => {
    setLoading(true);
    axios.post(`${API_BASE_URL}/products/${productId}/retry`)
      .then(() => {
        // Refresh product data
        return axios.get(`${API_BASE_URL}/products/${productId}`);
      })
      .then(res => setData(res.data))
      .catch(err => {
        console.error(err);
        if (showToast) showToast(err.response?.data?.detail || "Failed to retry", 'error');
      })
      .finally(() => setLoading(false));
  };

  if (!productId) return <div className="lg:col-span-8 bg-white rounded-2xl shadow-sm border border-slate-200/80 p-8 text-center text-slate-500 italic h-[520px] flex items-center justify-center">Select a product to view its dashboard</div>;
  if (loading) return (
    <div className="lg:col-span-8 bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 lg:p-8 flex flex-col min-h-[520px] animate-pulse">
      <div className="flex gap-4 mb-8">
        <div className="w-20 h-20 bg-slate-200 rounded-lg shrink-0"></div>
        <div className="flex-1 space-y-3 py-2">
          <div className="h-6 bg-slate-200 rounded w-3/4"></div>
          <div className="flex gap-2">
            <div className="h-5 bg-slate-200 rounded w-16"></div>
            <div className="h-5 bg-slate-200 rounded w-20"></div>
          </div>
          <div className="h-4 bg-slate-200 rounded w-1/2"></div>
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="h-20 bg-slate-200 rounded-xl"></div>
        <div className="h-20 bg-slate-200 rounded-xl"></div>
        <div className="h-20 bg-slate-200 rounded-xl"></div>
        <div className="h-20 bg-slate-200 rounded-xl"></div>
      </div>
      <div className="flex-1 bg-slate-100 rounded-xl mt-4 min-h-[200px]"></div>
    </div>
  );
  if (!data) return <div className="lg:col-span-8 bg-white rounded-2xl shadow-sm border border-slate-200/80 p-8 text-center text-rose-500 h-[520px] flex items-center justify-center">Error loading data</div>;

  const chartData = data.history.map(snap => ({
    date: new Date(snap.timestamp).toLocaleDateString(),
    Price: snap.price,
    MRP: snap.mrp_shown
  }));

  const getStatusBadge = (status) => {
    switch (status) {
      case 'PENDING': return <span className="bg-amber-50 border border-amber-100 text-amber-700 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider">Pending</span>;
      case 'SCRAPING': return <span className="bg-indigo-50 border border-indigo-100 text-indigo-700 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider">Scraping...</span>;
      case 'FAILED': return <span className="bg-rose-50 border border-rose-100 text-rose-700 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider">Failed</span>;
      case 'SUCCESS': return <span className="bg-emerald-50 border border-emerald-100 text-emerald-700 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider">Success</span>;
      default: return null;
    }
  };

  return (
    <>
      <div className="lg:col-span-8 bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 lg:p-8 flex flex-col min-h-[520px]">
        <div className="flex flex-col md:flex-row md:justify-between md:items-start gap-4 mb-4 shrink-0">
          <div className="flex gap-4 flex-1 min-w-0">
            {data.product.image_url && (
              <div className="w-20 h-20 shrink-0 rounded-lg overflow-hidden border border-slate-200 bg-white flex items-center justify-center p-1">
                <img src={data.product.image_url} alt={data.product.title} className="w-full h-full object-contain" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <h2 className="text-2xl lg:text-3xl font-extrabold text-slate-900 m-0 flex items-center gap-2 truncate tracking-tight mb-3">
                {data.product.title}
              </h2>
              <div className="flex flex-wrap gap-2 mb-3 items-center">
                {getStatusBadge(data.product.status)}
                {data.is_fake_discount && <span className="bg-rose-50 border border-rose-200 text-rose-700 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-1">⚠️ Fake Deal</span>}
                {!data.is_fake_discount && data.product.status === 'SUCCESS' && <span className="bg-emerald-50 border border-emerald-200 text-emerald-700 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-1">✅ Real Deal</span>}
              </div>
              <p className="text-slate-500 m-0 text-sm font-medium">Platform: <span className="text-slate-800">{data.product.platform.toUpperCase()}</span> • ID: <span className="text-slate-800">{data.product.product_id}</span></p>
              
              {data.history.length > 0 && (
                <p className="text-slate-400 mt-2 text-xs font-medium">
                  {(() => {
                    const latest = data.history[data.history.length - 1];
                    const diff = new Date() - new Date(latest.timestamp);
                    const minutes = Math.floor(diff / 60000);
                    const hours = Math.floor(minutes / 60);
                    const days = Math.floor(hours / 24);
                    if (days > 1) return `Updated ${days} days ago`;
                    if (days === 1) return `Updated yesterday`;
                    if (hours > 0) return `Updated ${hours} hour${hours > 1 ? 's' : ''} ago`;
                    if (minutes > 0) return `Updated ${minutes} minute${minutes > 1 ? 's' : ''} ago`;
                    return `Updated just now`;
                  })()}
                </p>
              )}
            </div>
          </div>
          <div className="flex flex-col gap-2 shrink-0">
            {data.product.status === 'FAILED' && (
              <button 
                onClick={handleRetry} 
                className="bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-300 px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors w-full"
              >
                Retry Scrape
              </button>
            )}
            <a 
              href={`${API_BASE_URL}/products/${data.product.id}/export`}
              download
              className="bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors w-full text-center"
            >
              Export CSV
            </a>
            <button 
              onClick={handleDelete} 
              disabled={isDeleting}
              className="bg-rose-50 text-rose-600 hover:bg-rose-100 border border-rose-200 px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50 w-full"
            >
              {isDeleting ? 'Deleting...' : 'Delete Product'}
            </button>
          </div>
        </div>
        
        {data.statistics && data.history.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-slate-50 border border-slate-100 rounded-xl p-3 md:p-4">
              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Current Price</div>
              <div className="text-lg sm:text-2xl font-extrabold text-slate-900 truncate">₹{data.statistics.current_price}</div>
            </div>
            <div className="bg-slate-50 border border-slate-100 rounded-xl p-3 md:p-4">
              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Lowest Ever</div>
              <div className="text-lg sm:text-2xl font-extrabold text-emerald-600 truncate">₹{data.statistics.lowest_price}</div>
            </div>
            <div className="bg-slate-50 border border-slate-100 rounded-xl p-3 md:p-4">
              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Average</div>
              <div className="text-lg sm:text-2xl font-extrabold text-indigo-600 truncate">₹{data.statistics.average_price}</div>
            </div>
            <div className="bg-slate-50 border border-slate-100 rounded-xl p-3 md:p-4">
              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Highest Ever</div>
              <div className="text-lg sm:text-2xl font-extrabold text-rose-600 truncate">₹{data.statistics.highest_price}</div>
            </div>
          </div>
        )}
        
        {data.deal_score && data.trend && data.history.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl p-5 text-white flex justify-between items-center shadow-md">
              <div>
                <div className="text-indigo-100 text-sm font-bold uppercase tracking-wider mb-1">Deal Score</div>
                <div className="text-3xl font-extrabold">{data.deal_score.deal_score} / 100</div>
                <div className="text-sm font-medium mt-1">{data.deal_score.deal_reason}</div>
              </div>
              <div className="text-3xl tracking-widest">{data.deal_score.deal_rating}</div>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-5 flex flex-col justify-center shadow-sm">
              <div className="text-slate-500 text-sm font-bold uppercase tracking-wider mb-1">Recent Trend</div>
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xl font-extrabold ${data.trend.trend === 'DOWN' ? 'text-emerald-500' : data.trend.trend === 'UP' ? 'text-rose-500' : 'text-slate-700'}`}>
                  {data.trend.trend === 'DOWN' ? 'Trending Down 📉' : data.trend.trend === 'UP' ? 'Trending Up 📈' : 'Stable Pricing ⚖️'}
                </span>
              </div>
              <div className="text-slate-600 text-sm font-medium">{data.trend.explanation}</div>
            </div>
          </div>
        )}
        
        {data.history.length === 0 ? (
          <div className="flex-1 flex items-center justify-center p-10 text-center bg-slate-50 border border-slate-100 rounded-xl text-slate-500 min-h-0">
            {data.product.status === 'FAILED' ? 'Scraping failed for this product. Check if the URL is valid.' : 'No price history available yet. The background scraper is fetching data...'}
          </div>
        ) : (
          <div className="flex-1 w-full min-h-0 mt-4 flex flex-col">
            <div className="flex-1 min-h-0">
              <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}} dy={10} />
                <YAxis domain={['auto', 'auto']} axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}} dx={-10} />
                <Tooltip 
                  contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)' }}
                />
                <Legend wrapperStyle={{ paddingTop: '20px' }} />
                <Line type="monotone" dataKey="Price" stroke="#4f46e5" strokeWidth={3} dot={{r: 4, strokeWidth: 2}} activeDot={{r: 6}} />
                <Line type="monotone" dataKey="MRP" stroke="#94a3b8" strokeWidth={2} strokeDasharray="5 5" dot={false} />
              </LineChart>
            </ResponsiveContainer>
            </div>
            {data.history.length === 1 && (
              <p className="text-center mt-3 text-sm text-slate-500 italic shrink-0">
                Tracking started today. Historical line graph will build automatically as daily checks run.
              </p>
            )}
          </div>
        )}
      </div>

      {/* Alert Section */}
      {data.product.status !== 'PENDING' && (
      <div className="lg:col-span-12 bg-white rounded-2xl shadow-sm border border-slate-200 p-6 lg:p-8">
        <h3 className="text-xl font-bold mb-6 text-slate-900 tracking-tight">WhatsApp Price Alerts</h3>
        <div className="flex flex-col lg:flex-row gap-10">
          <form onSubmit={handleAddAlert} className="flex flex-col gap-5 flex-1 min-w-[300px]">
            <div>
              <label className="block mb-1 font-semibold text-slate-700 text-sm">WhatsApp Number</label>
              <p className="text-xs text-slate-500 mb-2">Include country code (+91 for India)</p>
              <input 
                type="text" 
                value={phoneNumber} 
                onChange={e => setPhoneNumber(e.target.value)} 
                placeholder="+919876543210"
                className="w-full p-3.5 rounded-xl border border-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all shadow-sm"
                required 
              />
            </div>
            <div>
              <label className="block mb-2 font-semibold text-slate-700 text-sm">Target Price (₹)</label>
              <input 
                type="number" 
                value={thresholdPrice} 
                onChange={e => setThresholdPrice(e.target.value)} 
                placeholder="e.g. 50000"
                className="w-full p-3.5 rounded-xl border border-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all shadow-sm"
                required 
                min="1"
              />
            </div>
            <button type="submit" disabled={isSettingAlert} className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3.5 px-4 rounded-xl transition-all shadow-md shadow-indigo-200 disabled:opacity-50 w-full mt-2">
              {isSettingAlert ? 'Setting Alert...' : 'Set Alert'}
            </button>
          </form>

          <div className="flex-1 min-w-[300px]">
            <h4 className="text-sm uppercase tracking-wider font-bold mb-4 text-slate-500">Active / Triggered Alerts</h4>
            {alerts.length === 0 ? (
              <div className="flex items-center justify-center h-full min-h-[150px] bg-white rounded-xl border border-slate-200 border-dashed">
                <p className="text-slate-400 font-medium text-sm">No alerts set for this product.</p>
              </div>
            ) : (
              <ul className="flex flex-col gap-3 m-0 p-0 list-none">
                {alerts.map(a => (
                  <li key={a.id} className="bg-white p-4 rounded-xl border border-slate-200 flex justify-between items-center shadow-sm">
                    <div>
                      <strong className="text-xl font-bold text-slate-800">₹{a.threshold_price}</strong>
                      <div className="text-slate-500 text-sm mt-0.5 font-medium">{a.phone_number}</div>
                    </div>
                    {a.status === 'ACTIVE' && <span className="bg-indigo-50 text-indigo-700 border border-indigo-100 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider">Active</span>}
                    {a.status === 'TRIGGERED' && <span className="bg-emerald-50 text-emerald-700 border border-emerald-100 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider">Triggered</span>}
                    {a.status === 'FAILED' && <span className="bg-rose-50 text-rose-700 border border-rose-100 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider">Failed</span>}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
      )}
    </>
  );
}

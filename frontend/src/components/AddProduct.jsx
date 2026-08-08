import React, { useState } from 'react';
import apiClient from '../apiClient';
import { PlusCircle } from 'lucide-react';

export default function AddProduct({ onProductAdded, showToast }) {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const isValidUrl = (string) => {
    try {
      let urlToTest = (string || '').trim();
      if (!urlToTest) return false;
      if (!/^https?:\/\//i.test(urlToTest)) {
        urlToTest = 'https://' + urlToTest;
      }
      const parsed = new URL(urlToTest);
      const host = (parsed.hostname || '').toLowerCase();
      if (!host) return false;

      const allowedAmazon = ['amazon.in', 'amzn.in', 'amzn.to'];
      const allowedFlipkart = ['flipkart.com', 'dl.flipkart.com', 'fkrt.it'];

      const isAmazon = allowedAmazon.some(d => host === d || host.endsWith('.' + d));
      const isFlipkart = allowedFlipkart.some(d => host === d || host.endsWith('.' + d));

      return isAmazon || isFlipkart;
    } catch (_) {
      return false;
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const cleanUrl = url.trim();
    if (!cleanUrl) return;

    if (!isValidUrl(cleanUrl)) {
      const msg = 'Please enter a valid Amazon India (amazon.in, amzn.in) or Flipkart (flipkart.com) product URL.';
      setError(msg);
      if (showToast) showToast(msg, 'warning');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.post(`/products/track`, { url: cleanUrl });
      onProductAdded(response.data);
      setUrl('');
      if (showToast) showToast('Product added for tracking!', 'success');
    } catch (err) {
      const msg = err.customMessage || 'Failed to add product for tracking.';
      setError(msg);
      if (showToast) showToast(msg, err.customType || 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="shadow-xl shadow-indigo-100/50 dark:shadow-none border border-indigo-100 dark:border-slate-700/80 bg-white/90 dark:bg-slate-800/90 backdrop-blur-md rounded-2xl p-4 md:p-6 max-w-3xl mx-auto transition-colors">
      <form onSubmit={handleSubmit} className="flex flex-col md:flex-row gap-3">
        <div className="flex-1 space-y-1">
          <label htmlFor="product-url-input" className="sr-only">Product URL</label>
          <input
            id="product-url-input"
            type="url"
            value={url}
            maxLength={1000}
            onChange={(e) => { setUrl(e.target.value); setError(null); }}
            placeholder="Paste Amazon.in or Flipkart URL here (e.g. amzn.in/...)..."
            className={`w-full px-5 py-4 rounded-xl border outline-none transition-all text-slate-800 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 bg-white dark:bg-slate-900/80 shadow-sm text-sm ${
              error ? 'border-rose-300 dark:border-rose-500 focus:border-rose-500 focus:ring-2 focus:ring-rose-100 dark:focus:ring-rose-950' : 'border-slate-200 dark:border-slate-700 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:focus:ring-indigo-950'
            }`}
            required
          />
          <p className="text-[11px] text-slate-500 dark:text-slate-400 text-left px-2">
            Supports <span className="font-semibold text-slate-700 dark:text-slate-300">amazon.in</span>, <span className="font-semibold text-slate-700 dark:text-slate-300">amzn.in</span>, and <span className="font-semibold text-slate-700 dark:text-slate-300">flipkart.com</span> products.
          </p>
        </div>
        <button 
          type="submit" 
          disabled={loading || !url.trim()} 
          className="bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 text-white font-bold py-3 px-6 md:py-4 md:px-8 rounded-xl transition-all shadow-md shadow-indigo-200 dark:shadow-none flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shrink-0 w-full md:w-auto h-[52px] focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 dark:focus:ring-offset-slate-900"
        >
          {loading ? (
            <>
              <svg className="w-5 h-5 animate-spin text-white" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <span>Tracking...</span>
            </>
          ) : (
            <>
              <PlusCircle size={20} aria-hidden="true" />
              <span>Track Deal</span>
            </>
          )}
        </button>
      </form>
      {error && <p className="text-rose-600 dark:text-rose-400 mt-2 text-xs font-semibold px-2 text-left">{error}</p>}
    </div>
  );
}

import React, { useState } from 'react';
import axios from 'axios';
import { PlusCircle } from 'lucide-react';
import { API_BASE_URL } from '../config';

export default function AddProduct({ onProductAdded, showToast }) {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post(`${API_BASE_URL}/products/track`, { url });
      onProductAdded(response.data);
      setUrl('');
      if (showToast) showToast('Product added for tracking!', 'success');
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to add product';
      setError(msg);
      if (showToast) showToast(msg, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="shadow-xl shadow-indigo-100/50 border border-indigo-100 bg-white/80 backdrop-blur-md rounded-2xl p-4 md:p-6 max-w-3xl mx-auto">
      <form onSubmit={handleSubmit} className="flex flex-col md:flex-row gap-3">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste Amazon.in or Flipkart URL here..."
          className="flex-1 px-5 py-4 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all text-slate-700 placeholder-slate-400 bg-white shadow-sm"
          required
        />
        <button 
          type="submit" 
          disabled={loading} 
          className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 px-4 md:py-4 md:px-8 rounded-xl transition-all shadow-md shadow-indigo-200 flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed shrink-0 w-full md:w-auto"
        >
          {loading ? 'Tracking...' : <><PlusCircle size={20} /> Track Deal</>}
        </button>
      </form>
      {error && <p className="text-rose-500 mt-3 text-sm font-medium px-2">{error}</p>}
    </div>
  );
}

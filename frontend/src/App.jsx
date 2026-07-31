import React, { useState, useEffect } from 'react';
import axios from 'axios';
import AddProduct from './components/AddProduct';
import ProductDashboard from './components/ProductDashboard';
import { API_BASE_URL } from './config';
import './index.css';

function App() {
  const [products, setProducts] = useState([]);
  const [selectedProductId, setSelectedProductId] = useState(null);
  
  // Search & Pagination States
  const [searchQuery, setSearchQuery] = useState('');
  const [platformFilter, setPlatformFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pagination, setPagination] = useState({ total_pages: 1, has_next: false, has_previous: false, total_products: 0 });
  
  const handleProductSelect = (id) => {
    setSelectedProductId(id);
    if (window.innerWidth < 1024) {
      setTimeout(() => {
        document.getElementById('product-dashboard-container')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 50);
    }
  };
  
  const [metrics, setMetrics] = useState(null);
  const [toast, setToast] = useState({ message: '', type: 'error', visible: false });

  const showToast = (message, type = 'error') => {
    setToast({ message, type, visible: true });
    setTimeout(() => {
      setToast(prev => ({ ...prev, visible: false }));
    }, 4000);
  };

  const availableCategories = Array.from(new Set(
    products
      .map(p => p.category)
      .filter(cat => cat && typeof cat === 'string' && cat.trim() !== '')
  )).sort();

  useEffect(() => {
    fetchProducts();
  }, [currentPage, platformFilter, categoryFilter]);

  useEffect(() => {
    axios.get(`${API_BASE_URL}/metrics`)
      .then(res => setMetrics(res.data))
      .catch(err => {
        console.error("Error fetching metrics:", err);
        showToast('Network failure while fetching metrics.', 'error');
      });
  }, []);

  const fetchProducts = () => {
    const params = new URLSearchParams({
      q: searchQuery,
      platform: platformFilter,
      category: categoryFilter,
      page: currentPage,
      page_size: 50
    });
    
    axios.get(`${API_BASE_URL}/products/search/?${params.toString()}`)
      .then(res => {
        setProducts(res.data.products || []);
        setPagination(res.data.pagination || { total_pages: 1, has_next: false, has_previous: false, total_products: 0 });
        if (res.data.products && res.data.products.length > 0 && !selectedProductId) {
          setSelectedProductId(res.data.products[0].id);
        }
      })
      .catch(err => {
        console.error("Error fetching products:", err);
        showToast('Network failure while fetching products.', 'error');
      });
  };
  
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setCurrentPage(1);
    fetchProducts();
  };

  const handleProductAdded = (newProduct) => {
    fetchProducts();
    handleProductSelect(newProduct.id);
  };

  const handleProductDeleted = () => {
    setSelectedProductId(null);
    fetchProducts();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 text-slate-800 font-sans">
      {/* Hero Section */}
      <div className="pt-16 pb-12 px-4 text-center max-w-4xl mx-auto">
        <h1 className="text-4xl md:text-5xl font-extrabold text-slate-900 mb-4 tracking-tight">
          Smart Price Tracking & <span className="text-indigo-600">Fake Discount Shield</span>
        </h1>
        <p className="text-lg md:text-xl text-slate-600 mb-10 font-medium max-w-2xl mx-auto">
          Track real price trends across Amazon & Flipkart. Never fall for inflated discounts again.
        </p>
        
        <div className="relative z-10">
          <AddProduct onProductAdded={handleProductAdded} showToast={showToast} />
        </div>
        
        <div className="flex flex-wrap justify-center gap-6 mt-8 text-sm font-medium text-slate-600">
          <span className="flex items-center gap-2 bg-white/60 px-3 py-1.5 rounded-full border border-slate-200">⚡ Real-time alerts</span>
          <span className="flex items-center gap-2 bg-white/60 px-3 py-1.5 rounded-full border border-slate-200">🛡️ Fake deal detection</span>
          <span className="flex items-center gap-2 bg-white/60 px-3 py-1.5 rounded-full border border-slate-200">📈 Multi-platform support</span>
        </div>

        {metrics && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-8 w-full max-w-3xl mx-auto">
            <div className="bg-white/80 backdrop-blur-sm px-6 py-4 rounded-xl border border-slate-200/60 shadow-sm text-center">
              <div className="text-sm text-slate-500 font-bold uppercase tracking-wider mb-1">Products Tracking</div>
              <div className="text-2xl font-extrabold text-indigo-600">{metrics.total_products}</div>
            </div>
            <div className="bg-white/80 backdrop-blur-sm px-6 py-4 rounded-xl border border-slate-200/60 shadow-sm text-center">
              <div className="text-sm text-slate-500 font-bold uppercase tracking-wider mb-1">Active Alerts</div>
              <div className="text-2xl font-extrabold text-rose-500">{metrics.active_alerts}</div>
            </div>
            <div className="bg-white/80 backdrop-blur-sm px-6 py-4 rounded-xl border border-slate-200/60 shadow-sm text-center">
              <div className="text-sm text-slate-500 font-bold uppercase tracking-wider mb-1">Successful Scrapes</div>
              <div className="text-2xl font-extrabold text-emerald-500">{metrics.successful_scrapes}</div>
            </div>
          </div>
        )}
      </div>

      <div className="max-w-7xl mx-auto px-4 pb-16 w-full">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Sidebar */}
          <div className="lg:col-span-4">
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 sticky top-6 h-[520px] flex flex-col">
              <div className="flex flex-col gap-3 mb-5 border-b border-slate-100 pb-4 shrink-0">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg font-bold text-slate-800 m-0">Tracked Products</h3>
                  <span className="bg-slate-100 text-slate-600 text-xs font-bold px-2.5 py-1 rounded-full">
                    {pagination.total_products} Items
                  </span>
                </div>
                
                <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-2">
                  <input 
                    type="text" 
                    placeholder="Search title or brand..." 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="flex-1 p-2.5 sm:p-2 border border-slate-200 rounded-lg text-sm"
                  />
                  <button type="submit" className="bg-slate-100 hover:bg-slate-200 px-4 py-2.5 sm:px-3 sm:py-2 rounded-lg text-sm font-semibold w-full sm:w-auto">🔍 Search</button>
                </form>
                
                <div className="flex flex-col sm:flex-row gap-2">
                  <select 
                    value={platformFilter} 
                    onChange={(e) => { setPlatformFilter(e.target.value); setCurrentPage(1); }}
                    className="flex-1 p-2.5 sm:p-2 border border-slate-200 rounded-lg text-sm bg-white"
                  >
                    <option value="">All Platforms</option>
                    <option value="amazon">Amazon</option>
                    <option value="flipkart">Flipkart</option>
                  </select>
                  <select 
                    value={categoryFilter} 
                    onChange={(e) => { setCategoryFilter(e.target.value); setCurrentPage(1); }}
                    className="flex-1 p-2.5 sm:p-2 border border-slate-200 rounded-lg text-sm bg-white"
                  >
                    <option value="">All Categories</option>
                    {availableCategories.map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>
              </div>
              
              <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar flex flex-col gap-2 min-h-0">
                {products.length === 0 && (
                  <p className="text-slate-500 text-sm italic text-center py-4">No products tracked yet.</p>
                )}
                {products.map(p => (
                  <div 
                    key={p.id} 
                    onClick={() => handleProductSelect(p.id)}
                    className={`flex flex-col p-3 cursor-pointer rounded-xl border transition-all duration-200 hover:-translate-y-0.5 hover:shadow-sm shrink-0 ${
                      selectedProductId === p.id 
                        ? 'bg-indigo-50/80 text-indigo-900 border-l-4 border-l-indigo-600 border-t-indigo-100 border-r-indigo-100 border-b-indigo-100 shadow-sm' 
                        : 'border-slate-100 bg-white hover:bg-slate-50 hover:border-slate-200'
                    }`}
                    title={p.title}
                  >
                    <div className="flex items-start gap-3 mb-1.5">
                      {p.image_url && (
                        <div className="w-10 h-10 shrink-0 rounded-md overflow-hidden border border-slate-200 bg-white flex items-center justify-center">
                          <img src={p.image_url} alt={p.title} className="w-full h-full object-contain" />
                        </div>
                      )}
                      <div className="flex flex-col min-w-0 flex-1">
                        <div className="flex items-start gap-2">
                          <span className="shrink-0 mt-0.5">
                            {p.status === 'PENDING' || p.status === 'SCRAPING' ? <span className="inline-block animate-pulse">⏳</span> : ''}
                            {p.status === 'FAILED' ? '❌' : ''}
                            {p.status === 'SUCCESS' ? '✅' : ''}
                          </span>
                          <span className="truncate text-sm font-semibold text-slate-800">
                            {p.title}
                          </span>
                        </div>
                        {p.brand && <span className="text-xs text-slate-500 truncate ml-6">{p.brand}</span>}
                      </div>
                    </div>
                    <div className="flex gap-2 ml-6">
                      <span className="bg-slate-100 text-slate-600 text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full">
                        {p.platform}
                      </span>
                      {p.status === 'SUCCESS' ? (
                        <span className="bg-emerald-50 text-emerald-700 text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full border border-emerald-100">
                          Active
                        </span>
                      ) : p.status === 'FAILED' ? (
                        <span className="bg-rose-50 text-rose-700 text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full border border-rose-100">
                          Error
                        </span>
                      ) : (
                        <span className="bg-amber-50 text-amber-700 text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full border border-amber-100">
                          Pending
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="flex justify-between items-center pt-4 border-t border-slate-100 mt-2 shrink-0">
                <button 
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={!pagination.has_previous}
                  className="px-4 py-2.5 bg-white border border-slate-200 rounded-lg text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition-colors"
                >
                  Previous
                </button>
                <span className="text-xs font-semibold text-slate-500">
                  Page {pagination.current_page} of {pagination.total_pages}
                </span>
                <button 
                  onClick={() => setCurrentPage(p => p + 1)}
                  disabled={!pagination.has_next}
                  className="px-4 py-2.5 bg-white border border-slate-200 rounded-lg text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
          
          {/* Main Content */}
          <div id="product-dashboard-container" className="lg:col-span-8 scroll-mt-6">
            <ProductDashboard 
              productId={selectedProductId} 
              onProductDeleted={handleProductDeleted}
              showToast={showToast}
            />
          </div>
        </div>
      </div>
      
      {/* Toast Notification */}
      {toast.visible && (
        <div className={`fixed bottom-6 right-6 z-50 px-6 py-3 rounded-lg shadow-xl font-medium text-white transition-opacity duration-300 ${toast.type === 'error' ? 'bg-rose-600' : 'bg-emerald-600'}`}>
          {toast.message}
        </div>
      )}
    </div>
  );
}

export default App;

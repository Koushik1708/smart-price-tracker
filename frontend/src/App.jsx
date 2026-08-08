import React, { useState, useEffect, useContext, useCallback, lazy, Suspense } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import apiClient from './apiClient';
import AddProduct from './components/AddProduct';
import ProductDashboard from './components/ProductDashboard';
import Login from './components/Login';
import Register from './components/Register';
import ProtectedRoute from './components/ProtectedRoute';
import DashboardOverview from './components/DashboardOverview';
import ErrorBoundary from './components/ErrorBoundary';
import Toast from './components/common/Toast';
import EmptyState from './components/common/EmptyState';
import { ProductCardSkeleton } from './components/common/Skeletons';
import { AuthContext } from './AuthContext';
import { useTheme } from './ThemeContext';
import { Sun, Moon } from 'lucide-react';
import './index.css';

const AdminPanel = lazy(() => import('./components/AdminPanel'));

function Dashboard() {
  const { user, logout } = useContext(AuthContext);
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const handleLogout = () => {
    showToast('Logged out successfully.', 'info');
    logout();
    navigate('/login');
  };

  const [products, setProducts] = useState([]);
  const [selectedProductId, setSelectedProductId] = useState(null);
  const [isProductsLoading, setIsProductsLoading] = useState(true);
  
  // Search & Pagination States
  const [searchQuery, setSearchQuery] = useState('');
  const [platformFilter, setPlatformFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pagination, setPagination] = useState({ total_pages: 1, has_next: false, has_previous: false, total_products: 0 });
  
  const [activeView, setActiveView] = useState('dashboard'); // 'dashboard', 'products', 'admin'
  const [metrics, setMetrics] = useState(null);
  const [toast, setToast] = useState({ message: '', type: 'info', visible: false });

  const showToast = useCallback((message, type = 'info') => {
    setToast({ message, type, visible: true });
    setTimeout(() => {
      setToast(prev => ({ ...prev, visible: false }));
    }, 5000);
  }, []);

  const availableCategories = Array.from(new Set(
    products
      .map(p => p.category)
      .filter(cat => cat && typeof cat === 'string' && cat.trim() !== '')
  )).sort();

  const fetchMetrics = useCallback(() => {
    apiClient.get('/metrics')
      .then(res => setMetrics(res.data))
      .catch(err => {
        console.error("Error fetching metrics:", err);
      });
  }, []);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  const fetchProducts = useCallback(() => {
    setIsProductsLoading(true);
    const params = new URLSearchParams({
      q: searchQuery,
      platform: platformFilter,
      category: categoryFilter,
      page: currentPage,
      page_size: 50
    });
    
    apiClient.get(`/products/search/?${params.toString()}`)
      .then(res => {
        const fetchedProducts = res.data.products || [];
        setProducts(fetchedProducts);
        setPagination(res.data.pagination || { total_pages: 1, has_next: false, has_previous: false, total_products: 0 });
        if (fetchedProducts.length > 0 && !selectedProductId) {
          setSelectedProductId(fetchedProducts[0].id);
        }
      })
      .catch(err => {
        console.error("Error fetching products:", err);
        if (err.customType === 'network' || err.customType === 'timeout') {
          showToast(err.customMessage, 'error');
        }
      })
      .finally(() => {
        setIsProductsLoading(false);
      });
  }, [searchQuery, platformFilter, categoryFilter, currentPage, selectedProductId, showToast]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  const handleProductSelect = (id) => {
    setSelectedProductId(id);
    if (window.innerWidth < 1024) {
      setTimeout(() => {
        document.getElementById('product-dashboard-container')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 50);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setCurrentPage(1);
    fetchProducts();
  };

  const handleProductAdded = (newProduct) => {
    showToast(`Product added for tracking!`, 'success');
    if (newProduct && newProduct.id) {
      setProducts(prev => [newProduct, ...prev.filter(p => p.id !== newProduct.id)]);
      setPagination(prev => ({ ...prev, total_products: (prev.total_products || 0) + 1 }));
      handleProductSelect(newProduct.id);
    }
    fetchProducts();
    fetchMetrics();
  };

  const handleProductDeleted = (deletedId) => {
    setProducts(prev => prev.filter(p => p.id !== (deletedId || selectedProductId)));
    if (selectedProductId === deletedId || !deletedId) {
      setSelectedProductId(null);
    }
    fetchProducts();
    fetchMetrics();
  };

  // Real-Time Synchronizer Callback from ProductDashboard
  const handleProductUpdated = useCallback((updatedProduct) => {
    if (!updatedProduct || !updatedProduct.id) return;
    setProducts(prev => prev.map(p => p.id === updatedProduct.id ? { ...p, ...updatedProduct } : p));
    fetchMetrics();
  }, [fetchMetrics]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 text-slate-800 dark:text-slate-200 font-sans transition-colors">
      {/* Top Navigation Bar */}
      <div className="sticky top-0 z-30 backdrop-blur-md bg-white/80 dark:bg-slate-900/80 border-b border-slate-200/80 dark:border-slate-700/80">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-indigo-600 text-white rounded-lg flex items-center justify-center font-black text-sm shadow-sm">SP</div>
            <span className="text-sm font-bold text-slate-800 dark:text-slate-100 hidden sm:inline">Smart Price Tracker</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={toggleTheme}
              className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500"
              aria-label="Toggle light and dark mode"
            >
              {theme === 'dark' ? <Sun size={16} className="text-amber-400" /> : <Moon size={16} className="text-indigo-600" />}
            </button>
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-xs font-bold">
                {user?.name?.[0]?.toUpperCase() || 'U'}
              </div>
              <span className="text-sm font-semibold text-slate-700 dark:text-slate-300 hidden sm:inline">{user?.name}</span>
            </div>
            <button 
              onClick={handleLogout}
              className="text-xs font-semibold text-slate-500 dark:text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 border border-slate-200 dark:border-slate-700 px-2.5 py-1.5 rounded-lg transition-colors"
            >
              Logout
            </button>
          </div>
        </div>
      </div>

      {/* Hero Section */}
      <div className="pt-12 pb-10 px-4 text-center max-w-4xl mx-auto">
        <h1 className="text-4xl md:text-5xl font-extrabold text-slate-900 dark:text-slate-50 mb-4 tracking-tight">
          Smart Price Tracking & <span className="text-indigo-600 dark:text-indigo-400">Fake Discount Shield</span>
        </h1>
        <p className="text-lg md:text-xl text-slate-600 dark:text-slate-400 font-medium mb-8">
          Welcome, <span className="font-bold text-indigo-600 dark:text-indigo-400">{user?.name}</span>! Track real price trends.
        </p>
        
        <div className="relative z-10">
          <AddProduct onProductAdded={handleProductAdded} showToast={showToast} />
        </div>
        
        <div className="flex flex-wrap justify-center gap-6 mt-8 text-sm font-medium text-slate-600 dark:text-slate-400">
          <span className="flex items-center gap-2 bg-white/60 dark:bg-slate-800/60 px-3 py-1.5 rounded-full border border-slate-200 dark:border-slate-700">⚡ Real-time alerts</span>
          <span className="flex items-center gap-2 bg-white/60 dark:bg-slate-800/60 px-3 py-1.5 rounded-full border border-slate-200 dark:border-slate-700">🛡️ Fake deal detection</span>
          <span className="flex items-center gap-2 bg-white/60 dark:bg-slate-800/60 px-3 py-1.5 rounded-full border border-slate-200 dark:border-slate-700">📈 Multi-platform support</span>
        </div>

        {metrics && activeView === 'products' && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-8 w-full max-w-3xl mx-auto">
            <div className="bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm px-6 py-4 rounded-xl border border-slate-200/60 dark:border-slate-700/60 shadow-sm text-center">
              <div className="text-xs text-slate-500 dark:text-slate-400 font-bold uppercase tracking-wider mb-1">Products Tracking</div>
              <div className="text-2xl font-extrabold text-indigo-600 dark:text-indigo-400">{metrics.total_products}</div>
            </div>
            <div className="bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm px-6 py-4 rounded-xl border border-slate-200/60 dark:border-slate-700/60 shadow-sm text-center">
              <div className="text-xs text-slate-500 dark:text-slate-400 font-bold uppercase tracking-wider mb-1">Active Alerts</div>
              <div className="text-2xl font-extrabold text-rose-500 dark:text-rose-400">{metrics.active_alerts}</div>
            </div>
            <div className="bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm px-6 py-4 rounded-xl border border-slate-200/60 dark:border-slate-700/60 shadow-sm text-center">
              <div className="text-xs text-slate-500 dark:text-slate-400 font-bold uppercase tracking-wider mb-1">Successful Scrapes</div>
              <div className="text-2xl font-extrabold text-emerald-500 dark:text-emerald-400">{metrics.successful_scrapes}</div>
            </div>
          </div>
        )}
      </div>

      {/* Navigation Tabs */}
      <div className="max-w-7xl mx-auto px-4 mb-6">
        <div className="flex border-b border-slate-200 dark:border-slate-700">
          <button 
            onClick={() => setActiveView('dashboard')}
            className={`px-6 py-3 font-semibold text-sm transition-colors border-b-2 ${activeView === 'dashboard' ? 'border-indigo-600 dark:border-indigo-400 text-indigo-600 dark:text-indigo-400' : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 hover:border-slate-300 dark:hover:border-slate-600'}`}
          >
            📊 Dashboard Overview
          </button>
          <button 
            onClick={() => setActiveView('products')}
            className={`px-6 py-3 font-semibold text-sm transition-colors border-b-2 ${activeView === 'products' ? 'border-indigo-600 dark:border-indigo-400 text-indigo-600 dark:text-indigo-400' : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 hover:border-slate-300 dark:hover:border-slate-600'}`}
          >
            📦 Tracked Products
          </button>
          {user?.is_admin && (
            <button 
              onClick={() => setActiveView('admin')}
              className={`px-6 py-3 font-semibold text-sm transition-colors border-b-2 ${activeView === 'admin' ? 'border-indigo-600 dark:border-indigo-400 text-indigo-600 dark:text-indigo-400 font-bold' : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 hover:border-slate-300 dark:hover:border-slate-600'}`}
            >
              🛡️ Admin Panel
            </button>
          )}
        </div>
      </div>

      {/* Main View Area */}
      <div className="max-w-7xl mx-auto px-4 pb-16 w-full">
        {activeView === 'dashboard' ? (
          <ErrorBoundary>
            <DashboardOverview 
              onNavigate={(view) => {
                if (view === 'products' || view === 'alerts') setActiveView('products');
              }} 
              showToast={showToast}
              onMetricsChanged={fetchMetrics}
            />
          </ErrorBoundary>
        ) : activeView === 'admin' ? (
          <ErrorBoundary>
            <Suspense fallback={<div className="text-center py-12 font-semibold text-slate-500 dark:text-slate-400">Loading Admin Panel...</div>}>
              <AdminPanel showToast={showToast} />
            </Suspense>
          </ErrorBoundary>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Sidebar */}
          <div className="lg:col-span-4">
            <div className="bg-white dark:bg-slate-800/90 rounded-2xl shadow-sm border border-slate-200/80 dark:border-slate-700/80 p-5 sticky top-20 h-[560px] flex flex-col transition-colors">
              <div className="flex flex-col gap-3 mb-4 border-b border-slate-100 dark:border-slate-700/60 pb-4 shrink-0">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 m-0">Tracked Products</h3>
                  <span className="bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs font-bold px-2.5 py-1 rounded-full">
                    {pagination.total_products} Items
                  </span>
                </div>
                
                <form onSubmit={handleSearchSubmit} className="flex gap-2">
                  <input 
                    type="text" 
                    placeholder="Search title or brand..." 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="flex-1 p-2 border border-slate-200 dark:border-slate-700 rounded-lg text-sm outline-none focus:border-indigo-500 dark:focus:border-indigo-500 bg-white dark:bg-slate-900/80 text-slate-800 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 transition-colors"
                  />
                  <button type="submit" className="bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 px-3 py-2 rounded-lg text-sm font-semibold transition-colors">🔍</button>
                </form>
                
                <div className="flex gap-2">
                  <select 
                    value={platformFilter} 
                    onChange={(e) => { setPlatformFilter(e.target.value); setCurrentPage(1); }}
                    className="flex-1 p-2 border border-slate-200 dark:border-slate-700 rounded-lg text-sm bg-white dark:bg-slate-900/80 text-slate-800 dark:text-slate-200 outline-none transition-colors"
                  >
                    <option value="">All Platforms</option>
                    <option value="amazon">Amazon</option>
                    <option value="flipkart">Flipkart</option>
                  </select>
                  <select 
                    value={categoryFilter} 
                    onChange={(e) => { setCategoryFilter(e.target.value); setCurrentPage(1); }}
                    className="flex-1 p-2 border border-slate-200 dark:border-slate-700 rounded-lg text-sm bg-white dark:bg-slate-900/80 text-slate-800 dark:text-slate-200 outline-none transition-colors"
                  >
                    <option value="">All Categories</option>
                    {availableCategories.map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>
              </div>
              
              <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar flex flex-col gap-2 min-h-0">
                {isProductsLoading ? (
                  <>
                    <ProductCardSkeleton />
                    <ProductCardSkeleton />
                    <ProductCardSkeleton />
                  </>
                ) : products.length === 0 ? (
                  <EmptyState 
                    title="No tracked products"
                    description="Track your first product URL above to monitor live prices."
                    actionLabel="Add Product"
                    onAction={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                    className="my-auto py-6"
                  />
                ) : (
                  products.map(p => (
                    <div 
                      key={p.id} 
                      onClick={() => handleProductSelect(p.id)}
                      className={`flex flex-col p-3 cursor-pointer rounded-xl border transition-all duration-200 hover:-translate-y-0.5 hover:shadow-sm shrink-0 ${
                        selectedProductId === p.id 
                          ? 'bg-indigo-50/80 dark:bg-indigo-950/40 text-indigo-900 dark:text-indigo-100 border-l-4 border-l-indigo-600 dark:border-l-indigo-400 border-t-indigo-100 dark:border-t-indigo-900/50 border-r-indigo-100 dark:border-r-indigo-900/50 border-b-indigo-100 dark:border-b-indigo-900/50 shadow-sm' 
                          : 'border-slate-100 dark:border-slate-700/60 bg-white dark:bg-slate-800/60 hover:bg-slate-50 dark:hover:bg-slate-700/60 hover:border-slate-200 dark:hover:border-slate-600'
                      }`}
                      title={p.title}
                    >
                      <div className="flex items-start gap-3 mb-1.5">
                        {p.image_url && (
                          <div className="w-10 h-10 shrink-0 rounded-md overflow-hidden border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 flex items-center justify-center">
                            <img src={p.image_url} alt={p.title} className="w-full h-full object-contain" />
                          </div>
                        )}
                        <div className="flex flex-col min-w-0 flex-1">
                          <div className="flex items-start gap-2">
                            <span className="shrink-0 mt-0.5">
                              {p.status === 'PENDING' || p.status === 'SCRAPING' ? <span className="inline-block animate-pulse">⏳</span> : ''}
                              {p.status === 'FAILED' ? '❌' : ''}
                              {p.status === 'SUCCESS' ? '✅' : ''}
                              {p.status === 'PAUSED' ? '⏸️' : ''}
                            </span>
                            <span className="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">
                              {p.title}
                            </span>
                          </div>
                          {p.brand && <span className="text-xs text-slate-500 dark:text-slate-400 truncate ml-6">{p.brand}</span>}
                        </div>
                      </div>
                      <div className="flex gap-2 ml-6">
                        <span className="bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full">
                          {p.platform}
                        </span>
                        {p.status === 'SUCCESS' ? (
                          <span className="bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-400 text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full border border-emerald-100 dark:border-emerald-900/50">
                            Active
                          </span>
                        ) : p.status === 'PAUSED' ? (
                          <span className="bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full border border-slate-200 dark:border-slate-600">
                            Paused
                          </span>
                        ) : p.status === 'FAILED' ? (
                          <span className="bg-rose-50 dark:bg-rose-950/50 text-rose-700 dark:text-rose-400 text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full border border-rose-100 dark:border-rose-900/50">
                            Error
                          </span>
                        ) : (
                          <span className="bg-amber-50 dark:bg-amber-950/50 text-amber-700 dark:text-amber-400 text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full border border-amber-100 dark:border-amber-900/50">
                            Pending
                          </span>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
              
              <div className="flex justify-between items-center pt-4 border-t border-slate-100 dark:border-slate-700/60 mt-2 shrink-0">
                <button 
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={!pagination.has_previous || isProductsLoading}
                  className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 transition-colors"
                >
                  Previous
                </button>
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                  Page {pagination.current_page} of {pagination.total_pages}
                </span>
                <button 
                  onClick={() => setCurrentPage(p => p + 1)}
                  disabled={!pagination.has_next || isProductsLoading}
                  className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
          
          {/* Main Content */}
          <div id="product-dashboard-container" className="lg:col-span-8 scroll-mt-6">
            <ErrorBoundary>
              <ProductDashboard 
                productId={selectedProductId} 
                onProductDeleted={handleProductDeleted}
                onProductUpdated={handleProductUpdated}
                showToast={showToast}
              />
            </ErrorBoundary>
          </div>
        </div>
        )}
      </div>
      
      {/* Toast Notification */}
      <Toast toast={toast} onClose={() => setToast(prev => ({ ...prev, visible: false }))} />
    </div>
  );
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Dashboard />} />
      </Route>
    </Routes>
  );
}

export default App;

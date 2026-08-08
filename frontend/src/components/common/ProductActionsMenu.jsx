import React, { useState, useRef, useEffect } from 'react';
import apiClient from '../../apiClient';

export default function ProductActionsMenu({
  product,
  onRefresh,
  onDelete,
  onPauseToggle,
  onViewDetails,
  showToast
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isPausing, setIsPausing] = useState(false);
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setIsOpen(false);
        setShowConfirmDelete(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  const handleRefresh = async () => {
    setIsOpen(false);
    setIsRefreshing(true);
    try {
      await apiClient.post(`/products/${product.id}/scrape`);
      if (showToast) showToast('Scrape job triggered for product.', 'info');
      if (onRefresh) onRefresh();
    } catch (err) {
      if (showToast) showToast(err.customMessage || 'Failed to trigger refresh.', 'error');
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleExportCSV = () => {
    setIsOpen(false);
    const downloadUrl = `${apiClient.defaults.baseURL}/products/${product.id}/export`;
    window.open(downloadUrl, '_blank');
    if (showToast) showToast('CSV Export initiated.', 'success');
  };

  const handlePauseToggle = async () => {
    setIsOpen(false);
    setIsPausing(true);
    const newStatus = product.status === 'PAUSED' ? 'PENDING' : 'PAUSED';
    try {
      await apiClient.patch(`/products/${product.id}`, { status: newStatus });
      if (showToast) showToast(`Product tracking ${newStatus === 'PAUSED' ? 'paused' : 'resumed'}.`, 'success');
      if (onPauseToggle) onPauseToggle(newStatus);
    } catch (err) {
      if (showToast) showToast(err.customMessage || 'Failed to update tracking state.', 'error');
    } finally {
      setIsPausing(false);
    }
  };

  const confirmDeleteAction = async () => {
    setShowConfirmDelete(false);
    setIsOpen(false);
    setIsDeleting(true);

    try {
      await apiClient.delete(`/products/${product.id}`);
      if (showToast) showToast('Product deleted successfully.', 'success');
      if (onDelete) onDelete(product.id);
    } catch (err) {
      if (showToast) showToast(err.customMessage || 'Failed to delete product.', 'error');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="relative inline-block text-left" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isDeleting || isRefreshing || isPausing}
        aria-expanded={isOpen}
        aria-haspopup="true"
        className="p-2 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 hover:border-slate-300 dark:hover:border-slate-600 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 flex items-center justify-center text-slate-600 dark:text-slate-300"
        aria-label={`Actions for ${product.title || 'product'}`}
      >
        {isDeleting || isRefreshing || isPausing ? (
          <svg className="w-5 h-5 animate-spin text-indigo-600 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" aria-hidden="true">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        ) : (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
          </svg>
        )}
      </button>

      {isOpen && (
        <div
          role="menu"
          aria-orientation="vertical"
          className="origin-top-right absolute right-0 mt-2 w-48 rounded-2xl shadow-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 ring-1 ring-black ring-opacity-5 z-40 py-1.5 focus:outline-none divide-y divide-slate-100 dark:divide-slate-700/60"
        >
          <div className="py-1" role="none">
            {onViewDetails && (
              <button
                role="menuitem"
                onClick={() => { setIsOpen(false); onViewDetails(product.id); }}
                className="w-full text-left px-4 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-indigo-50 dark:hover:bg-indigo-950/60 hover:text-indigo-600 dark:hover:text-indigo-400 font-semibold flex items-center gap-2 transition-colors"
              >
                👁️ View Details
              </button>
            )}
            <button
              role="menuitem"
              onClick={handleRefresh}
              className="w-full text-left px-4 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-indigo-50 dark:hover:bg-indigo-950/60 hover:text-indigo-600 dark:hover:text-indigo-400 font-semibold flex items-center gap-2 transition-colors"
            >
              🔄 Refresh Now
            </button>
            <button
              role="menuitem"
              onClick={handleExportCSV}
              className="w-full text-left px-4 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-indigo-50 dark:hover:bg-indigo-950/60 hover:text-indigo-600 dark:hover:text-indigo-400 font-semibold flex items-center gap-2 transition-colors"
            >
              📊 Export CSV
            </button>
          </div>

          <div className="py-1" role="none">
            <button
              role="menuitem"
              onClick={handlePauseToggle}
              className="w-full text-left px-4 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-indigo-50 dark:hover:bg-indigo-950/60 hover:text-indigo-600 dark:hover:text-indigo-400 font-semibold flex items-center gap-2 transition-colors"
            >
              {product.status === 'PAUSED' ? '▶️ Resume Tracking' : '⏸️ Pause Tracking'}
            </button>
          </div>

          <div className="py-1" role="none">
            <button
              role="menuitem"
              onClick={() => { setIsOpen(false); setShowConfirmDelete(true); }}
              className="w-full text-left px-4 py-2 text-sm text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/50 font-bold flex items-center gap-2 transition-colors"
            >
              🗑️ Delete Product
            </button>
          </div>
        </div>
      )}

      {/* Modal Confirmation Dialog */}
      {showConfirmDelete && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-modal-title"
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        >
          <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 max-w-sm w-full shadow-2xl border border-slate-200 dark:border-slate-700 text-center space-y-4 animate-in fade-in zoom-in duration-200">
            <div className="w-12 h-12 bg-rose-100 dark:bg-rose-950/80 text-rose-600 dark:text-rose-400 rounded-full flex items-center justify-center mx-auto">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </div>
            <div>
              <h4 id="delete-modal-title" className="text-lg font-bold text-slate-900 dark:text-slate-100">Delete Product?</h4>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                Are you sure you want to delete <span className="font-semibold text-slate-800 dark:text-slate-200">"{product.title}"</span>? All price history and alerts will be permanently removed.
              </p>
            </div>
            <div className="flex gap-3 pt-2">
              <button
                onClick={() => setShowConfirmDelete(false)}
                className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-semibold hover:bg-slate-50 dark:hover:bg-slate-700/60 transition-colors text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
              >
                Cancel
              </button>
              <button
                onClick={confirmDeleteAction}
                className="flex-1 px-4 py-2.5 rounded-xl bg-rose-600 dark:bg-rose-500 hover:bg-rose-700 dark:hover:bg-rose-600 text-white font-bold transition-colors text-sm shadow-md shadow-rose-200 dark:shadow-none focus:outline-none focus:ring-2 focus:ring-rose-500"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

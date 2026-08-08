import React from 'react';

export default function Toast({ toast, onClose }) {
  if (!toast || !toast.visible) return null;

  const typeStyles = {
    error: 'bg-rose-600 dark:bg-rose-700 text-white shadow-rose-900/20 border-rose-500',
    warning: 'bg-amber-500 dark:bg-amber-600 text-white shadow-amber-900/20 border-amber-400',
    info: 'bg-indigo-600 dark:bg-indigo-700 text-white shadow-indigo-900/20 border-indigo-500',
    success: 'bg-emerald-600 dark:bg-emerald-700 text-white shadow-emerald-900/20 border-emerald-500',
  };

  const icons = {
    error: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    success: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    warning: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    info: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  };

  return (
    <div
      role="status"
      aria-live="polite"
      className={`fixed bottom-6 right-6 z-50 px-5 py-4 rounded-xl shadow-2xl font-medium flex items-center gap-3 border transition-all duration-300 transform translate-y-0 opacity-100 max-w-md backdrop-blur-md ${
        typeStyles[toast.type] || typeStyles.error
      }`}
    >
      <div className="shrink-0">{icons[toast.type] || icons.error}</div>
      <div className="flex-1 text-sm font-semibold leading-snug tracking-wide">{toast.message}</div>
      {onClose && (
        <button
          onClick={onClose}
          className="shrink-0 p-1 hover:bg-black/10 dark:hover:bg-white/10 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-white"
          aria-label="Close notification"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  );
}

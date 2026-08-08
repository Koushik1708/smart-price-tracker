import React from 'react';

export default function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  className = ""
}) {
  return (
    <div className={`flex flex-col items-center justify-center p-8 text-center bg-slate-50/80 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-700/80 rounded-2xl ${className}`}>
      <div className="w-14 h-14 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 rounded-2xl flex items-center justify-center mb-4 shadow-sm border border-indigo-100/50 dark:border-indigo-900/50">
        {icon || (
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
          </svg>
        )}
      </div>
      <h3 className="text-base font-bold text-slate-800 dark:text-slate-100 mb-1 tracking-tight">{title}</h3>
      <p className="text-slate-500 dark:text-slate-400 text-sm max-w-sm mb-6 font-medium leading-relaxed">{description}</p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 text-white font-bold px-5 py-2.5 rounded-xl text-sm transition-all shadow-md shadow-indigo-200 dark:shadow-none hover:-translate-y-0.5 active:translate-y-0 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 dark:focus:ring-offset-slate-900"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}

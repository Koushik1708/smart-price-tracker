import React from 'react';

const formatCurrency = (val) => {
  if (val === undefined || val === null) return '-';
  return '₹' + parseFloat(val).toLocaleString('en-IN', { maximumFractionDigits: 0 });
};

const PriceDrops = ({ drops, loading }) => {
  if (loading) {
    return (
      <div className="bg-white dark:bg-slate-800/90 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700/80 p-5 h-full">
        <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-4">Biggest Price Drops</h3>
        <div className="space-y-3">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="flex gap-4 animate-pulse">
              <div className="w-12 h-12 bg-slate-200 dark:bg-slate-700 rounded-md"></div>
              <div className="flex-1 space-y-2 py-1">
                <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-3/4"></div>
                <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-1/4"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800/90 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700/80 p-5 h-full flex flex-col">
      <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-4">Biggest Price Drops</h3>
      
      {!drops || drops.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center py-10 opacity-75">
          <div className="w-16 h-16 bg-slate-50 dark:bg-slate-700/50 text-slate-300 dark:text-slate-500 rounded-full flex items-center justify-center mb-4">
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"></path>
            </svg>
          </div>
          <p className="text-sm font-semibold text-slate-500 dark:text-slate-400">No price drops detected</p>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">We'll alert you here when prices fall.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
            <thead className="text-xs uppercase bg-slate-50 dark:bg-slate-700/40 text-slate-500 dark:text-slate-400 font-bold border-b border-slate-100 dark:border-slate-700/60">
              <tr>
                <th className="px-3 py-2 rounded-tl-lg">Product</th>
                <th className="px-3 py-2">Before</th>
                <th className="px-3 py-2">Now</th>
                <th className="px-3 py-2 rounded-tr-lg">Savings</th>
              </tr>
            </thead>
            <tbody>
              {drops.map((drop, idx) => (
                <tr key={idx} className="border-b border-slate-50 dark:border-slate-700/40 hover:bg-slate-50/50 dark:hover:bg-slate-700/30 transition-colors">
                  <td className="px-3 py-3">
                    <div className="flex items-center gap-3 max-w-[200px]">
                      {drop.image && (
                        <div className="w-10 h-10 shrink-0 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-700 rounded p-1 flex items-center justify-center">
                          <img src={drop.image} alt={drop.title} className="max-w-full max-h-full object-contain" />
                        </div>
                      )}
                      <span className="font-semibold text-slate-800 dark:text-slate-100 truncate" title={drop.title}>{drop.title}</span>
                    </div>
                  </td>
                  <td className="px-3 py-3 line-through text-slate-400 dark:text-slate-500">{formatCurrency(drop.previous_price)}</td>
                  <td className="px-3 py-3 font-bold text-slate-800 dark:text-slate-100">{formatCurrency(drop.current_price)}</td>
                  <td className="px-3 py-3">
                    <div className="flex flex-col">
                      <span className="text-emerald-600 dark:text-emerald-400 font-bold">-{formatCurrency(drop.savings)}</span>
                      <span className="text-[10px] font-semibold text-emerald-500 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50 px-1.5 py-0.5 rounded-full w-fit">
                        {drop.savings_percent}% OFF
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default React.memo(PriceDrops);

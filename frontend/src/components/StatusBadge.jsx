import React from 'react';

export default function StatusBadge({ status }) {
  const s = (status || 'created').toLowerCase();
  
  const config = {
    created: { bg: 'bg-slate-800', text: 'text-slate-300', border: 'border-slate-700', label: 'Draft' },
    analyzing: { bg: 'bg-amber-950/60', text: 'text-amber-400', border: 'border-amber-800/60', label: 'Analyzing...' },
    running: { bg: 'bg-amber-950/60', text: 'text-amber-400', border: 'border-amber-800/60', label: 'Processing' },
    analyzed: { bg: 'bg-emerald-950/60', text: 'text-emerald-400', border: 'border-emerald-800/60', label: 'Analyzed' },
    completed: { bg: 'bg-emerald-950/60', text: 'text-emerald-400', border: 'border-emerald-800/60', label: 'Completed' },
    error: { bg: 'bg-rose-950/60', text: 'text-rose-400', border: 'border-rose-800/60', label: 'Error' },
  };

  const current = config[s] || config.created;

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${current.bg} ${current.text} ${current.border}`}>
      <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-current opacity-75"></span>
      {current.label}
    </span>
  );
}

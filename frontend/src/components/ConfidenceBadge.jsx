import React from 'react';

export default function ConfidenceBadge({ band }) {
  const b = (band || 'medium').toLowerCase();

  const styles = {
    high: {
      bg: 'bg-emerald-950/50',
      text: 'text-emerald-400',
      border: 'border-emerald-800/40',
      dot: 'bg-emerald-400',
      label: 'High Reliability',
    },
    medium: {
      bg: 'bg-amber-950/50',
      text: 'text-amber-400',
      border: 'border-amber-800/40',
      dot: 'bg-amber-400',
      label: 'Medium Reliability',
    },
    low: {
      bg: 'bg-orange-950/50',
      text: 'text-orange-400',
      border: 'border-orange-800/40',
      dot: 'bg-orange-400',
      label: 'Heuristic Indicator',
    },
  };

  const current = styles[b] || styles.medium;

  return (
    <span
      title="Confidence band measures empirical reliability of this specific forensic observation, NOT a probability of deception."
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono font-medium border ${current.bg} ${current.text} ${current.border}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${current.dot}`}></span>
      {current.label}
    </span>
  );
}

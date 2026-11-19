import React from 'react';
import { NavLink } from 'react-router-dom';
import { Shield, PlusCircle, LayoutDashboard, FileSearch, Sparkles, Settings as SettingsIcon } from 'lucide-react';

export default function Sidebar() {
  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/investigations/new', label: 'New Investigation', icon: PlusCircle },
    { to: '/settings', label: 'AI & Settings', icon: SettingsIcon },
  ];

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col shrink-0 min-h-screen">
      {/* Brand */}
      <div className="p-5 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-tight text-white flex items-center gap-1.5">
              TruthLens
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/50">MVP</span>
            </h1>
            <p className="text-xs text-slate-400 font-mono">Forensic Intelligence</p>
          </div>
        </div>
        <p className="text-[11px] text-slate-500 mt-3 italic leading-relaxed">
          "Detect. Analyze. Correlate. Explain."
        </p>
      </div>

      {/* Navigation */}
      <nav className="p-4 space-y-1.5 flex-1">
        <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider px-3 mb-2">
          Investigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-600/15 text-cyan-400 border border-blue-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              {item.label}
            </NavLink>
          );
        })}
      </nav>

      {/* Core Principle Footer */}
      <div className="p-4 m-3 rounded-lg bg-slate-950/70 border border-slate-800 text-[11px] text-slate-400 leading-normal">
        <div className="flex items-center gap-1.5 font-semibold text-slate-300 mb-1">
          <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
          Forensic Principle
        </div>
        A detection score is an indicator, not a verdict. Observations & correlations require human review.
      </div>
    </aside>
  );
}

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getInvestigations } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import { Shield, Plus, FolderKanban, FileCheck, Layers, ArrowRight, Activity } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

export default function Dashboard() {
  const [investigations, setInvestigations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await getInvestigations();
      setInvestigations(res.data || []);
    } catch (err) {
      console.error('Failed to load investigations:', err);
    } finally {
      setLoading(false);
    }
  };

  // Compute metrics
  const totalInvestigations = investigations.length;
  const totalEvidence = investigations.reduce((acc, inv) => acc + (inv.evidence_count || 0), 0);
  const totalCompleted = investigations.filter((inv) => inv.status === 'analyzed' || inv.status === 'completed').length;

  // Chart data: investigations status distribution
  const chartData = [
    { name: 'Draft / Created', count: investigations.filter((i) => i.status === 'created').length, color: '#64748b' },
    { name: 'In Analysis', count: investigations.filter((i) => i.status === 'analyzing' || i.status === 'running').length, color: '#f59e0b' },
    { name: 'Analyzed', count: totalCompleted, color: '#10b981' },
  ];

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Forensic Intelligence Dashboard
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Multimodal deepfake detection, cross-evidence correlation & explainable analysis
          </p>
        </div>
        <Link
          to="/investigations/new"
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-medium text-sm transition-all shadow-lg shadow-cyan-900/30"
        >
          <Plus className="w-4 h-4" />
          New Investigation
        </Link>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Total Investigations</span>
            <div className="p-2 rounded-lg bg-blue-950/60 text-blue-400 border border-blue-800/40">
              <FolderKanban className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold font-mono text-white mt-3">
            {totalInvestigations}
          </div>
          <span className="text-xs text-slate-500 mt-1 block">Active forensic case files</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Evidence Items</span>
            <div className="p-2 rounded-lg bg-cyan-950/60 text-cyan-400 border border-cyan-800/40">
              <Layers className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold font-mono text-white mt-3">
            {totalEvidence}
          </div>
          <span className="text-xs text-slate-500 mt-1 block">Images, videos, audio & transcripts</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Completed Analyses</span>
            <div className="p-2 rounded-lg bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
              <FileCheck className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold font-mono text-white mt-3">
            {totalCompleted}
          </div>
          <span className="text-xs text-slate-500 mt-1 block">Multi-engine correlated reports</span>
        </div>
      </div>

      {/* Overview Analytics Chart */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-semibold text-slate-200">Investigation Pipeline Status</h3>
          </div>
          <span className="text-xs font-mono text-slate-400">Total Cases: {totalInvestigations}</span>
        </div>
        <div className="h-44 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
              <XAxis type="number" stroke="#64748b" fontSize={11} allowDecimals={false} />
              <YAxis dataKey="name" type="category" stroke="#94a3b8" fontSize={11} width={100} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                cursor={{ fill: '#1e293b' }}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Investigations Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <h3 className="font-semibold text-slate-200 text-sm">Recent Investigations</h3>
          <span className="text-xs font-mono text-slate-500">{investigations.length} recorded</span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-500 font-mono text-xs">
            Loading investigation records...
          </div>
        ) : investigations.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <Shield className="w-12 h-12 text-slate-600 mx-auto" />
            <p className="text-sm text-slate-400">No forensic investigations created yet</p>
            <Link
              to="/investigations/new"
              className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 font-medium"
            >
              Initialize your first investigation <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 uppercase font-mono border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Title & Context</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Evidence Items</th>
                  <th className="py-3 px-4">Created Date</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {investigations.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3.5 px-4">
                      <Link to={`/investigations/${inv.id}`} className="font-semibold text-slate-200 hover:text-cyan-400">
                        {inv.title}
                      </Link>
                      {inv.description && (
                        <p className="text-slate-400 truncate max-w-md mt-0.5">{inv.description}</p>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={inv.status} />
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {inv.evidence_count} file{inv.evidence_count === 1 ? '' : 's'}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-400">
                      {inv.created_at ? new Date(inv.created_at).toLocaleDateString() : 'N/A'}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <Link
                        to={`/investigations/${inv.id}`}
                        className="inline-flex items-center gap-1 text-cyan-400 hover:text-cyan-300 font-medium"
                      >
                        Open Workspace <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

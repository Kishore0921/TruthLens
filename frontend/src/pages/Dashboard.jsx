import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getInvestigations, getDashboardStats } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import {
  Shield, Plus, FolderKanban, FileCheck, Layers, ArrowRight, Activity,
  Search, AlertTriangle, GitCompare, Sparkles, Filter, CheckCircle2, Clock
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

export default function Dashboard() {
  const [investigations, setInvestigations] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [invRes, statsRes] = await Promise.all([
        getInvestigations(),
        getDashboardStats().catch(() => null)
      ]);
      setInvestigations(invRes.data || []);
      if (statsRes && statsRes.data) {
        setStats(statsRes.data);
      }
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Metrics (fallback to client calc if stats endpoint fails)
  const totalInv = stats ? stats.total_investigations : investigations.length;
  const totalEv = stats ? stats.total_evidence : investigations.reduce((acc, i) => acc + (i.evidence_count || 0), 0);
  const totalFindings = stats ? stats.total_findings : investigations.reduce((acc, i) => acc + (i.findings_count || 0), 0);
  const totalCorrelations = stats ? stats.total_correlations : investigations.reduce((acc, i) => acc + (i.correlations_count || 0), 0);
  const completedRuns = stats ? stats.completed_analyses : investigations.filter(i => i.status === 'analyzed').length;

  const pipeline = stats ? stats.pipeline_status : {
    draft: investigations.filter(i => i.status === 'created' || i.status === 'draft').length,
    in_analysis: investigations.filter(i => i.status === 'analyzing' || i.status === 'running').length,
    analyzed: completedRuns,
    failed: 0
  };

  const chartData = [
    { name: 'Draft / Ready', count: pipeline.draft || 0, color: '#64748b' },
    { name: 'In Analysis', count: pipeline.in_analysis || 0, color: '#f59e0b' },
    { name: 'Analyzed', count: pipeline.analyzed || 0, color: '#10b981' },
    { name: 'Failed', count: pipeline.failed || 0, color: '#ef4444' }
  ];

  const filteredInvestigations = investigations.filter((inv) => {
    const matchesSearch =
      inv.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (inv.description && inv.description.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesStatus =
      statusFilter === 'all' ||
      (statusFilter === 'draft' && (inv.status === 'created' || inv.status === 'draft')) ||
      (statusFilter === 'analyzing' && (inv.status === 'analyzing' || inv.status === 'running')) ||
      (statusFilter === 'analyzed' && (inv.status === 'analyzed' || inv.status === 'completed'));
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-cyan-400" />
            <h2 className="text-2xl font-bold tracking-tight text-white">
              Forensic Intelligence Dashboard
            </h2>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Multimodal deepfake detection, signal forensics, cross-evidence correlation & explainable analysis
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/investigations/new"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-medium text-sm transition-all shadow-lg shadow-cyan-900/30"
          >
            <Plus className="w-4 h-4" />
            New Investigation
          </Link>
        </div>
      </div>

      {/* Primary Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Investigations</span>
            <div className="p-2 rounded-lg bg-blue-950/60 text-blue-400 border border-blue-800/40">
              <FolderKanban className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-bold font-mono text-white mt-2">{totalInv}</div>
          <span className="text-xs text-slate-500 mt-1 block">Active forensic cases</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Evidence Assets</span>
            <div className="p-2 rounded-lg bg-cyan-950/60 text-cyan-400 border border-cyan-800/40">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-bold font-mono text-white mt-2">{totalEv}</div>
          <span className="text-xs text-slate-500 mt-1 block">Images, videos, audio & text</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Forensic Findings</span>
            <div className="p-2 rounded-lg bg-indigo-950/60 text-indigo-400 border border-indigo-800/40">
              <Sparkles className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-bold font-mono text-white mt-2">{totalFindings}</div>
          <span className="text-xs text-slate-500 mt-1 block">Signal & heuristic observations</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Cross-Modal Links</span>
            <div className="p-2 rounded-lg bg-purple-950/60 text-purple-400 border border-purple-800/40">
              <GitCompare className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-bold font-mono text-white mt-2">{totalCorrelations}</div>
          <span className="text-xs text-slate-500 mt-1 block">Corroborations & contradictions</span>
        </div>
      </div>

      {/* Investigation Pipeline Overview Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-semibold text-slate-200">Investigation Pipeline Status</h3>
            </div>
            <span className="text-xs font-mono text-slate-400">{completedRuns} completed</span>
          </div>
          <div className="h-44 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 30, left: 30, bottom: 5 }}>
                <XAxis type="number" stroke="#64748b" fontSize={11} allowDecimals={false} />
                <YAxis dataKey="name" type="category" stroke="#94a3b8" fontSize={11} width={90} />
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

        {/* Quick Pipeline Status Summary */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col justify-between shadow-sm">
          <div>
            <h3 className="text-sm font-semibold text-slate-200 mb-4">Pipeline Breakdown</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs py-1.5 border-b border-slate-800/80">
                <span className="text-slate-400 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-slate-400"></span> Draft / Uploading
                </span>
                <span className="font-mono font-semibold text-slate-200">{pipeline.draft || 0}</span>
              </div>
              <div className="flex items-center justify-between text-xs py-1.5 border-b border-slate-800/80">
                <span className="text-amber-400 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span> In Analysis
                </span>
                <span className="font-mono font-semibold text-amber-300">{pipeline.in_analysis || 0}</span>
              </div>
              <div className="flex items-center justify-between text-xs py-1.5 border-b border-slate-800/80">
                <span className="text-emerald-400 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400"></span> Fully Analyzed
                </span>
                <span className="font-mono font-semibold text-emerald-300">{pipeline.analyzed || 0}</span>
              </div>
              <div className="flex items-center justify-between text-xs py-1.5">
                <span className="text-red-400 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-red-400"></span> Failed Runs
                </span>
                <span className="font-mono font-semibold text-red-300">{pipeline.failed || 0}</span>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800">
            <Link
              to="/settings"
              className="text-xs text-slate-400 hover:text-cyan-400 flex items-center justify-between transition-colors"
            >
              <span>AI Provider Configuration</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>

      {/* Investigations Table with Search & Filter */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-800 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <h3 className="font-semibold text-slate-200 text-sm">Recent Investigations</h3>
            <span className="text-xs font-mono text-slate-500 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
              {filteredInvestigations.length} cases
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search cases..."
                className="pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-cyan-500 w-44"
              />
            </div>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-300 px-3 py-1.5 focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="analyzing">In Analysis</option>
              <option value="analyzed">Analyzed</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-500 font-mono text-xs">
            Loading investigation records...
          </div>
        ) : filteredInvestigations.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <Shield className="w-12 h-12 text-slate-600 mx-auto" />
            <p className="text-sm text-slate-400">
              {searchQuery ? 'No investigations match your query' : 'No forensic investigations created yet'}
            </p>
            <Link
              to="/investigations/new"
              className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 font-medium"
            >
              Initialize new case <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 uppercase font-mono border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Title & Description</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Evidence</th>
                  <th className="py-3 px-4">Findings</th>
                  <th className="py-3 px-4">Correlations</th>
                  <th className="py-3 px-4">Created Date</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {filteredInvestigations.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3.5 px-4">
                      <Link to={`/investigations/${inv.id}`} className="font-semibold text-slate-200 hover:text-cyan-400">
                        {inv.title}
                      </Link>
                      {inv.description && (
                        <p className="text-slate-400 truncate max-w-sm mt-0.5">{inv.description}</p>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={inv.status} />
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {inv.evidence_count} item{inv.evidence_count === 1 ? '' : 's'}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {inv.findings_count !== undefined ? inv.findings_count : '—'}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {inv.correlations_count !== undefined ? inv.correlations_count : '—'}
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

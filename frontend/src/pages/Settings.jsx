import React, { useEffect, useState } from 'react';
import {
  getAIProviders, updateAIProvider, testAIProvider,
  getSystemHealth, getForensicDatasets
} from '../services/api';
import {
  ShieldCheck, Cpu, CheckCircle2, XCircle, AlertCircle, RefreshCw,
  Sparkles, Server, Database, Layers, Lock, FileCode, Check
} from 'lucide-react';

export default function Settings() {
  const [providers, setProviders] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [testingId, setTestingId] = useState(null);
  const [testResults, setTestResults] = useState({});
  const [feedback, setFeedback] = useState({ type: '', text: '' });

  useEffect(() => {
    loadAllDiagnostics();
  }, []);

  const loadAllDiagnostics = async () => {
    try {
      setLoading(true);
      const [provRes, healthRes, datasetsRes] = await Promise.allSettled([
        getAIProviders(),
        getSystemHealth(),
        getForensicDatasets()
      ]);

      if (provRes.status === 'fulfilled') {
        setProviders(provRes.value.data || []);
      }
      if (healthRes.status === 'fulfilled') {
        setSystemHealth(healthRes.value.data || null);
      }
      if (datasetsRes.status === 'fulfilled') {
        setDatasets(datasetsRes.value.data || []);
      }
    } catch (err) {
      console.error('Failed to load system diagnostics:', err);
      setFeedback({ type: 'error', text: 'Failed to retrieve diagnostics.' });
    } finally {
      setLoading(false);
    }
  };

  const handleModelChange = async (providerId, selectedModel) => {
    try {
      await updateAIProvider(providerId, { selected_model: selectedModel });
      const provRes = await getAIProviders();
      setProviders(provRes.data || []);
      setFeedback({ type: 'success', text: `Updated model selection for ${providerId}.` });
    } catch (err) {
      setFeedback({ type: 'error', text: `Failed to update model: ${err.message}` });
    }
  };

  const handleToggleEnable = async (providerId, currentEnabled) => {
    try {
      await updateAIProvider(providerId, { is_enabled: !currentEnabled });
      const provRes = await getAIProviders();
      setProviders(provRes.data || []);
    } catch (err) {
      setFeedback({ type: 'error', text: `Failed to toggle provider: ${err.message}` });
    }
  };

  const handleTestConnection = async (providerId) => {
    try {
      setTestingId(providerId);
      const res = await testAIProvider(providerId);
      setTestResults((prev) => ({ ...prev, [providerId]: res.data }));
      const provRes = await getAIProviders();
      setProviders(provRes.data || []);
    } catch (err) {
      setTestResults((prev) => ({
        ...prev,
        [providerId]: {
          success: false,
          status: 'error',
          message: err.response?.data?.detail || err.message,
        },
      }));
    } finally {
      setTestingId(null);
    }
  };

  const executionMode = systemHealth?.execution_mode || 'HYBRID';

  return (
    <div className="p-8 space-y-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <ShieldCheck className="w-6 h-6 text-cyan-400" />
            AI & System Settings
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Environment-configured provider health, local ML model registry, and forensic dataset benchmarks.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <span className="text-xs font-mono text-slate-400">Execution Mode:</span>
          <span className="px-3 py-1 rounded-full text-xs font-mono font-semibold bg-cyan-950/80 text-cyan-300 border border-cyan-800 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
            {executionMode}
          </span>
          <button
            onClick={loadAllDiagnostics}
            disabled={loading}
            className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition-colors"
            title="Refresh Diagnostics"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {feedback.text && (
        <div
          className={`p-4 rounded-lg flex items-center justify-between text-xs font-medium ${
            feedback.type === 'success'
              ? 'bg-emerald-950/60 border border-emerald-800 text-emerald-300'
              : 'bg-red-950/60 border border-red-800 text-red-300'
          }`}
        >
          <span>{feedback.text}</span>
          <button onClick={() => setFeedback({ type: '', text: '' })} className="hover:opacity-75">
            Dismiss
          </button>
        </div>
      )}

      {/* Mandatory Administrator Configuration Notice */}
      <div className="bg-slate-900/90 border border-cyan-900/40 rounded-xl p-5 shadow-sm">
        <div className="flex items-start gap-3.5">
          <div className="p-2 rounded-lg bg-cyan-950/80 border border-cyan-800/60 text-cyan-400 mt-0.5">
            <Lock className="w-5 h-5" />
          </div>
          <div className="text-xs space-y-1.5 text-slate-300">
            <h4 className="font-semibold text-slate-100 text-sm flex items-center gap-2">
              Server-Managed Credentials Architecture
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-cyan-400 border border-slate-700">
                backend/.env
              </span>
            </h4>
            <p className="text-slate-300 leading-relaxed font-medium">
              "AI providers are configured securely by the application administrator through the backend environment file. API credentials are never entered or exposed through the frontend."
            </p>
            <p className="text-slate-400 leading-relaxed mt-1">
              TruthLens performs full reference-independent digital forensics offline even when all cloud providers are unconfigured.
              Local signal forensics (2D-FFT frequency domain analysis, sensor noise variance, ELA, pHash, and acoustic spectral inspection) remain 100% operational.
            </p>
          </div>
        </div>
      </div>

      {/* Provider Status Summary Table */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold uppercase tracking-wider font-mono text-slate-400 flex items-center gap-2">
          <Server className="w-4 h-4 text-cyan-400" />
          AI Provider Configuration Status
        </h3>

        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/80 text-[11px] font-mono uppercase tracking-wider text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Provider</th>
                  <th className="py-3 px-4">Configuration Source</th>
                  <th className="py-3 px-4">Execution Target</th>
                  <th className="py-3 px-4">Active Model</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 font-sans">
                {providers.map((p) => {
                  const result = testResults[p.id];
                  const isTesting = testingId === p.id;

                  return (
                    <tr key={p.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-white">{p.provider_name}</div>
                        <div className="text-[10px] text-slate-500 font-mono">ID: {p.id}</div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-mono text-[11px] text-cyan-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                          Backend .env
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-xs font-mono">
                        {p.execution_type || (p.id === 'huggingface' ? 'Local CPU / Hub' : 'Cloud Reasoning')}
                      </td>
                      <td className="py-3 px-4">
                        <select
                          value={p.selected_model}
                          onChange={(e) => handleModelChange(p.id, e.target.value)}
                          disabled={!p.has_key}
                          className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500 disabled:opacity-40"
                        >
                          {p.available_models.map((m) => (
                            <option key={m} value={m}>
                              {m}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-mono border ${
                            p.has_key
                              ? 'bg-emerald-950/60 border-emerald-800 text-emerald-400'
                              : 'bg-slate-950 border-slate-800 text-slate-500'
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              p.has_key ? 'bg-emerald-400' : 'bg-slate-600'
                            }`}
                          ></span>
                          {p.has_key ? 'Configured' : 'Missing'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleToggleEnable(p.id, p.is_enabled)}
                            disabled={!p.has_key}
                            className={`text-xs px-2.5 py-1 rounded font-medium transition-colors border ${
                              p.is_enabled
                                ? 'bg-cyan-600/20 text-cyan-400 border-cyan-800 hover:bg-cyan-600/30'
                                : 'bg-slate-800 text-slate-400 hover:bg-slate-700 border-slate-700'
                            } ${!p.has_key ? 'cursor-not-allowed opacity-40' : ''}`}
                          >
                            {p.is_enabled ? 'Enabled' : 'Disabled'}
                          </button>

                          <button
                            onClick={() => handleTestConnection(p.id)}
                            disabled={isTesting || !p.has_key}
                            className="py-1 px-2.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 font-medium text-xs transition-colors inline-flex items-center gap-1.5 border border-slate-700"
                          >
                            {isTesting ? (
                              <RefreshCw className="w-3 h-3 animate-spin text-cyan-400" />
                            ) : (
                              <Server className="w-3 h-3 text-slate-400" />
                            )}
                            Test
                          </button>
                        </div>
                        {result && (
                          <div className={`mt-1.5 text-[10px] text-right ${result.success ? 'text-emerald-400' : 'text-red-400'}`}>
                            {result.message}
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Pretrained Forensic Model Registry */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold uppercase tracking-wider font-mono text-slate-400 flex items-center gap-2">
          <Layers className="w-4 h-4 text-cyan-400" />
          Pretrained Digital Forensic & Deepfake Model Registry
        </h3>

        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/80 text-[11px] font-mono uppercase tracking-wider text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Model ID</th>
                  <th className="py-3 px-4">Modality</th>
                  <th className="py-3 px-4">Architecture</th>
                  <th className="py-3 px-4">Execution Target</th>
                  <th className="py-3 px-4">Hardware Profile</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 font-sans">
                {(systemHealth?.models || []).map((m) => (
                  <tr key={m.model_id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-semibold text-white font-mono">{m.model_id}</div>
                      <div className="text-[10px] text-slate-400">{m.detection_task}</div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-slate-800 text-slate-300 border border-slate-700 uppercase">
                        {m.modality}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-300">{m.architecture}</td>
                    <td className="py-3 px-4">
                      <span className="text-emerald-400 font-mono text-[11px]">
                        {m.execution_method}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400 text-[11px] font-mono">
                      {m.hardware_requirements}
                    </td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-950/60 text-emerald-400 border border-emerald-800">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                        Active
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Hugging Face Curated Evaluation Benchmarks */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wider font-mono text-slate-400 flex items-center gap-2">
            <Database className="w-4 h-4 text-cyan-400" />
            Curated Digital Forensics Evaluation Benchmarks (Hugging Face)
          </h3>
          <span className="text-xs font-mono text-slate-500">
            Catalog Inspector (Safe Metadata View)
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {datasets.map((d) => (
            <div
              key={d.id}
              className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2.5 hover:border-slate-700 transition-colors"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-semibold text-cyan-400">{d.repo_id}</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-400 uppercase">
                  {d.modality}
                </span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">{d.description}</p>
              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400">
                <span>Task: {d.task}</span>
                <span className="text-slate-500">Size: {d.estimated_size}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Hardware Safeguards Profile */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
        <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 flex items-center gap-2">
          <Cpu className="w-4 h-4 text-cyan-400" /> Host Hardware Execution Safeguards
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
            <span className="text-slate-500 block">CPU Profile</span>
            <span className="font-mono text-slate-200 font-semibold mt-0.5 block">
              {systemHealth?.hardware?.cpu_cores || 2} Physical/Virtual Cores
            </span>
          </div>
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
            <span className="text-slate-500 block">Image Inference Cap</span>
            <span className="font-mono text-slate-200 font-semibold mt-0.5 block">
              Max {systemHealth?.hardware?.max_image_dim || 512}px (Tensor Safe)
            </span>
          </div>
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
            <span className="text-slate-500 block">Video Sampling</span>
            <span className="font-mono text-slate-200 font-semibold mt-0.5 block">
              Max {systemHealth?.hardware?.max_video_frames || 10} Sampled Frames
            </span>
          </div>
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
            <span className="text-slate-500 block">Audio Duration Cap</span>
            <span className="font-mono text-slate-200 font-semibold mt-0.5 block">
              {systemHealth?.hardware?.max_audio_duration_s || 15}s Sparse Processing
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

import React, { useEffect, useState } from 'react';
import {
  getAIProviders, updateAIProvider, testAIProvider, deleteAIProviderKey
} from '../services/api';
import {
  Key, ShieldCheck, Cpu, CheckCircle2, XCircle, AlertCircle, RefreshCw,
  ExternalLink, Trash2, Eye, EyeOff, Save, Sparkles, Server
} from 'lucide-react';

export default function Settings() {
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);
  const [testingId, setTestingId] = useState(null);
  const [testResults, setTestResults] = useState({});
  const [keyInputs, setKeyInputs] = useState({});
  const [showKeys, setShowKeys] = useState({});
  const [feedback, setFeedback] = useState({ type: '', text: '' });

  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    try {
      setLoading(true);
      const res = await getAIProviders();
      setProviders(res.data || []);
    } catch (err) {
      console.error('Failed to load AI providers:', err);
      setFeedback({ type: 'error', text: 'Failed to retrieve AI provider configs.' });
    } finally {
      setLoading(false);
    }
  };

  const handleKeyChange = (providerId, value) => {
    setKeyInputs((prev) => ({ ...prev, [providerId]: value }));
  };

  const handleModelChange = async (providerId, selectedModel) => {
    try {
      setSavingId(providerId);
      await updateAIProvider(providerId, { selected_model: selectedModel });
      await loadProviders();
      setFeedback({ type: 'success', text: `Updated default model for ${providerId}.` });
    } catch (err) {
      setFeedback({ type: 'error', text: `Failed to update model: ${err.message}` });
    } finally {
      setSavingId(null);
    }
  };

  const handleToggleEnable = async (providerId, currentEnabled) => {
    try {
      setSavingId(providerId);
      await updateAIProvider(providerId, { is_enabled: !currentEnabled });
      await loadProviders();
    } catch (err) {
      setFeedback({ type: 'error', text: `Failed to toggle provider: ${err.message}` });
    } finally {
      setSavingId(null);
    }
  };

  const handleSaveKey = async (providerId) => {
    const key = keyInputs[providerId];
    if (!key) return;

    try {
      setSavingId(providerId);
      await updateAIProvider(providerId, { api_key: key });
      setKeyInputs((prev) => ({ ...prev, [providerId]: '' }));
      await loadProviders();
      setFeedback({ type: 'success', text: `API key saved securely and encrypted with Fernet for ${providerId}.` });
    } catch (err) {
      setFeedback({ type: 'error', text: `Failed to save key: ${err.message}` });
    } finally {
      setSavingId(null);
    }
  };

  const handleDeleteKey = async (providerId) => {
    if (!confirm(`Are you sure you want to remove the API key for ${providerId}?`)) return;

    try {
      setSavingId(providerId);
      await deleteAIProviderKey(providerId);
      await loadProviders();
      setTestResults((prev) => ({ ...prev, [providerId]: null }));
      setFeedback({ type: 'success', text: `API key deleted for ${providerId}.` });
    } catch (err) {
      setFeedback({ type: 'error', text: `Failed to delete key: ${err.message}` });
    } finally {
      setSavingId(null);
    }
  };

  const handleTestConnection = async (providerId) => {
    try {
      setTestingId(providerId);
      const res = await testAIProvider(providerId);
      setTestResults((prev) => ({ ...prev, [providerId]: res.data }));
      await loadProviders();
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

  return (
    <div className="p-8 space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="pb-6 border-b border-slate-800">
        <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <Key className="w-6 h-6 text-cyan-400" />
          Settings & AI Integrations
        </h2>
        <p className="text-sm text-slate-400 mt-1">
          Configure optional cloud AI models (Gemini & OpenAI) for enhanced reference fact extraction and semantic cross-modal comparison.
        </p>
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

      {/* Security Architecture Notice */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <div className="flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-emerald-400 mt-0.5 shrink-0" />
          <div className="text-xs space-y-1.5 text-slate-300">
            <h4 className="font-semibold text-slate-100 text-sm">Security & Privacy Architecture</h4>
            <p className="text-slate-400 leading-relaxed">
              API keys are encrypted on disk using AES-128 via Fernet encryption and are never sent to the browser or stored in plaintext.
              TruthLens functions 100% offline without external API keys using built-in signal forensics, ELA, and rule-based NLP comparison.
            </p>
          </div>
        </div>
      </div>

      {/* Provider Cards */}
      <div className="space-y-6">
        <h3 className="text-sm font-semibold uppercase tracking-wider font-mono text-slate-400">
          Available AI Providers
        </h3>

        {loading ? (
          <div className="p-8 text-center text-xs font-mono text-slate-500">
            Loading provider configs...
          </div>
        ) : (
          providers.map((p) => {
            const result = testResults[p.id];
            const isSaving = savingId === p.id;
            const isTesting = testingId === p.id;

            return (
              <div
                key={p.id}
                className={`bg-slate-900 border rounded-xl p-6 transition-all shadow-sm ${
                  p.is_enabled ? 'border-slate-700' : 'border-slate-800/80 opacity-80'
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-lg bg-blue-950/60 text-blue-400 border border-blue-800/40">
                      <Sparkles className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-white text-base">{p.provider_name}</h4>
                      <p className="text-xs text-slate-400 font-mono">ID: {p.id}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span
                      className={`text-xs px-2.5 py-1 rounded-full font-mono border ${
                        p.connection_status === 'connected'
                          ? 'bg-emerald-950/60 border-emerald-800 text-emerald-400'
                          : p.connection_status === 'error'
                          ? 'bg-red-950/60 border-red-800 text-red-400'
                          : 'bg-slate-950 border-slate-800 text-slate-400'
                      }`}
                    >
                      {p.connection_status === 'connected'
                        ? '● Connected'
                        : p.connection_status === 'error'
                        ? '▲ Error'
                        : '○ Not Configured'}
                    </span>

                    <button
                      onClick={() => handleToggleEnable(p.id, p.is_enabled)}
                      disabled={isSaving || !p.has_key}
                      className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
                        p.is_enabled
                          ? 'bg-cyan-600/20 text-cyan-400 border border-cyan-800 hover:bg-cyan-600/30'
                          : 'bg-slate-800 text-slate-400 hover:bg-slate-700 border border-slate-700'
                      } ${!p.has_key ? 'cursor-not-allowed opacity-50' : ''}`}
                    >
                      {p.is_enabled ? 'Enabled' : 'Disabled'}
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-5">
                  {/* API Key Section */}
                  <div className="space-y-3">
                    <label className="text-xs font-semibold text-slate-300 block">
                      API Key
                    </label>

                    {p.has_key ? (
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 font-mono text-xs text-slate-300 flex items-center justify-between">
                          <span>{p.masked_key}</span>
                          <span className="text-emerald-400 text-[10px] font-sans font-medium bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-900">
                            Stored
                          </span>
                        </div>
                        <button
                          onClick={() => handleDeleteKey(p.id)}
                          disabled={isSaving}
                          title="Remove Key"
                          className="p-2 rounded-lg bg-red-950/40 border border-red-900/60 text-red-400 hover:bg-red-900/40 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <div className="relative">
                          <input
                            type={showKeys[p.id] ? 'text' : 'password'}
                            value={keyInputs[p.id] || ''}
                            onChange={(e) => handleKeyChange(p.id, e.target.value)}
                            placeholder={`Enter ${p.provider_name} API Key...`}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-3 pr-10 py-2 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                          />
                          <button
                            type="button"
                            onClick={() =>
                              setShowKeys((prev) => ({ ...prev, [p.id]: !prev[p.id] }))
                            }
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                          >
                            {showKeys[p.id] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                          </button>
                        </div>
                        <button
                          onClick={() => handleSaveKey(p.id)}
                          disabled={isSaving || !keyInputs[p.id]}
                          className="w-full py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition-colors flex items-center justify-center gap-1.5"
                        >
                          <Save className="w-3.5 h-3.5" />
                          Save API Key
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Model Selection & Actions */}
                  <div className="space-y-3">
                    <label className="text-xs font-semibold text-slate-300 block">
                      Default Model
                    </label>

                    <select
                      value={p.selected_model}
                      onChange={(e) => handleModelChange(p.id, e.target.value)}
                      disabled={isSaving}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                    >
                      {p.available_models.map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                    </select>

                    <div className="pt-1 flex items-center gap-3">
                      <button
                        onClick={() => handleTestConnection(p.id)}
                        disabled={isTesting || !p.has_key}
                        className="flex-1 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 font-medium text-xs transition-colors flex items-center justify-center gap-2 border border-slate-700"
                      >
                        {isTesting ? (
                          <>
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                            Testing Connection...
                          </>
                        ) : (
                          <>
                            <Server className="w-3.5 h-3.5" />
                            Test Connection
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Test Feedback Result */}
                {result && (
                  <div
                    className={`mt-4 p-3 rounded-lg text-xs flex items-start gap-2.5 ${
                      result.success
                        ? 'bg-emerald-950/40 border border-emerald-900/60 text-emerald-300'
                        : 'bg-red-950/40 border border-red-900/60 text-red-300'
                    }`}
                  >
                    {result.success ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                    )}
                    <div>
                      <p className="font-semibold">{result.message}</p>
                      {result.model_used && (
                        <p className="font-mono text-[11px] text-slate-400 mt-0.5">
                          Verified Model: {result.model_used}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Hardware Profile Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
        <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 flex items-center gap-2">
          <Cpu className="w-4 h-4 text-cyan-400" /> Host Execution Profile
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
            <span className="text-slate-500 block">CPU Architecture</span>
            <span className="font-mono text-slate-200 font-semibold mt-0.5 block">x86_64 CPU-First</span>
          </div>
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
            <span className="text-slate-500 block">Memory Budget</span>
            <span className="font-mono text-slate-200 font-semibold mt-0.5 block">8 GB RAM Safe</span>
          </div>
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
            <span className="text-slate-500 block">Acceleration</span>
            <span className="font-mono text-slate-200 font-semibold mt-0.5 block">CPU (No CUDA Req.)</span>
          </div>
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
            <span className="text-slate-500 block">Local Models</span>
            <span className="font-mono text-slate-200 font-semibold mt-0.5 block">Signal & ELA Engines</span>
          </div>
        </div>
      </div>
    </div>
  );
}

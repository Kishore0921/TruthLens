import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createInvestigation, extractReferenceFacts } from '../services/api';
import { Shield, ArrowLeft, Info, Sparkles, Wand2, CheckCircle2, Bot } from 'lucide-react';

export default function NewInvestigation() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    reference_context: '',
    ai_enabled: false,
    ai_provider: 'gemini',
  });
  const [structuredFacts, setStructuredFacts] = useState(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleExtractFacts = async () => {
    if (!formData.reference_context.trim()) return;
    try {
      setIsExtracting(true);
      setError('');
      const res = await extractReferenceFacts(formData.reference_context);
      setStructuredFacts(res.data);
    } catch (err) {
      console.warn('Extraction fallback to local regex:', err);
    } finally {
      setIsExtracting(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.title.trim()) {
      setError('Please provide an investigation title.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError('');
      const payload = {
        ...formData,
        structured_facts: structuredFacts || {}
      };
      const res = await createInvestigation(payload);
      navigate(`/investigations/${res.data.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create investigation.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/')}
          className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h2 className="text-xl font-bold text-white">Create New Forensic Investigation</h2>
          <p className="text-xs text-slate-400 mt-0.5">Establish case parameters & reference baseline</p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-950/60 border border-rose-800/80 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-5 shadow-sm">
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase font-mono">
            Investigation Title <span className="text-rose-400">*</span>
          </label>
          <input
            type="text"
            required
            placeholder="e.g. Operation DeepBlue: Speech & Video Verification"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-sm focus:outline-none focus:border-cyan-500 transition-colors"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase font-mono">
            Case Description
          </label>
          <textarea
            rows={2}
            placeholder="Describe the context of the inquiry, media sources, alleged provenance, or subject matter..."
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-sm focus:outline-none focus:border-cyan-500 transition-colors"
          />
        </div>

        {/* Reference Context */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-xs font-semibold text-slate-300 uppercase font-mono">
              Reference Context / Ground Truth Facts (Optional)
            </label>
            <span className="text-[11px] text-cyan-400 font-mono flex items-center gap-1">
              <Sparkles className="w-3 h-3" /> Reference-Independent Enabled
            </span>
          </div>
          <textarea
            rows={3}
            placeholder="e.g. Official dispatch stating: 'The meeting occurred in Bangalore on Monday with the chief minister.' Uploaded evidence will also be independently evaluated without reference."
            value={formData.reference_context}
            onChange={(e) => setFormData({ ...formData, reference_context: e.target.value })}
            className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-sm focus:outline-none focus:border-cyan-500 transition-colors"
          />
          <div className="flex items-center justify-between mt-2">
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Ground truth is <strong>never mandatory</strong>. TruthLens will independently analyze image compression, sensor noise, audio acoustics, and video temporal consistency.
            </p>
            {formData.reference_context.trim().length > 10 && (
              <button
                type="button"
                onClick={handleExtractFacts}
                disabled={isExtracting}
                className="text-xs px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700 flex items-center gap-1 font-mono transition-colors shrink-0 ml-3"
              >
                <Wand2 className="w-3 h-3" />
                {isExtracting ? 'Parsing...' : 'Extract Entities'}
              </button>
            )}
          </div>

          {/* Structured Facts Preview */}
          {structuredFacts && (
            <div className="mt-3 p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs space-y-1">
              <div className="font-semibold text-cyan-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Structured Ground Truth Baseline
              </div>
              <div className="grid grid-cols-2 gap-2 text-slate-300 font-mono text-[11px] pt-1">
                <div>Date: {structuredFacts.event_date || 'None'}</div>
                <div>Location: {structuredFacts.location || 'None'}</div>
                <div>Entities: {(structuredFacts.people || []).join(', ') || 'None'}</div>
                <div>Type: {structuredFacts.event_type || 'Unspecified'}</div>
              </div>
            </div>
          )}
        </div>

        {/* AI Enhancement Toggle */}
        <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot className="w-4 h-4 text-cyan-400" />
            <div>
              <span className="text-xs font-semibold text-slate-200 block">AI-Assisted Cross-Modal Reasoning</span>
              <span className="text-[11px] text-slate-400">Uses configured Gemini or OpenAI provider for semantic correlation</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={formData.ai_provider}
              onChange={(e) => setFormData({ ...formData, ai_provider: e.target.value })}
              className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-300 font-mono"
            >
              <option value="gemini">Gemini</option>
              <option value="openai">OpenAI</option>
            </select>
            <input
              type="checkbox"
              checked={formData.ai_enabled}
              onChange={(e) => setFormData({ ...formData, ai_enabled: e.target.checked })}
              className="w-4 h-4 rounded text-cyan-500 focus:ring-0 bg-slate-950 border-slate-700"
            />
          </div>
        </div>

        <div className="pt-4 border-t border-slate-800 flex justify-end gap-3">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-5 py-2 rounded-lg bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-medium text-sm transition-all shadow-md shadow-cyan-950 disabled:opacity-50"
          >
            {isSubmitting ? 'Initializing...' : 'Create Investigation'}
          </button>
        </div>
      </form>
    </div>
  );
}

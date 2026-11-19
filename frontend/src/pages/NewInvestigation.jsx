import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createInvestigation } from '../services/api';
import { Shield, ArrowLeft, Info, Sparkles } from 'lucide-react';

export default function NewInvestigation() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    reference_context: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.title.trim()) {
      setError('Please provide an investigation title.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError('');
      const res = await createInvestigation(formData);
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
            rows={3}
            placeholder="Describe the context of the inquiry, media sources, alleged provenance, or subject matter..."
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-sm focus:outline-none focus:border-cyan-500 transition-colors"
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-xs font-semibold text-slate-300 uppercase font-mono">
              Reference Context / Ground Truth Facts (Optional)
            </label>
            <span className="text-[11px] text-cyan-400 font-mono flex items-center gap-1">
              <Sparkles className="w-3 h-3" /> Cross-Modal Reference
            </span>
          </div>
          <textarea
            rows={4}
            placeholder="e.g. Official dispatch stating: 'The meeting occurred in Bangalore on Monday with the chief minister.' This text will be cross-referenced against uploaded audio transcripts, video text, and images to flag discrepancies."
            value={formData.reference_context}
            onChange={(e) => setFormData({ ...formData, reference_context: e.target.value })}
            className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-sm focus:outline-none focus:border-cyan-500 transition-colors"
          />
          <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">
            The cross-modal correlation engine uses this reference baseline to detect contradictions, location mismatches, and date conflicts against uploaded evidence.
          </p>
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

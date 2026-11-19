import React, { useState } from 'react';
import { AlertCircle, ChevronDown, ChevronUp, Clock, Eye, Layers } from 'lucide-react';
import ConfidenceBadge from './ConfidenceBadge';
import { getArtifactUrl, getEvidenceFileUrl } from '../services/api';

export default function FindingCard({ finding, evidenceMap = {} }) {
  const [showLimitations, setShowLimitations] = useState(false);
  const [showArtifactModal, setShowArtifactModal] = useState(false);

  const ev = evidenceMap[finding.evidence_id];
  const isEla = finding.engine === 'ela_engine' || finding.indicator?.includes('ela');
  const isMask = finding.engine === 'manipulation_localization_engine' || finding.location?.region?.has_mask;
  const isAudioAcoustic = finding.engine?.includes('audio') && finding.indicator?.includes('profile');

  const isModel = [
    'frequency_spectral_analyzer',
    'local_noise_analyzer',
    'temporal_consistency_detector',
    'synthetic_speech_acoustic_analyzer',
    'manipulation_localization_engine',
    'ela_engine'
  ].includes(finding.engine);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700/80 transition-all shadow-md">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3 mb-2">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className={`font-mono text-xs uppercase px-2 py-0.5 rounded border font-medium ${
              isModel
                ? 'bg-purple-950/60 text-purple-300 border-purple-800/40'
                : 'bg-blue-950/60 text-blue-400 border-blue-800/40'
            }`}>
              {finding.engine}
            </span>
            <span className="text-xs text-slate-400 font-mono">
              {finding.indicator}
            </span>
            {isModel && (
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-cyan-400 border border-slate-700">
                Model Indicator
              </span>
            )}
          </div>
          {ev && (
            <p className="text-xs text-slate-400 font-medium">
              Source Evidence: <span className="text-slate-200">{ev.original_filename}</span> ({ev.media_type})
            </p>
          )}
        </div>

        <div className="flex items-center gap-2">
          {finding.model_score !== null && finding.model_score !== undefined && (
            <span
              className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-cyan-300"
              title="Normalized heuristic indicator score (0.0 to 1.0). Not a definitive verdict."
            >
              Metric: {(finding.model_score * 100).toFixed(0)}%
            </span>
          )}
          <ConfidenceBadge band={finding.confidence_band} />
        </div>
      </div>

      {/* Description */}
      <p className="text-sm text-slate-200 leading-relaxed mt-2.5">
        {finding.description}
      </p>

      {/* Location / Timestamps */}
      {finding.location && (finding.location.timestamp !== null || finding.location.frame_number !== null) && (
        <div className="flex items-center gap-4 mt-3 text-xs font-mono text-slate-400 bg-slate-950/60 px-3 py-1.5 rounded border border-slate-800">
          {finding.location.timestamp !== null && (
            <span className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              Timestamp: {finding.location.timestamp.toFixed(2)}s
            </span>
          )}
          {finding.location.frame_number !== null && (
            <span className="flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-blue-400" />
              Frame: #{finding.location.frame_number}
            </span>
          )}
        </div>
      )}

      {/* Embedded Artifact Inspection (e.g. ELA preview or audio graphs) */}
      {isEla && ev && (
        <div className="mt-4 p-3 bg-slate-950 rounded-lg border border-slate-800">
          <div className="text-xs font-semibold text-slate-300 mb-2 flex items-center justify-between">
            <span>Visual Forensic Artifact: Error Level Analysis Comparison</span>
            <span className="text-[11px] text-slate-500 font-normal">Re-save Q92 delta</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <span className="text-[11px] text-slate-400 block mb-1 font-mono">Original File</span>
              <div className="h-32 bg-slate-900 rounded border border-slate-800 overflow-hidden flex items-center justify-center">
                <img
                  src={getEvidenceFileUrl(finding.evidence_id)}
                  alt="Original"
                  className="w-full h-full object-contain"
                  loading="lazy"
                />
              </div>
            </div>
            <div>
              <span className="text-[11px] text-slate-400 block mb-1 font-mono">ELA Difference Map</span>
              <div className="h-32 bg-slate-900 rounded border border-slate-800 overflow-hidden flex items-center justify-center">
                <img
                  src={getArtifactUrl(finding.evidence_id, 'ela_visualization.png')}
                  alt="ELA Map"
                  className="w-full h-full object-contain"
                  onError={(e) => {
                    e.target.style.display = 'none';
                  }}
                  loading="lazy"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Embedded Manipulation Mask Visualizer */}
      {isMask && ev && (
        <div className="mt-4 p-3 bg-slate-950 rounded-lg border border-slate-800">
          <div className="text-xs font-semibold text-slate-300 mb-2 flex items-center justify-between">
            <span>Pixel-Level Manipulation Localization Mask</span>
            <span className="text-[11px] text-slate-500 font-normal">Spatial residual cluster isolation</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <span className="text-[11px] text-slate-400 block mb-1 font-mono">Source Asset</span>
              <div className="h-32 bg-slate-900 rounded border border-slate-800 overflow-hidden flex items-center justify-center">
                <img
                  src={getEvidenceFileUrl(finding.evidence_id)}
                  alt="Original"
                  className="w-full h-full object-contain"
                  loading="lazy"
                />
              </div>
            </div>
            <div>
              <span className="text-[11px] text-slate-400 block mb-1 font-mono">Anomalous Region Mask</span>
              <div className="h-32 bg-slate-900 rounded border border-slate-800 overflow-hidden flex items-center justify-center">
                <img
                  src={getArtifactUrl(finding.evidence_id, 'manipulation_mask.png')}
                  alt="Manipulation Mask"
                  className="w-full h-full object-contain"
                  onError={(e) => {
                    e.target.style.display = 'none';
                  }}
                  loading="lazy"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {isAudioAcoustic && ev && (
        <div className="mt-4 p-3 bg-slate-950 rounded-lg border border-slate-800">
          <div className="text-xs font-semibold text-slate-300 mb-2">
            Acoustic Signal Visualizations
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <span className="text-[11px] text-slate-400 block mb-1 font-mono">Amplitude Waveform</span>
              <div className="h-28 bg-slate-900 rounded border border-slate-800 overflow-hidden flex items-center justify-center">
                <img
                  src={getArtifactUrl(finding.evidence_id, 'waveform.png')}
                  alt="Waveform"
                  className="w-full h-full object-contain"
                  onError={(e) => (e.target.style.display = 'none')}
                  loading="lazy"
                />
              </div>
            </div>
            <div>
              <span className="text-[11px] text-slate-400 block mb-1 font-mono">Mel Spectrogram</span>
              <div className="h-28 bg-slate-900 rounded border border-slate-800 overflow-hidden flex items-center justify-center">
                <img
                  src={getArtifactUrl(finding.evidence_id, 'spectrogram.png')}
                  alt="Spectrogram"
                  className="w-full h-full object-contain"
                  onError={(e) => (e.target.style.display = 'none')}
                  loading="lazy"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Limitations Disclosure (Expandable) */}
      {finding.limitations && finding.limitations.length > 0 && (
        <div className="mt-4 pt-3 border-t border-slate-800/80">
          <button
            onClick={() => setShowLimitations(!showLimitations)}
            className="flex items-center justify-between w-full text-xs text-slate-400 hover:text-slate-300 font-medium transition-colors"
          >
            <span className="flex items-center gap-1.5 text-amber-500/90">
              <AlertCircle className="w-3.5 h-3.5" />
              Forensic Limitations & Caveats ({finding.limitations.length})
            </span>
            {showLimitations ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-500" />}
          </button>

          {showLimitations && (
            <ul className="mt-2.5 space-y-1 text-xs text-slate-400 bg-slate-950/70 p-3 rounded-lg border border-slate-800/80">
              {finding.limitations.map((lim, idx) => (
                <li key={idx} className="flex items-start gap-2 leading-relaxed">
                  <span className="text-amber-500/80 mt-0.5">•</span>
                  <span>{lim}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

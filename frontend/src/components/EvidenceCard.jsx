import React, { useState } from 'react';
import { FileImage, Video, Music, FileText, Copy, Check, ExternalLink, ShieldCheck, Trash2 } from 'lucide-react';
import { getEvidenceFileUrl } from '../services/api';

export default function EvidenceCard({ evidence, onRemove, canDelete = false }) {
  const [copied, setCopied] = useState(false);

  const mediaIcons = {
    image: FileImage,
    video: Video,
    audio: Music,
    text: FileText,
  };

  const Icon = mediaIcons[evidence.media_type] || FileText;
  const fileUrl = getEvidenceFileUrl(evidence.id);

  const copyHash = (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(evidence.sha256);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatSize = (bytes) => {
    if (!bytes) return '0 B';
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${bytes} B`;
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between hover:border-slate-700 transition-all shadow-md">
      <div>
        {/* Preview / Media Header */}
        <div className="relative w-full h-40 bg-slate-950 rounded-lg overflow-hidden border border-slate-800/80 mb-3 flex items-center justify-center group">
          {evidence.media_type === 'image' ? (
            <img
              src={fileUrl}
              alt={evidence.original_filename}
              className="w-full h-full object-contain"
              loading="lazy"
            />
          ) : evidence.media_type === 'video' ? (
            <video
              src={fileUrl}
              controls
              className="w-full h-full object-contain bg-black"
              preload="metadata"
            />
          ) : evidence.media_type === 'audio' ? (
            <div className="w-full p-3 flex flex-col items-center justify-center gap-2">
              <Music className="w-8 h-8 text-amber-400 opacity-80" />
              <audio controls src={fileUrl} className="w-full h-8" preload="metadata" />
            </div>
          ) : (
            <div className="text-center p-3">
              <FileText className="w-10 h-10 text-blue-400 mx-auto mb-1 opacity-80" />
              <span className="text-[11px] font-mono text-slate-400">Text Corpus</span>
            </div>
          )}

          {/* Quick open link */}
          <a
            href={fileUrl}
            target="_blank"
            rel="noopener noreferrer"
            title="Inspect raw original"
            className="absolute top-2 right-2 p-1.5 rounded bg-slate-900/80 text-slate-300 hover:text-white hover:bg-slate-800 border border-slate-700/60 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>

        {/* Title & Metadata */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <h4 className="text-sm font-semibold text-slate-200 truncate" title={evidence.original_filename}>
              {evidence.original_filename}
            </h4>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-[11px] font-mono px-2 py-0.5 rounded uppercase font-medium bg-slate-800 text-slate-300 border border-slate-700">
                {evidence.media_type}
              </span>
              <span className="text-xs text-slate-400 font-mono">
                {formatSize(evidence.file_size)}
              </span>
            </div>
          </div>

          {canDelete && onRemove && (
            <button
              onClick={() => onRemove(evidence.id)}
              title="Remove evidence"
              className="p-1.5 rounded text-slate-500 hover:text-red-400 hover:bg-red-950/40 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Forensic Chain of Custody & Hash */}
      <div className="mt-4 pt-3 border-t border-slate-800/80">
        <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
          <span className="flex items-center gap-1 text-slate-500">
            <ShieldCheck className="w-3.5 h-3.5 text-cyan-500" />
            SHA-256
          </span>
          <button
            onClick={copyHash}
            className="flex items-center gap-1 text-cyan-400 hover:text-cyan-300 font-mono transition-colors"
            title="Copy cryptographic hash"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-emerald-400" />
                <span className="text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                <span>{evidence.sha256 ? `${evidence.sha256.substring(0, 8)}...` : 'N/A'}</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

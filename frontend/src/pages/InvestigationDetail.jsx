import React, { useEffect, useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  getInvestigation,
  getEvidence,
  uploadEvidence,
  startAnalysis,
  getFindings,
  getCorrelations,
  downloadPdfReport,
} from '../services/api';
import StatusBadge from '../components/StatusBadge';
import UploadZone from '../components/UploadZone';
import EvidenceCard from '../components/EvidenceCard';
import FindingCard from '../components/FindingCard';
import CorrelationGraph from '../components/CorrelationGraph';
import {
  ArrowLeft,
  Play,
  Download,
  Layers,
  Search,
  Network,
  FileText,
  AlertCircle,
  CheckCircle2,
  Sparkles,
  ShieldAlert,
} from 'lucide-react';

export default function InvestigationDetail() {
  const { id } = useParams();
  const [investigation, setInvestigation] = useState(null);
  const [evidence, setEvidence] = useState([]);
  const [findings, setFindings] = useState([]);
  const [correlations, setCorrelations] = useState([]);
  const [activeTab, setActiveTab] = useState('evidence'); // 'evidence' | 'analysis' | 'correlations' | 'report'

  const [loading, setLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState('');
  const [mediaFilter, setMediaFilter] = useState('all');

  useEffect(() => {
    loadInvestigationData();
  }, [id]);

  const loadInvestigationData = async () => {
    try {
      setLoading(true);
      const [invRes, evRes] = await Promise.all([
        getInvestigation(id),
        getEvidence(id),
      ]);
      setInvestigation(invRes.data);
      setEvidence(evRes.data || []);

      // If analyzed, also fetch findings & correlations
      if (invRes.data.status === 'analyzed' || invRes.data.status === 'completed') {
        const [fRes, cRes] = await Promise.all([
          getFindings(id),
          getCorrelations(id),
        ]);
        setFindings(fRes.data || []);
        setCorrelations(cRes.data || []);
      }
    } catch (err) {
      console.error('Failed to load investigation:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleUploadFiles = async (files) => {
    setIsUploading(true);
    setUploadProgress(0);
    try {
      for (let i = 0; i < files.length; i++) {
        await uploadEvidence(id, files[i], (percent) => {
          setUploadProgress(percent);
        });
      }
      // Refresh evidence list
      const evRes = await getEvidence(id);
      setEvidence(evRes.data || []);
    } catch (err) {
      alert(err.response?.data?.detail || 'Upload failed');
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleRunAnalysis = async () => {
    if (evidence.length === 0) return;
    setIsAnalyzing(true);
    setAnalysisError('');
    try {
      await startAnalysis(id);
      // Refresh data
      const [invRes, fRes, cRes] = await Promise.all([
        getInvestigation(id),
        getFindings(id),
        getCorrelations(id),
      ]);
      setInvestigation(invRes.data);
      setFindings(fRes.data || []);
      setCorrelations(cRes.data || []);
      setActiveTab('analysis');
    } catch (err) {
      setAnalysisError(err.response?.data?.detail || 'Analysis execution failed');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleDownloadPdf = async () => {
    try {
      const res = await downloadPdfReport(id);
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `truthlens_report_${id.substring(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert('Failed to generate or download PDF report');
    }
  };

  const evidenceMap = useMemo(() => {
    const map = {};
    evidence.forEach((e) => {
      map[e.id] = e;
    });
    return map;
  }, [evidence]);

  const filteredFindings = useMemo(() => {
    if (mediaFilter === 'all') return findings;
    return findings.filter((f) => {
      const ev = evidenceMap[f.evidence_id];
      return ev?.media_type === mediaFilter;
    });
  }, [findings, mediaFilter, evidenceMap]);

  if (loading || !investigation) {
    return (
      <div className="p-12 text-center font-mono text-sm text-slate-500">
        Loading forensic case data...
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Top Breadcrumb & Action Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <Link
            to="/"
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="text-xl font-bold text-white tracking-tight">{investigation.title}</h2>
              <StatusBadge status={investigation.status} />
            </div>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              ID: {investigation.id} | Created: {new Date(investigation.created_at).toLocaleString()}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRunAnalysis}
            disabled={isAnalyzing || evidence.length === 0}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-medium text-xs transition-all shadow-md shadow-cyan-950 disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            {isAnalyzing ? 'Analyzing All Engines...' : 'Analyze Investigation'}
          </button>

          {(investigation.status === 'analyzed' || investigation.status === 'completed') && (
            <button
              onClick={handleDownloadPdf}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium text-xs transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              Download PDF Report
            </button>
          )}
        </div>
      </div>

      {/* Case Reference Context Box */}
      {investigation.reference_context && (
        <div className="p-4 bg-slate-900/90 border border-slate-800 rounded-xl text-xs space-y-1">
          <div className="flex items-center gap-1.5 font-semibold text-cyan-400 font-mono uppercase">
            <Sparkles className="w-3.5 h-3.5" />
            Reference Context Baseline
          </div>
          <p className="text-slate-300 leading-relaxed italic">
            "{investigation.reference_context}"
          </p>
        </div>
      )}

      {analysisError && (
        <div className="p-4 bg-rose-950/60 border border-rose-800 rounded-xl text-xs text-rose-300">
          {analysisError}
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-1">
        {[
          { key: 'evidence', label: 'Evidence Inventory', count: evidence.length, icon: Layers },
          { key: 'analysis', label: 'Forensic Findings', count: findings.length, icon: Search },
          { key: 'correlations', label: 'Cross-Modal Correlation', count: correlations.length, icon: Network },
          { key: 'report', label: 'Forensic Report', icon: FileText },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-semibold transition-all ${
                isActive
                  ? 'bg-blue-600/15 text-cyan-400 border border-blue-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span className="font-mono text-[10px] px-1.5 py-0.2 rounded-full bg-slate-800 text-slate-300">
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* TAB 1: Evidence Upload & Inventory */}
      {activeTab === 'evidence' && (
        <div className="space-y-6">
          <UploadZone
            onFilesSelected={handleUploadFiles}
            isUploading={isUploading}
            uploadProgress={uploadProgress}
          />

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-300">
                Uploaded Evidence ({evidence.length})
              </h3>
              <span className="text-xs font-mono text-slate-500">
                Immutable SHA-256 Chain of Custody
              </span>
            </div>

            {evidence.length === 0 ? (
              <div className="p-8 text-center text-slate-500 bg-slate-900/40 rounded-xl border border-slate-800 text-xs">
                No evidence items uploaded yet. Upload images, videos, audio, or text transcripts above.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {evidence.map((ev) => (
                  <EvidenceCard key={ev.id} evidence={ev} />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: Forensic Analysis Findings */}
      {activeTab === 'analysis' && (
        <div className="space-y-6">
          {/* Media type filter buttons */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-900 border border-slate-800 rounded-xl">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-mono">Filter by Media:</span>
              {['all', 'image', 'video', 'audio', 'text'].map((m) => (
                <button
                  key={m}
                  onClick={() => setMediaFilter(m)}
                  className={`text-xs px-2.5 py-1 rounded capitalize font-medium transition-colors ${
                    mediaFilter === m
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
            <span className="text-xs font-mono text-slate-500">
              Showing {filteredFindings.length} of {findings.length} findings
            </span>
          </div>

          {findings.length === 0 ? (
            <div className="p-12 text-center text-slate-500 bg-slate-900/40 rounded-xl border border-slate-800 space-y-3">
              <Search className="w-10 h-10 mx-auto opacity-50 text-slate-400" />
              <p className="text-sm font-medium">No analysis findings recorded</p>
              <p className="text-xs text-slate-500">
                Click "Analyze Investigation" to execute forensic engines on uploaded evidence.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredFindings.map((finding) => (
                <FindingCard key={finding.id} finding={finding} evidenceMap={evidenceMap} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Cross-Modal Correlation */}
      {activeTab === 'correlations' && (
        <CorrelationGraph
          evidence={evidence}
          findings={findings}
          correlations={correlations}
        />
      )}

      {/* TAB 4: Forensic Report */}
      {activeTab === 'report' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 space-y-8 shadow-sm">
          {/* Header */}
          <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-slate-800">
            <div>
              <div className="text-xs font-mono text-cyan-400 uppercase">TruthLens Digital Forensics</div>
              <h3 className="text-2xl font-bold text-white mt-1">Formal Investigation Report</h3>
              <p className="text-xs text-slate-400 font-mono mt-1">Case: {investigation.title} | ID: {investigation.id}</p>
            </div>
            <button
              onClick={handleDownloadPdf}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs transition-colors shadow-md"
            >
              <Download className="w-4 h-4" />
              Download Formal PDF Report
            </button>
          </div>

          {/* Core Principle Alert */}
          <div className="p-4 rounded-lg bg-amber-950/40 border border-amber-800/60 text-xs text-amber-300 leading-relaxed flex items-start gap-3">
            <ShieldAlert className="w-5 h-5 shrink-0 text-amber-400 mt-0.5" />
            <div>
              <strong className="block text-amber-200 mb-0.5">Mandatory Human Review Disclaimer:</strong>
              This automated report outputs empirical observations, heuristic indicators, and model-based metrics.
              Detection scores are indicators, never definitive verdicts. Absence of EXIF metadata does not prove manipulation, and ELA cannot independently confirm forgery. All conclusions require qualified human verification.
            </div>
          </div>

          {/* Evidence Inventory Table */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-slate-200">1. Evidence Inventory & Cryptographic Hashes</h4>
            <div className="overflow-x-auto border border-slate-800 rounded-lg">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="py-2.5 px-3">#</th>
                    <th className="py-2.5 px-3">Filename</th>
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3">Size</th>
                    <th className="py-2.5 px-3">SHA-256 Hash</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-300">
                  {evidence.map((ev, i) => (
                    <tr key={ev.id}>
                      <td className="py-2.5 px-3 text-slate-500">{i + 1}</td>
                      <td className="py-2.5 px-3 font-semibold text-slate-200">{ev.original_filename}</td>
                      <td className="py-2.5 px-3 uppercase text-cyan-400">{ev.media_type}</td>
                      <td className="py-2.5 px-3">{(ev.file_size / 1024).toFixed(1)} KB</td>
                      <td className="py-2.5 px-3 text-slate-400">{ev.sha256}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Cross-Modal Correlations */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-slate-200">2. Cross-Modal Correlations & Discrepancies</h4>
            {correlations.length > 0 ? (
              <div className="space-y-2">
                {correlations.map((c) => (
                  <div key={c.id} className="p-3.5 bg-slate-950 rounded-lg border border-slate-800 text-xs">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-bold text-cyan-400 font-mono uppercase">{c.relationship_type}</span>
                      <span className="text-slate-500 font-mono">| Strength: {c.strength} | Rule: {c.rule_id}</span>
                    </div>
                    <p className="text-slate-300 leading-normal">{c.explanation}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No cross-modal correlations recorded.</p>
            )}
          </div>

          {/* Limitations */}
          <div className="space-y-3 pt-4 border-t border-slate-800">
            <h4 className="text-sm font-semibold text-slate-200">3. System Limitations & Investigative Notes</h4>
            <ul className="space-y-1.5 text-xs text-slate-400 list-disc list-inside">
              <li>Image ELA highlights compression anomalies but cannot differentiate benign edits from deepfakes.</li>
              <li>Acoustic analysis reflects signal features; lossy codecs (MP3/AAC) can mimic synthetic speech cutoffs.</li>
              <li>Text contradiction detection operates on deterministic rule patterns rather than general artificial intelligence.</li>
              <li>Video frame inspection is sampled at interval intervals (hardware constraints max 15s window).</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

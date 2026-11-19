import React, { useMemo, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Network, AlertTriangle, CheckCircle, Clock, Link2, FileQuestion } from 'lucide-react';

const relationshipColors = {
  SUPPORTS: '#10b981', // green
  CONTRADICTS: '#f43f5e', // red/rose
  RELATED: '#3b82f6', // blue
  TIME_ALIGNED: '#a855f7', // purple
  SAME_CONTENT_CANDIDATE: '#06b6d4', // cyan
};

export default function CorrelationGraph({ evidence = [], findings = [], correlations = [] }) {
  const [selectedEdge, setSelectedEdge] = useState(null);

  // Index findings and evidence for fast lookup
  const findingMap = useMemo(() => {
    const map = {};
    findings.forEach((f) => {
      map[f.id] = f;
    });
    return map;
  }, [findings]);

  const evidenceMap = useMemo(() => {
    const map = {};
    evidence.forEach((e) => {
      map[e.id] = e;
    });
    return map;
  }, [evidence]);

  // Construct Nodes and Edges
  const { nodes, edges } = useMemo(() => {
    const nodeList = [];
    const edgeList = [];

    // Filter to findings that actually have correlations to keep the graph relevant
    const activeFindingIds = new Set();
    correlations.forEach((c) => {
      activeFindingIds.add(c.source_finding_id);
      activeFindingIds.add(c.target_finding_id);
    });

    // 1. Evidence Nodes (Top/Left row)
    const activeEvidenceIds = new Set();
    activeFindingIds.forEach((fid) => {
      const f = findingMap[fid];
      if (f && f.evidence_id) activeEvidenceIds.add(f.evidence_id);
    });

    const evList = evidence.filter((e) => activeEvidenceIds.has(e.id));
    const evSpacing = 320;
    evList.forEach((ev, idx) => {
      nodeList.push({
        id: `ev-${ev.id}`,
        type: 'default',
        position: { x: idx * evSpacing + 50, y: 50 },
        data: {
          label: (
            <div className="p-2 text-left">
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-cyan-400 border border-slate-700">
                {ev.media_type} Evidence
              </span>
              <p className="font-semibold text-xs text-slate-100 truncate mt-1 w-48" title={ev.original_filename}>
                {ev.original_filename}
              </p>
            </div>
          ),
        },
        style: {
          background: '#0f172a',
          border: '1px solid #334155',
          borderRadius: '10px',
          color: '#f8fafc',
          width: 220,
        },
      });
    });

    // 2. Finding Nodes (Placed below evidence nodes)
    const findingsToRender = findings.filter((f) => activeFindingIds.has(f.id));
    findingsToRender.forEach((f, idx) => {
      const evIdx = evList.findIndex((e) => e.id === f.evidence_id);
      const baseX = evIdx >= 0 ? evIdx * evSpacing + 50 : (idx % 4) * 260 + 50;
      const yOffset = 200 + Math.floor(idx / Math.max(1, evList.length)) * 140;

      nodeList.push({
        id: f.id,
        type: 'default',
        position: { x: baseX + (idx % 2 === 0 ? -20 : 20), y: yOffset },
        data: {
          label: (
            <div className="p-2 text-left text-xs">
              <div className="flex items-center justify-between gap-1 mb-1">
                <span className="font-mono text-[10px] text-blue-400 font-medium">
                  {f.engine}
                </span>
                <span className="text-[10px] px-1 py-0.2 rounded bg-slate-800 text-slate-300">
                  {f.confidence_band}
                </span>
              </div>
              <p className="font-medium text-slate-200 line-clamp-2 text-[11px]" title={f.description}>
                {f.indicator}: {f.description}
              </p>
            </div>
          ),
        },
        style: {
          background: '#1e293b',
          border: '1px solid #475569',
          borderRadius: '8px',
          color: '#e2e8f0',
          width: 210,
        },
      });

      // Link evidence to its finding with subtle dashed edge
      if (f.evidence_id) {
        edgeList.push({
          id: `link-ev-${f.id}`,
          source: `ev-${f.evidence_id}`,
          target: f.id,
          style: { stroke: '#475569', strokeDasharray: '4 4', strokeWidth: 1.2 },
          animated: false,
        });
      }
    });

    // 3. Correlation Edges (Colored per relationship type)
    correlations.forEach((c) => {
      const color = relationshipColors[c.relationship_type] || '#94a3b8';
      edgeList.push({
        id: c.id,
        source: c.source_finding_id,
        target: c.target_finding_id,
        label: `${c.relationship_type} (${c.strength})`,
        data: c,
        animated: c.relationship_type === 'CONTRADICTS' || c.relationship_type === 'TIME_ALIGNED',
        style: {
          stroke: color,
          strokeWidth: 2.5,
        },
        labelStyle: {
          fill: color,
          fontWeight: 700,
          fontSize: 10,
          fontFamily: 'monospace',
        },
        labelBgStyle: {
          fill: '#0f172a',
          fillOpacity: 0.9,
          stroke: color,
          strokeWidth: 0.5,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: color,
        },
      });
    });

    return { nodes: nodeList, edges: edgeList };
  }, [evidence, findings, correlations, findingMap]);

  const onEdgeClick = (_, edge) => {
    if (edge.data) {
      setSelectedEdge(edge.data);
    }
  };

  return (
    <div className="space-y-4">
      {/* Legend Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-slate-900 border border-slate-800 rounded-xl text-xs">
        <div className="flex items-center gap-2">
          <Network className="w-4 h-4 text-cyan-400" />
          <span className="font-semibold text-slate-200">Cross-Modal Relationship Graph</span>
        </div>
        <div className="flex flex-wrap items-center gap-4 text-xs font-mono">
          {Object.entries(relationshipColors).map(([type, color]) => (
            <div key={type} className="flex items-center gap-1.5">
              <span className="w-3 h-1 rounded-full" style={{ backgroundColor: color }}></span>
              <span className="text-slate-300 font-medium">{type}</span>
            </div>
          ))}
        </div>
      </div>

      {/* React Flow Viewport */}
      <div className="h-[520px] bg-slate-950 border border-slate-800 rounded-xl overflow-hidden relative shadow-inner">
        {nodes.length > 0 ? (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onEdgeClick={onEdgeClick}
            fitView
            attributionPosition="bottom-left"
          >
            <Background color="#1e293b" gap={20} size={1} />
            <Controls className="bg-slate-900 border-slate-800 text-slate-300" />
            <MiniMap
              nodeColor={(n) => (n.id.startsWith('ev-') ? '#0ea5e9' : '#64748b')}
              maskColor="rgba(15, 23, 42, 0.75)"
              className="bg-slate-900 border border-slate-800 rounded"
            />
          </ReactFlow>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-slate-500">
            <FileQuestion className="w-10 h-10 mb-2 opacity-50" />
            <p className="text-sm font-medium">No cross-modal correlations identified yet</p>
            <p className="text-xs text-slate-600 mt-1">Run analysis on multi-item evidence to generate relationship graph</p>
          </div>
        )}
      </div>

      {/* Selected Relationship Detail Card */}
      {selectedEdge && (
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl text-xs space-y-2 animate-fadeIn">
          <div className="flex items-center justify-between">
            <span
              className="font-mono font-bold uppercase px-2 py-0.5 rounded text-xs"
              style={{
                backgroundColor: `${relationshipColors[selectedEdge.relationship_type]}15`,
                color: relationshipColors[selectedEdge.relationship_type],
                border: `1px solid ${relationshipColors[selectedEdge.relationship_type]}40`,
              }}
            >
              {selectedEdge.relationship_type}
            </span>
            <span className="text-slate-400 font-mono">
              Correlation Strength: {selectedEdge.strength} | Rule: {selectedEdge.rule_id}
            </span>
          </div>
          <p className="text-slate-200 text-sm leading-relaxed">
            {selectedEdge.explanation}
          </p>
        </div>
      )}

      {/* Readable Tabular Correlation List */}
      <div className="mt-6">
        <h4 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
          <span>Correlated Relationships List</span>
          <span className="text-xs font-mono text-slate-500 font-normal">({correlations.length} connections)</span>
        </h4>

        {correlations.length > 0 ? (
          <div className="space-y-3">
            {correlations.map((corr) => {
              const srcF = findingMap[corr.source_finding_id];
              const tgtF = findingMap[corr.target_finding_id];
              const color = relationshipColors[corr.relationship_type] || '#94a3b8';

              return (
                <div
                  key={corr.id}
                  onClick={() => setSelectedEdge(corr)}
                  className="p-4 bg-slate-900 border border-slate-800 rounded-lg hover:border-slate-700 transition-all cursor-pointer shadow-sm"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <span
                        className="px-2 py-0.5 rounded text-xs font-mono font-bold"
                        style={{
                          backgroundColor: `${color}15`,
                          color: color,
                          border: `1px solid ${color}40`,
                        }}
                      >
                        {corr.relationship_type}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">
                        Rule: {corr.rule_id}
                      </span>
                    </div>
                    <span className="text-xs font-mono text-cyan-400">
                      Strength: {corr.strength}
                    </span>
                  </div>

                  <p className="text-sm text-slate-200 leading-relaxed mb-2">
                    {corr.explanation}
                  </p>

                  <div className="flex flex-wrap gap-4 text-xs font-mono text-slate-400 pt-2 border-t border-slate-800/80">
                    <div>
                      <span className="text-slate-500">Source: </span>
                      <span className="text-slate-300">{srcF?.indicator || 'Finding 1'}</span> ({srcF?.engine})
                    </div>
                    <div>
                      <span className="text-slate-500">Target: </span>
                      <span className="text-slate-300">{tgtF?.indicator || 'Finding 2'}</span> ({tgtF?.engine})
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-8 text-center text-slate-500 bg-slate-900/50 rounded-lg border border-slate-800">
            No cross-evidence correlations recorded.
          </div>
        )}
      </div>
    </div>
  );
}

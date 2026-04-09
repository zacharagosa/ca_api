import React, { useEffect, useRef, useCallback, useMemo, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

// Color palette for different node types
const NODE_COLORS = {
  Clan: '#f59e0b',     // Amber - Clans stand out
  Player: '#3b82f6',   // Blue - Players
  Item: '#10b981',     // Green - Items
  Friend: '#8b5cf6',   // Purple - Friend relationships
  default: '#6b7280'   // Gray - fallback
};

const NODE_SIZES = {
  Clan: 14,            // Clans are larger (hub nodes)
  Player: 10,          // Players are medium
  Item: 8,             // Items are smaller
  Friend: 10,
  default: 10
};

const GraphRenderer = ({ data, width, height }) => {
  const fgRef = useRef();
  const [focusedNode, setFocusedNode] = useState(null);
  const [viewMode, setViewMode] = useState('all'); // 'all' or 'focused'

  // Compute which groups are actually present in the data
  const presentGroups = useMemo(() => {
    if (!data || !data.nodes) return [];
    const groups = new Set(data.nodes.map(n => n.group).filter(Boolean));
    return Array.from(groups);
  }, [data]);

  // Filter data based on focused node for drill-down view
  const filteredData = useMemo(() => {
    if (!data || !data.nodes || !data.links) return data;
    if (!focusedNode || viewMode === 'all') return data;

    // Find all nodes connected to the focused node
    const connectedNodeIds = new Set([focusedNode.id]);
    data.links.forEach(link => {
      const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
      const targetId = typeof link.target === 'object' ? link.target.id : link.target;
      if (sourceId === focusedNode.id) connectedNodeIds.add(targetId);
      if (targetId === focusedNode.id) connectedNodeIds.add(sourceId);
    });

    // Filter nodes and links
    const filteredNodes = data.nodes.filter(n => connectedNodeIds.has(n.id));
    const filteredLinks = data.links.filter(link => {
      const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
      const targetId = typeof link.target === 'object' ? link.target.id : link.target;
      return connectedNodeIds.has(sourceId) && connectedNodeIds.has(targetId);
    });

    return { nodes: filteredNodes, links: filteredLinks };
  }, [data, focusedNode, viewMode]);

  useEffect(() => {
    if (fgRef.current) {
      // Adjust force simulation for better spread
      fgRef.current.d3Force('charge').strength(-300);
      fgRef.current.d3Force('link').distance(100);

      // Zoom to fit after initial render
      setTimeout(() => {
        fgRef.current.zoomToFit(400, 80);
      }, 500);
    }
  }, [filteredData]);

  // Handle node click for drill-down
  const handleNodeClick = useCallback((node) => {
    if (focusedNode && focusedNode.id === node.id) {
      // Double-click same node = go back to all view
      setFocusedNode(null);
      setViewMode('all');
    } else {
      setFocusedNode(node);
      setViewMode('focused');
    }
  }, [focusedNode]);

  // Reset to full view
  const handleResetView = useCallback(() => {
    setFocusedNode(null);
    setViewMode('all');
    setTimeout(() => {
      fgRef.current?.zoomToFit(400, 80);
    }, 100);
  }, []);

  // Custom node rendering for better visibility and hierarchy
  const drawNode = useCallback((node, ctx, globalScale) => {
    const group = node.group || 'default';
    const baseSize = NODE_SIZES[group] || NODE_SIZES.default;
    // Make focused node larger
    const size = focusedNode && focusedNode.id === node.id ? baseSize * 1.5 : baseSize;
    const color = NODE_COLORS[group] || NODE_COLORS.default;
    const label = node.label || node.id || '';

    // Check if this node is the focused one
    const isFocused = focusedNode && focusedNode.id === node.id;

    // Draw node circle with glow effect
    ctx.beginPath();
    ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);

    // Glow effect for Clans or focused nodes
    if (group === 'Clan' || isFocused) {
      ctx.shadowColor = color;
      ctx.shadowBlur = isFocused ? 20 : 15;
    }

    ctx.fillStyle = color;
    ctx.fill();

    // Border - thicker for focused node
    ctx.strokeStyle = isFocused ? '#000' : '#374151';
    ctx.lineWidth = isFocused ? 3 : (group === 'Clan' ? 2 : 1);
    ctx.stroke();

    // Reset shadow
    ctx.shadowBlur = 0;

    // Draw label - always show for focused view or when zoomed in
    const fontSize = Math.max(12 / globalScale, 4);
    if (globalScale > 0.4 || viewMode === 'focused') {
      ctx.font = `${isFocused ? 'bold ' : ''}${fontSize}px Inter, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';

      // Text background for readability
      const textMetrics = ctx.measureText(label);
      const textHeight = fontSize;
      ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
      ctx.fillRect(
        node.x - textMetrics.width / 2 - 3,
        node.y + size + 3,
        textMetrics.width + 6,
        textHeight + 4
      );

      // Text
      ctx.fillStyle = '#1f2937';
      ctx.fillText(label, node.x, node.y + size + 5);
    }
  }, [focusedNode, viewMode]);

  // Custom link rendering for visible connections
  const drawLink = useCallback((link, ctx, globalScale) => {
    const start = link.source;
    const end = link.target;

    if (!start || !end || typeof start.x === 'undefined') return;

    // Gradient line based on source/target types
    const sourceColor = NODE_COLORS[start.group] || NODE_COLORS.default;
    const targetColor = NODE_COLORS[end.group] || NODE_COLORS.default;

    // Make links to/from focused node more prominent
    const isFocusedLink = focusedNode &&
      (start.id === focusedNode.id || end.id === focusedNode.id);

    const gradient = ctx.createLinearGradient(start.x, start.y, end.x, end.y);
    gradient.addColorStop(0, isFocusedLink ? sourceColor : sourceColor + '60');
    gradient.addColorStop(1, isFocusedLink ? targetColor : targetColor + '60');

    ctx.beginPath();
    ctx.moveTo(start.x, start.y);
    ctx.lineTo(end.x, end.y);
    ctx.strokeStyle = gradient;
    ctx.lineWidth = isFocusedLink ? 3 : 2;
    ctx.stroke();

    // Draw arrow for directed relationships
    const arrowLength = isFocusedLink ? 10 : 8;
    const dx = end.x - start.x;
    const dy = end.y - start.y;
    const angle = Math.atan2(dy, dx);

    // Position arrow near the target node
    const targetSize = NODE_SIZES[end.group] || NODE_SIZES.default;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < targetSize + 10) return; // Don't draw arrow for very short links

    const arrowX = start.x + (dist - targetSize - 8) / dist * dx;
    const arrowY = start.y + (dist - targetSize - 8) / dist * dy;

    ctx.beginPath();
    ctx.moveTo(arrowX, arrowY);
    ctx.lineTo(
      arrowX - arrowLength * Math.cos(angle - Math.PI / 6),
      arrowY - arrowLength * Math.sin(angle - Math.PI / 6)
    );
    ctx.lineTo(
      arrowX - arrowLength * Math.cos(angle + Math.PI / 6),
      arrowY - arrowLength * Math.sin(angle + Math.PI / 6)
    );
    ctx.closePath();
    ctx.fillStyle = targetColor;
    ctx.fill();
  }, [focusedNode]);

  if (!data || !data.nodes || !data.links) return null;

  return (
    <div className="relative w-full h-full overflow-hidden rounded-lg" style={{ backgroundColor: '#ffffff' }}>
      {/* Legend - Dynamic based on actual data */}
      <div className="absolute top-2 left-2 z-10 bg-white/95 p-2 rounded-lg border border-gray-300 text-xs shadow-sm">
        <div className="font-semibold text-gray-800 mb-1">Legend</div>
        {presentGroups.map((group) => (
          <div key={group} className="flex items-center gap-2 text-gray-700">
            <span
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: NODE_COLORS[group] || NODE_COLORS.default }}
            />
            {group}s
          </div>
        ))}
        {presentGroups.length === 0 && (
          <div className="text-gray-500 italic">No data</div>
        )}
      </div>

      {/* Drill-down controls */}
      <div className="absolute top-2 right-2 z-10 flex gap-2">
        {viewMode === 'focused' && focusedNode && (
          <div className="bg-blue-500 text-white px-3 py-1.5 rounded-lg text-xs shadow-sm flex items-center gap-2">
            <span>Viewing: <strong>{focusedNode.label || focusedNode.id}</strong></span>
            <span className="text-blue-200">({filteredData.nodes?.length} nodes)</span>
          </div>
        )}
        {viewMode === 'focused' && (
          <button
            onClick={handleResetView}
            className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-1.5 rounded-lg text-xs shadow-sm flex items-center gap-1 transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="1 4 1 10 7 10"></polyline>
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
            </svg>
            Show All
          </button>
        )}
      </div>

      {/* Hint for drill-down */}
      {viewMode === 'all' && data.nodes?.length > 5 && (
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 z-10 bg-gray-800/80 text-white px-3 py-1.5 rounded-full text-xs">
          💡 Click a node to focus on its connections
        </div>
      )}

      <ForceGraph2D
        ref={fgRef}
        width={width || 600}
        height={height || 400}
        graphData={filteredData}
        nodeCanvasObject={drawNode}
        nodePointerAreaPaint={(node, color, ctx) => {
          const size = NODE_SIZES[node.group] || NODE_SIZES.default;
          ctx.beginPath();
          ctx.arc(node.x, node.y, size + 6, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
        }}
        linkCanvasObject={drawLink}
        linkDirectionalParticles={viewMode === 'focused' ? 3 : 1}
        linkDirectionalParticleWidth={3}
        linkDirectionalParticleColor={() => '#3b82f6'}
        enableNodeDrag={true}
        enableZoomInteraction={true}
        backgroundColor="#ffffff"
        cooldownTicks={100}
        onNodeClick={handleNodeClick}
        onEngineStop={() => fgRef.current?.zoomToFit(400, 80)}
      />
    </div>
  );
};

export default GraphRenderer;

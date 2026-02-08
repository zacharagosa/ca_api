
import React, { useEffect, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

const GraphRenderer = ({ data, width, height }) => {
  const fgRef = useRef();

  useEffect(() => {
    if (fgRef.current) {
      fgRef.current.d3Force('charge').strength(-120);
    }
  }, []);

  if (!data || !data.nodes || !data.links) return null;

  return (
    <div className="border rounded-md overflow-hidden bg-card">
        <ForceGraph2D
          ref={fgRef}
          width={width || 600}
          height={height || 400}
          graphData={data}
          nodeLabel="id"
          nodeAutoColorBy="group"
          linkDirectionalArrowLength={3.5}
          linkDirectionalArrowRelPos={1}
          linkCurvature={0.25}
          backgroundColor="#1f2937" // Dark background for contrast
        />
    </div>
  );
};

export default GraphRenderer;

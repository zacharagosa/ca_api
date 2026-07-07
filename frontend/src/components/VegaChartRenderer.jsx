import { useMemo, useEffect, useRef } from 'react';
import vegaEmbed from 'vega-embed';

/**
 * VegaChartRenderer - Renders Vega-Lite specs from API v2 fast mode responses.
 * 
 * The API returns a vega_config object with encoding, data, mark, and title.
 * This component wraps it with proper sizing and light theme defaults.
 */
const VegaChartRenderer = ({ vegaConfig, data, width = 'container', height = 250 }) => {
    const containerRef = useRef(null);

    // Build the complete Vega-Lite spec with defaults
    const spec = useMemo(() => {
        try {
            const safeVegaConfig = vegaConfig ? JSON.parse(JSON.stringify(vegaConfig)) : null;
            if (!safeVegaConfig) return null;

            // Handle nested config (API v2 often wraps the spec in a "vega_config" key)
            const actualConfig = safeVegaConfig.vega_config || safeVegaConfig;

            const hasVisuals = actualConfig.mark || actualConfig.layer || actualConfig.concat || actualConfig.vconcat || actualConfig.hconcat;
            if (!hasVisuals) return null;

            const finalSpec = {
                $schema: 'https://vega.github.io/schema/vega-lite/v6.json',
                width: width === 'container' ? 'container' : (width || 500),
                height: height || 250,
                autosize: {
                    type: 'fit',
                    contains: 'padding'
                },
                ...actualConfig,
                config: {
                    background: 'transparent',
                    view: { stroke: 'transparent' },
                    axis: {
                        labelColor: '#6B7280', titleColor: '#374151', gridColor: '#E5E7EB',
                        domainColor: '#D1D5DB', tickColor: '#D1D5DB'
                    },
                    legend: { labelColor: '#6B7280', titleColor: '#374151' },
                    title: { color: '#111827', fontSize: 14, fontWeight: 600 },
                    bar: { color: '#3B82F6' },
                    line: { color: '#3B82F6', strokeWidth: 2 },
                    point: { color: '#3B82F6' },
                    area: { color: '#3B82F6', opacity: 0.3 },
                    ...(actualConfig.config || {})
                }
            };

            // Safely inject data only if the spec does not already embed data under datasets or values
            const hasEmbeddedData = (actualConfig.datasets && Object.keys(actualConfig.datasets).length > 0) || 
                                     (actualConfig.data && Array.isArray(actualConfig.data.values)) ||
                                     (actualConfig.data && actualConfig.data.values);

            if (!hasEmbeddedData && data && data.rows && data.rows.length > 0) {
                // Overwrite data entirely to drop the "name" attribute, forcing Vega-Lite to process it as inline data
                finalSpec.data = { values: data.rows };
            }

            return finalSpec;
        } catch (e) {
            console.error("Vega spec generation error:", e);
            return null;
        }
    }, [vegaConfig, data, width, height]);

    useEffect(() => {
        if (!containerRef.current || !spec) return;

        let viewPromise = null;
        try {
            viewPromise = vegaEmbed(containerRef.current, spec, {
                actions: false,
                renderer: 'svg',
                width: 'container'
            });
        } catch (err) {
            console.error("Vega embedding error:", err);
        }

        return () => {
            if (viewPromise) {
                viewPromise.then(res => {
                    if (res && typeof res.finalize === 'function') {
                        res.finalize();
                    }
                }).catch(() => {});
            }
        };
    }, [spec]);

    if (!spec) return null;

    return (
        <div 
            ref={containerRef}
            className="w-full min-h-[250px] min-w-[300px]" 
            style={{ width: '100%', minHeight: '250px' }} 
        />
    );
};

export default VegaChartRenderer;

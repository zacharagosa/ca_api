import { useMemo } from 'react';
import { VegaEmbed } from 'react-vega';

/**
 * VegaChartRenderer - Renders Vega-Lite specs from API v2 fast mode responses.
 * 
 * The API returns a vega_config object with encoding, data, mark, and title.
 * This component wraps it with proper sizing and light theme defaults.
 */
const VegaChartRenderer = ({ vegaConfig, width = 'container', height = 250 }) => {
    // Build the complete Vega-Lite spec with defaults
    const spec = useMemo(() => {
        if (!vegaConfig) return null;

        // Basic validation - must have minimal Vega-Lite properties
        // If it's an empty object or lacks visual definitions, don't render
        const hasVisuals = vegaConfig.mark || vegaConfig.layer || vegaConfig.concat || vegaConfig.vconcat || vegaConfig.hconcat;
        if (!hasVisuals) return null;

        return {
            $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
            width: width,
            height: height,
            autosize: {
                type: 'fit',
                contains: 'padding'
            },
            // Merge in the config from API
            ...vegaConfig,
            // Override config for light theme styling
            config: {
                background: 'transparent',
                view: {
                    stroke: 'transparent'
                },
                axis: {
                    labelColor: '#6B7280',
                    titleColor: '#374151',
                    gridColor: '#E5E7EB',
                    domainColor: '#D1D5DB',
                    tickColor: '#D1D5DB'
                },
                legend: {
                    labelColor: '#6B7280',
                    titleColor: '#374151'
                },
                title: {
                    color: '#111827',
                    fontSize: 14,
                    fontWeight: 600
                },
                bar: {
                    color: '#3B82F6'
                },
                line: {
                    color: '#3B82F6',
                    strokeWidth: 2
                },
                point: {
                    color: '#3B82F6'
                },
                area: {
                    color: '#3B82F6',
                    opacity: 0.3
                },
                ...vegaConfig.config
            }
        };
    }, [vegaConfig, width, height]);

    if (!spec) return null;

    return (
        <div className="w-full">
            <VegaEmbed
                spec={spec}
                options={{
                    actions: false,
                    renderer: 'svg'
                }}
            />
        </div>
    );
};

export default VegaChartRenderer;

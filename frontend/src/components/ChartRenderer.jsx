import React from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, ArcElement, Filler } from 'chart.js';
import { Bar, Line, Pie, Scatter } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler
);

const ChartRenderer = ({ config }) => {
  // Comprehensive validation - return null for any invalid config
  if (!config || !config.data) return null;

  // Detect Chart.js format (from frontend heuristic) vs ChartRenderer format (from backend)
  // Chart.js format has config.data.labels and config.data.datasets
  // ChartRenderer format has config.data as array and config.series
  const isChartJsFormat = config.data && Array.isArray(config.data.labels) && Array.isArray(config.data.datasets);

  if (isChartJsFormat) {
    // Additional validation for Chart.js format
    if (!config.data.labels || !config.data.datasets || config.data.datasets.length === 0) {
      return null;
    }

    // Render directly using Chart.js format with light theme
    const chartType = config.type || 'bar';
    const lightThemeOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
          labels: { color: 'hsl(var(--foreground))', font: { size: 12 } }
        },
        title: config.options?.plugins?.title ? {
          ...config.options.plugins.title,
          color: 'hsl(var(--foreground))',
          font: { size: 14, weight: 'bold' }
        } : undefined
      },
      scales: {
        x: { ticks: { color: 'hsl(var(--muted-foreground))' }, grid: { color: 'hsl(var(--border))' } },
        y: { ticks: { color: 'hsl(var(--muted-foreground))' }, grid: { color: 'hsl(var(--border))' } }
      }
    };
    // Merge user options with light theme defaults
    const options = { ...lightThemeOptions, ...(config.options || {}) };

    if (chartType === 'bar') return <Bar options={options} data={config.data} />;
    if (chartType === 'line' || chartType === 'area') return <Line options={options} data={config.data} />;
    if (chartType === 'pie') return <Pie options={options} data={config.data} />;
    return <Bar options={options} data={config.data} />;
  }

  // Original ChartRenderer format handling
  if (!Array.isArray(config.data) || !Array.isArray(config.series) || config.series.length === 0) return null;

  const hasRightAxis = config.series.some(s => s.yAxisID === 'right');

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: 'hsl(var(--foreground))',
          font: { size: 12 }
        }
      },
      title: {
        display: !!config.title,
        text: config.title,
        color: 'hsl(var(--foreground))',
        font: { size: 14, weight: 'bold' }
      },
    },
    scales: {
      x: {
        stacked: config.stacked,
        ticks: { color: 'hsl(var(--muted-foreground))' },
        grid: { color: 'hsl(var(--border))' },
      },
      y: {
        type: 'linear',
        display: true,
        position: 'left',
        stacked: config.stacked,
        ticks: { color: 'hsl(var(--muted-foreground))' },
        grid: { color: 'hsl(var(--border))' },
      },
      ...(hasRightAxis && {
        y1: {
          type: 'linear',
          display: true,
          position: 'right',
          grid: {
            drawOnChartArea: false,
          },
          stacked: config.stacked,
          ticks: { color: 'hsl(var(--muted-foreground))' },
        }
      }),
    },
  };

  const chartData = {
    labels: config.data.map(item => item[config.xAxisKey]),
    datasets: config.series.map((s, i) => ({
      label: s.name,
      data: config.data.map(item => item[s.dataKey]),
      backgroundColor: s.fillColor || `hsla(${i * 60}, 70%, 50%, 0.5)`,
      borderColor: s.strokeColor || `hsla(${i * 60}, 70%, 50%, 1)`,
      borderWidth: 1,
      yAxisID: s.yAxisID === 'right' ? 'y1' : 'y',
      fill: config.type === 'area' || s.type === 'area',
    })),
  };

  const renderChart = () => {
    // Basic types
    if (config.type === 'bar') return <Bar options={options} data={chartData} />;
    if (config.type === 'line' || config.type === 'area') return <Line options={options} data={chartData} />;

    if (config.type === 'pie') {
      const pieData = {
        ...chartData,
        datasets: chartData.datasets.map(ds => ({
          ...ds,
          backgroundColor: config.data.map((_, i) => `hsla(${i * 45}, 70%, 50%, 0.5)`),
          borderColor: config.data.map((_, i) => `hsla(${i * 45}, 70%, 50%, 1)`),
        }))
      };
      return <Pie options={options} data={pieData} />;
    }

    if (config.type === 'scatter') {
      const scatterData = {
        datasets: config.series.map((s, i) => ({
          label: s.name,
          data: config.data.map(item => ({
            x: item[config.xAxisKey],
            y: item[s.dataKey]
          })),
          backgroundColor: s.fillColor || `hsla(${i * 60}, 70%, 50%, 0.5)`,
        }))
      }
      return <Scatter options={options} data={scatterData} />;
    }

    if (config.type === 'combo') {
      // Combo chart usually uses 'Bar' component with mixed types in datasets
      const comboData = {
        labels: config.data.map(item => item[config.xAxisKey]),
        datasets: config.series.map((s, i) => ({
          type: s.type || 'bar', // 'line' or 'bar'
          label: s.name,
          data: config.data.map(item => item[s.dataKey]),
          backgroundColor: s.fillColor || `hsla(${i * 60}, 70%, 50%, 0.5)`,
          borderColor: s.strokeColor || `hsla(${i * 60}, 70%, 50%, 1)`,
          borderWidth: 1,
          yAxisID: s.yAxisID === 'right' ? 'y1' : 'y',
        }))
      };
      return <Bar options={options} data={comboData} />;
    }

    return null;
  };

  return (
    <div className="chart-container-wrapper">
      {renderChart()}
    </div>
  );
};

export default ChartRenderer;

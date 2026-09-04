import { clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(val) {
  if (val === null || val === undefined) return '$0'
  const num = typeof val === 'string' ? parseFloat(val.replace(/[^0-9.-]+/g, '')) : val
  if (isNaN(num)) return '$0'
  if (num >= 1000000) return `$${(num / 1000000).toFixed(2)}M`
  if (num >= 1000) return `$${(num / 1000).toFixed(1)}k`
  return `$${num.toLocaleString()}`
}

export function formatNumber(val) {
  if (val === null || val === undefined) return '0'
  const num = typeof val === 'string' ? parseFloat(val.replace(/[^0-9.-]+/g, '')) : val
  if (isNaN(num)) return '0'
  if (num >= 1000000) return `${(num / 1000000).toFixed(2)}M`
  if (num >= 1000) return `${(num / 1000).toFixed(1)}k`
  return num.toLocaleString()
}

export function getCategoryBadgeColor(category) {
  switch (category) {
    case 'metrics_fast':
      return 'bg-amber-500/10 text-amber-400 border-amber-500/30'
    case 'social_graph':
      return 'bg-purple-500/10 text-purple-400 border-purple-500/30'
    case 'dashboard_builder':
      return 'bg-sky-500/10 text-sky-400 border-sky-500/30'
    case 'deep_research':
      return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
    default:
      return 'bg-slate-500/10 text-slate-400 border-slate-500/30'
  }
}

export function getCategoryName(category) {
  switch (category) {
    case 'metrics_fast':
      return 'Quantitative Metrics'
    case 'social_graph':
      return 'Spanner Social Graph'
    case 'dashboard_builder':
      return 'Dashboard Architect'
    case 'deep_research':
      return 'Deep Research'
    default:
      return category
  }
}

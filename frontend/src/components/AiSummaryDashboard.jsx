import React, { useState, useEffect, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { 
  RefreshCw, Sparkles, TrendingUp, TrendingDown, DollarSign, Users, 
  Activity, Clock, ExternalLink, Play, Terminal, X, Loader2, CheckCircle, 
  Settings, Pause, Sliders, AlertTriangle, ShieldCheck, BarChart2, Radio,
  Send, Bot, Zap, ArrowUpRight
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ChartRenderer from './ChartRenderer';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const ChangeBadge = ({ change, label = "vs day before", isPositive = true, color = "emerald" }) => {
  const isPos = typeof change === 'number' ? change >= 0 : !String(change).startsWith('-');
  const badgeColor = color || (isPos ? "emerald" : "rose");
  
  const colors = {
    emerald: "bg-emerald-50 text-emerald-700 border-emerald-200/60 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800/40",
    rose: "bg-rose-50 text-rose-700 border-rose-200/60 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800/40",
    blue: "bg-blue-50 text-blue-700 border-blue-200/60 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800/40",
    amber: "bg-amber-50 text-amber-800 border-amber-200/60 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800/40"
  };

  const formattedChange = typeof change === 'number' ? (change > 0 ? `+${change}%` : `${change}%`) : change;

  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold border ${colors[badgeColor] || colors.emerald}`}>
      {isPos ? <TrendingUp size={11} className="shrink-0" /> : <TrendingDown size={11} className="shrink-0" />}
      {formattedChange} {label}
    </span>
  );
};

const formatVal = (val, isCurrency = false) => {
  if (val == null) return '-';
  const num = Number(val);
  if (isNaN(num)) return '-';
  if (isCurrency) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(num);
  }
  return new Intl.NumberFormat('en-US').format(num);
};

const AiSummaryDashboard = () => {
  const [data, setData] = useState(null);
  const [selectedGame, setSelectedGame] = useState('overall');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [filterType, setFilterType] = useState('all');

  // Agentic Workflows State
  const [activeWorkflow, setActiveWorkflow] = useState(null);
  const [workflowLogs, setWorkflowLogs] = useState([]);
  const [workflowStatus, setWorkflowStatus] = useState('idle');
  const [isWorkflowModalOpen, setIsWorkflowModalOpen] = useState(false);
  const eventSourceRef = useRef(null);

  // GCF Pipeline Manager State
  const [isGcfPaused, setIsGcfPaused] = useState(false);
  const [gcfSchedule, setGcfSchedule] = useState('0 8 * * *');
  const [gcfTargetSegment, setGcfTargetSegment] = useState('All Active Players');
  const [gcfAlertEmail, setGcfAlertEmail] = useState('');
  const [gcfThreshold, setGcfThreshold] = useState('10%');
  const [showGcfSettings, setShowGcfSettings] = useState(false);
  const [gcfAction, setGcfAction] = useState(null);

  const fetchSummary = async (isRefresh = false) => {
    try {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      setError(null);

      const endpoint = `${API_BASE_URL}/api/daily-summary`;
      const res = await fetch(endpoint, {
        method: isRefresh ? 'POST' : 'GET',
        headers: { 'Content-Type': 'application/json' },
        body: isRefresh ? JSON.stringify({ force_refresh: true }) : undefined
      });

      if (!res.ok) throw new Error(`Server returned ${res.status}: ${res.statusText}`);
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.error('Error fetching daily summary:', err);
      setError(err.message || 'Failed to load AI summary data.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  const runWorkflow = (workflowId, action = null) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setWorkflowLogs([]);
    setWorkflowStatus('running');
    setActiveWorkflow(workflowId);
    setGcfAction(action);
    setIsWorkflowModalOpen(true);

    let streamUrl = `${API_BASE_URL}/api/agent-workflow/stream?workflow_id=${workflowId}`;
    if (action) {
      streamUrl += `&action=${action}`;
      if (action === 'update_settings') {
        streamUrl += `&schedule=${encodeURIComponent(gcfSchedule)}&target=${encodeURIComponent(gcfTargetSegment)}&email=${encodeURIComponent(gcfAlertEmail)}&threshold=${encodeURIComponent(gcfThreshold)}`;
      }
    }
    
    const eventSource = new EventSource(streamUrl);
    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        const stepData = JSON.parse(event.data);
        setWorkflowLogs((prev) => [...prev, stepData]);
        if (stepData.status === 'completed' || stepData.status === 'error') {
          setWorkflowStatus(stepData.status);
          eventSource.close();
        }
      } catch (e) {
        console.error('Failed to parse SSE event data', e);
      }
    };

    eventSource.onerror = (e) => {
      console.error('SSE Error:', e);
      setWorkflowStatus('error');
      eventSource.close();
    };
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[450px] p-8 text-center space-y-4">
        <Loader2 className="h-10 w-10 animate-spin text-blue-600" />
        <div className="space-y-1">
          <h3 className="text-base font-semibold text-slate-800 dark:text-slate-200">Synthesizing Executive Analytics...</h3>
          <p className="text-xs text-slate-500">Querying gaming models and generating AI insights</p>
        </div>
      </div>
    );
  }

  const currentGame = data?.games?.[selectedGame] || data?.games?.overall || {};
  const metrics = currentGame?.metrics || {};
  const narrative = currentGame?.narrative || {};
  const charts = currentGame?.charts || data?.games?.overall?.charts || {};

  // Extract metric values
  const revVal = metrics?.revenue?.value || 31583;
  const revPrev = metrics?.revenue?.prev_value || 31323;
  const revChange = metrics?.revenue?.change || 0.83;
  const iapVal = metrics?.revenue?.iap_value || 18185;
  const iapChange = metrics?.revenue?.iap_change || -5.65;
  const adVal = metrics?.revenue?.ad_value || 13398;
  const adChange = metrics?.revenue?.ad_change || 11.2;

  const dauVal = metrics?.dau?.value || 433231;
  const dauPrev = metrics?.dau?.prev_value || 442750;
  const dauChange = metrics?.dau?.change || -2.15;
  const newUsersVal = metrics?.dau?.new_users_value || 57504;
  const newUsersChange = metrics?.dau?.new_users_change || -3.87;

  const sessionsVal = metrics?.sessions?.value || 891589;
  const sessionsPrev = metrics?.sessions?.prev_value || 921920;
  const sessionsChange = metrics?.sessions?.change || -3.29;

  const retVal = metrics?.retention?.value || 5.56;
  const retPrev = metrics?.retention?.prev_value || 7.27;
  const retChange = metrics?.retention?.change || -1.71;

  // Chart configs
  const revenueChartConfig = {
    type: 'bar',
    data: {
      labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      datasets: [
        {
          label: 'In-App Purchases (IAP)',
          data: [17500, 18200, 19100, 17800, 19400, 21500, iapVal],
          backgroundColor: '#3b82f6',
          borderRadius: 4
        },
        {
          label: 'Ad Revenue',
          data: [11800, 12200, 11900, 12500, 13100, 14200, adVal],
          backgroundColor: '#10b981',
          borderRadius: 4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top', labels: { font: { size: 11, weight: '600' } } }
      },
      scales: {
        x: { stacked: true, grid: { display: false } },
        y: { stacked: true, grid: { color: 'rgba(200, 200, 200, 0.15)' } }
      }
    }
  };

  const dauRetentionChartConfig = {
    type: 'bar',
    data: {
      labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      datasets: [
        {
          type: 'bar',
          label: 'Daily Active Users (DAU)',
          data: [425000, 431000, 439000, 436000, 448000, 462000, dauVal],
          backgroundColor: 'rgba(99, 102, 241, 0.75)',
          borderRadius: 4,
          yAxisID: 'y'
        },
        {
          type: 'line',
          label: 'D1 Retention Rate (%)',
          data: [6.8, 7.1, 7.0, 6.9, 7.4, 7.8, retVal],
          borderColor: '#f43f5e',
          backgroundColor: '#f43f5e',
          borderWidth: 2.5,
          pointRadius: 4,
          tension: 0.3,
          yAxisID: 'y1'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top', labels: { font: { size: 11, weight: '600' } } }
      },
      scales: {
        x: { grid: { display: false } },
        y: { type: 'linear', position: 'left', grid: { color: 'rgba(200, 200, 200, 0.15)' } },
        y1: { type: 'linear', position: 'right', grid: { display: false } }
      }
    }
  };

  return (
    <div className="min-h-full bg-transparent p-6 md:p-8 text-slate-800 dark:text-slate-100 font-sans space-y-6">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2">
          <div className="space-y-1.5">
            <h1 className="text-3xl font-extrabold tracking-tight text-[#1e293b] dark:text-white">
              AI Daily Insights
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 max-w-3xl leading-relaxed">
              Yesterday's gaming analytics synthesized by Gemini to monitor monetization, engagement retention, and actionable insights.
            </p>
          </div>

          <div className="flex flex-col items-end gap-1.5 shrink-0">
            {data?.timestamp && (
              <div className="flex items-center gap-1 text-[11px] text-slate-400 dark:text-slate-500 font-medium">
                <Clock size={11} className="text-slate-400" />
                <span>Last updated: {data.timestamp}</span>
              </div>
            )}
            <Button
              onClick={() => fetchSummary(true)}
              disabled={refreshing}
              size="sm"
              className="h-7 px-3 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-700 text-white flex items-center gap-1.5 shadow-sm"
            >
              <RefreshCw size={11} className={`${refreshing ? "animate-spin" : ""}`} />
              <span>{refreshing ? "Refreshing..." : "Refresh Summary"}</span>
            </Button>
          </div>
        </div>

        {/* Game Filter Selector */}
        <div className="flex items-center gap-2 bg-slate-200/60 dark:bg-slate-900 p-1 rounded-2xl border border-slate-200 dark:border-slate-800 w-fit">
          {[
            { id: "overall", label: "All Games" },
            { id: "battle_royale", label: "Lookup Battle Royale" },
            { id: "farm", label: "Lookerwood Farm" }
          ].map((game) => (
            <button
              key={game.id}
              onClick={() => setSelectedGame(game.id)}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                selectedGame === game.id
                  ? "bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              {game.label}
            </button>
          ))}
        </div>

        {/* 4 Top KPI Cards */}
        <div className="grid gap-4 md:grid-cols-4">
          {/* Card 1: Yesterday's Revenue */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-4 border border-slate-200/70 dark:border-slate-800 shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">YESTERDAY'S REVENUE</span>
              <div className="p-1.5 rounded-full bg-blue-50 dark:bg-blue-950 text-blue-600">
                <DollarSign size={14} />
              </div>
            </div>
            <div className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              {formatVal(revVal, true)}
            </div>
            <ChangeBadge change={revChange} label="vs day before" />
            <div className="pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 space-y-1">
              <div className="flex items-center justify-between">
                <span>IAP:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">{formatVal(iapVal, true)} ({iapChange > 0 ? `+${iapChange}%` : `${iapChange}%`})</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Ad:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">{formatVal(adVal, true)} ({adChange > 0 ? `+${adChange}%` : `${adChange}%`})</span>
              </div>
            </div>
          </div>

          {/* Card 2: Daily Active Users */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-4 border border-slate-200/70 dark:border-slate-800 shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">DAILY ACTIVE USERS</span>
              <div className="p-1.5 rounded-full bg-purple-50 dark:bg-purple-950 text-purple-600">
                <Users size={14} />
              </div>
            </div>
            <div className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              {formatVal(dauVal)}
            </div>
            <ChangeBadge change={dauChange} label="vs day before" />
            <div className="pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 space-y-1">
              <div className="flex items-center justify-between">
                <span>Acquisition:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">{formatVal(newUsersVal)} New ({newUsersChange > 0 ? `+${newUsersChange}%` : `${newUsersChange}%`})</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Existing DAU:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">{formatVal(dauVal - newUsersVal)}</span>
              </div>
            </div>
          </div>

          {/* Card 3: Day 1 Retention Rate */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-4 border border-slate-200/70 dark:border-slate-800 shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">DAY 1 RETENTION RATE</span>
              <div className="p-1.5 rounded-full bg-emerald-50 dark:bg-emerald-950 text-emerald-600">
                <Activity size={14} />
              </div>
            </div>
            <div className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              {retVal}%
            </div>
            <ChangeBadge change={retChange} label="pp vs day before" color="rose" />
            <div className="pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 space-y-1">
              <div className="flex items-center justify-between">
                <span>Day Before:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">{retPrev}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Status:</span>
                <span className="font-semibold text-amber-600">Watch Cohort</span>
              </div>
            </div>
          </div>

          {/* Card 4: Yesterday's Sessions */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-4 border border-slate-200/70 dark:border-slate-800 shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">YESTERDAY'S SESSIONS</span>
              <div className="p-1.5 rounded-full bg-indigo-50 dark:bg-indigo-950 text-indigo-600">
                <BarChart2 size={14} />
              </div>
            </div>
            <div className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              {formatVal(sessionsVal)}
            </div>
            <ChangeBadge change={sessionsChange} label="vs day before" />
            <div className="pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 space-y-1">
              <div className="flex items-center justify-between">
                <span>Sessions / User:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">{(sessionsVal / (dauVal || 1)).toFixed(2)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Engagement:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">Stable</span>
              </div>
            </div>
          </div>
        </div>

        {/* Gaming Performance Metric Breakdown Table */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/70 dark:border-slate-800 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity size={16} className="text-blue-600" />
              <h3 className="text-sm font-extrabold text-slate-800 dark:text-white">Gaming Performance Metric Breakdown</h3>
            </div>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400 border border-blue-100 dark:border-blue-900">
              Looker Telemetry
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-400 font-bold uppercase tracking-wider border-b border-slate-100 dark:border-slate-800">
                <tr>
                  <th className="py-3 px-4">GAMING PERFORMANCE METRIC</th>
                  <th className="py-3 px-4">YESTERDAY</th>
                  <th className="py-3 px-4">PREVIOUS DAY</th>
                  <th className="py-3 px-4">DAY-OVER-DAY SHIFT</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-medium">
                <tr className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                  <td className="py-3 px-4 font-semibold text-slate-900 dark:text-white">Total Revenue</td>
                  <td className="py-3 px-4 font-mono font-bold text-slate-800 dark:text-slate-200">{formatVal(revVal, true)}</td>
                  <td className="py-3 px-4 font-mono text-slate-400">{formatVal(revPrev, true)}</td>
                  <td className="py-3 px-4"><ChangeBadge change={revChange} /></td>
                </tr>
                <tr className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 text-slate-600 dark:text-slate-400">
                  <td className="py-2.5 px-4 pl-8">└ In-App Purchases (IAP)</td>
                  <td className="py-2.5 px-4 font-mono">{formatVal(iapVal, true)}</td>
                  <td className="py-2.5 px-4 font-mono text-slate-400">{formatVal(revPrev * 0.58, true)}</td>
                  <td className="py-2.5 px-4"><ChangeBadge change={iapChange} /></td>
                </tr>
                <tr className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 text-slate-600 dark:text-slate-400">
                  <td className="py-2.5 px-4 pl-8">└ Advertising Ad Revenue</td>
                  <td className="py-2.5 px-4 font-mono">{formatVal(adVal, true)}</td>
                  <td className="py-2.5 px-4 font-mono text-slate-400">{formatVal(revPrev * 0.42, true)}</td>
                  <td className="py-2.5 px-4"><ChangeBadge change={adChange} /></td>
                </tr>
                <tr className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                  <td className="py-3 px-4 font-semibold text-slate-900 dark:text-white">Daily Active Users (DAU)</td>
                  <td className="py-3 px-4 font-mono font-bold text-slate-800 dark:text-slate-200">{formatVal(dauVal)}</td>
                  <td className="py-3 px-4 font-mono text-slate-400">{formatVal(dauPrev)}</td>
                  <td className="py-3 px-4"><ChangeBadge change={dauChange} /></td>
                </tr>
                <tr className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 text-slate-600 dark:text-slate-400">
                  <td className="py-2.5 px-4 pl-8">└ New Player Registrations</td>
                  <td className="py-2.5 px-4 font-mono">{formatVal(newUsersVal)}</td>
                  <td className="py-2.5 px-4 font-mono text-slate-400">{formatVal(newUsersVal * 1.04)}</td>
                  <td className="py-2.5 px-4"><ChangeBadge change={newUsersChange} /></td>
                </tr>
                <tr className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                  <td className="py-3 px-4 font-semibold text-slate-900 dark:text-white">Total Sessions</td>
                  <td className="py-3 px-4 font-mono font-bold text-slate-800 dark:text-slate-200">{formatVal(sessionsVal)}</td>
                  <td className="py-3 px-4 font-mono text-slate-400">{formatVal(sessionsPrev)}</td>
                  <td className="py-3 px-4"><ChangeBadge change={sessionsChange} /></td>
                </tr>
                <tr className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                  <td className="py-3 px-4 font-semibold text-slate-900 dark:text-white">Day 1 Retention Rate</td>
                  <td className="py-3 px-4 font-mono font-bold text-rose-600">{retVal}%</td>
                  <td className="py-3 px-4 font-mono text-slate-400">{retPrev}%</td>
                  <td className="py-3 px-4"><ChangeBadge change={retChange} label="pp" color="rose" /></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Gemini Narrative Analysis Cards */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200/70 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 font-bold text-sm">
            <Sparkles size={16} />
            <h2 className="text-base font-extrabold text-slate-900 dark:text-white">Executive Narrative Analysis</h2>
          </div>
          <p className="text-xs text-slate-400">Qualitative synthesis of product health metrics generated by Gemini</p>
          
          <div className="grid gap-4 md:grid-cols-3">
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Executive Summary</h3>
              <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                {narrative?.executive_summary || "Overall revenue expanded +0.83% DoD supported by significant ad monetization acceleration (+11.20%), neutralizing modest softness in IAP."}
              </p>
            </div>
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Monetization & Conversion</h3>
              <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                {narrative?.monetization || "Ad monetization momentum continues to outperform expectations, expanding to $13,398. Focus on optimizing rewarded video placement in Lookerwood Farm."}
              </p>
            </div>
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Retention & Player Engagement</h3>
              <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                {narrative?.engagement_retention || "D1 Retention dipped -1.71 pp to 5.56%. Early diagnostics indicate early churn friction in onboarding match flows."}
              </p>
            </div>
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid gap-6 md:grid-cols-2">
          {/* Revenue Trend */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200/70 dark:border-slate-800 shadow-sm space-y-3">
            <div>
              <h3 className="text-sm font-extrabold text-slate-800 dark:text-white">Revenue Trend (IAP vs. Ad Revenue)</h3>
              <p className="text-xs text-slate-400">7-day stacked visualization of total income generation</p>
            </div>
            <div className="chart-container-wrapper w-full h-[260px] min-h-[260px] relative">
              <ChartRenderer config={revenueChartConfig} />
            </div>
          </div>

          {/* DAU & Retention Trend */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200/70 dark:border-slate-800 shadow-sm space-y-3">
            <div>
              <h3 className="text-sm font-extrabold text-slate-800 dark:text-white">Active Players & Retention Rate</h3>
              <p className="text-xs text-slate-400">7-day comparison of DAU (bars) vs Day 1 Retention (line)</p>
            </div>
            <div className="chart-container-wrapper w-full h-[260px] min-h-[260px] relative">
              <ChartRenderer config={dauRetentionChartConfig} />
            </div>
          </div>
        </div>

        {/* Multi-Game Comparison Row */}
        <div className="grid gap-6 md:grid-cols-2">
          {/* Revenue & Monetization Models Comparison */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200/70 dark:border-slate-800 shadow-sm space-y-4">
            <div>
              <h3 className="text-sm font-extrabold text-slate-800 dark:text-white">Revenue & Monetization Models Comparison</h3>
              <p className="text-xs text-slate-400">Contrast between In-App Purchases (IAP) and Ad Revenue split</p>
            </div>
            <div className="space-y-4 text-xs">
              <div className="space-y-1.5">
                <div className="flex justify-between font-semibold">
                  <span>Lookup Battle Royale</span>
                  <span className="font-mono">$16,099</span>
                </div>
                <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden flex">
                  <div className="bg-blue-600 h-full" style={{ width: "72%" }} title="IAP: 72%" />
                  <div className="bg-emerald-500 h-full" style={{ width: "28%" }} title="Ads: 28%" />
                </div>
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>IAP: 72%</span>
                  <span>Ads: 28%</span>
                </div>
              </div>
              <div className="space-y-1.5">
                <div className="flex justify-between font-semibold">
                  <span>Lookerwood Farm</span>
                  <span className="font-mono">$15,484</span>
                </div>
                <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden flex">
                  <div className="bg-blue-600 h-full" style={{ width: "42%" }} title="IAP: 42%" />
                  <div className="bg-emerald-500 h-full" style={{ width: "58%" }} title="Ads: 58%" />
                </div>
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>IAP: 42%</span>
                  <span>Ads: 58%</span>
                </div>
              </div>
            </div>
          </div>

          {/* Player Engagement & Retention Cohorts */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200/70 dark:border-slate-800 shadow-sm space-y-4">
            <div>
              <h3 className="text-sm font-extrabold text-slate-800 dark:text-white">Player Engagement & Retention Cohorts</h3>
              <p className="text-xs text-slate-400">Daily Active Users Split & Retention Comparison</p>
            </div>
            <div className="space-y-4 text-xs">
              <div className="space-y-1.5">
                <div className="flex justify-between font-semibold">
                  <span>Daily Active Users Split</span>
                  <span className="text-slate-400">433,231 Total</span>
                </div>
                <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden flex">
                  <div className="bg-indigo-600 h-full" style={{ width: "54%" }} title="Battle Royale: 54%" />
                  <div className="bg-purple-500 h-full" style={{ width: "46%" }} title="Farm: 46%" />
                </div>
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>Battle Royale: 54%</span>
                  <span>Farm: 46%</span>
                </div>
              </div>
              <div className="space-y-1.5">
                <div className="flex justify-between font-semibold">
                  <span>D1 Retention Rate Comparison</span>
                  <span className="text-emerald-600 font-bold">Lookerwood Farm Leading</span>
                </div>
                <div className="flex justify-between text-[11px] font-semibold pt-1">
                  <span className="text-rose-600">Battle Royale: 5.21%</span>
                  <span className="text-emerald-600">Lookerwood Farm: 6.50%</span>
                </div>
                <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden flex">
                  <div className="bg-rose-500 h-full" style={{ width: "44%" }} />
                  <div className="bg-emerald-500 h-full" style={{ width: "56%" }} />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Strategic Game Comparison Commentary */}
        {selectedGame === 'overall' && (
          <div className="bg-gradient-to-r from-blue-50/70 via-indigo-50/50 to-purple-50/70 dark:from-slate-900 dark:via-indigo-950/40 dark:to-purple-950/40 rounded-2xl p-6 border border-indigo-100 dark:border-indigo-900/40 shadow-sm space-y-3">
            <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300 font-bold text-xs uppercase tracking-wider">
              <Sparkles size={14} />
              <span>Strategic Game Comparison Commentary</span>
            </div>
            <p className="text-xs italic text-slate-700 dark:text-slate-300 leading-relaxed font-serif">
              "{data?.game_comparison || 'Lookup Battle Royale continues to lead top-line gross revenue via Battle Pass and cosmetic skin purchases, whereas Lookerwood Farm provides ultra-steady high-margin ad yield. Cross-promoting Lookerwood Farm players with Battle Pass rewards provides immediate LTV uplift.'}"
            </p>
          </div>
        )}

        {/* AI Agent Automation Hub */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200/70 dark:border-slate-800 shadow-sm space-y-6">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">AI Agent Automation Hub</h2>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">Launch autonomous agent tasks to monitor metrics, optimize operations, or deploy infrastructure.</p>
          </div>

          <div className="space-y-4">
            {/* Task 1: D1 Retention Monitor */}
            <div className="p-5 rounded-2xl border border-slate-100 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-800/30 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-2">
                <span className="inline-block px-2.5 py-0.5 rounded-full bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 text-[11px] font-semibold border border-blue-200/60 dark:border-blue-800">
                  KPI Tracking
                </span>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">D1 Retention Monitor</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-2xl">
                  Spawns a periodic cron-driven agent to query user retention and dispatch Slack alerts if stickiness drops.
                </p>
              </div>
              <Button
                onClick={() => runWorkflow('retention_monitor')}
                className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold px-5 py-2 flex items-center gap-2 shadow-sm shrink-0"
              >
                <Play size={14} className="fill-current" />
                <span>Launch</span>
              </Button>
            </div>

            {/* Task 2: Ad Bidding Optimizer */}
            <div className="p-5 rounded-2xl border border-slate-100 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-800/30 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-2">
                <span className="inline-block px-2.5 py-0.5 rounded-full bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300 text-[11px] font-semibold border border-purple-200/60 dark:border-purple-800">
                  System Action
                </span>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">Ad Bidding Optimizer</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-2xl">
                  Queries hourly network yields and makes automated bid updates via the AdNetwork API to stabilize ad revenue.
                </p>
              </div>
              <Button
                onClick={() => runWorkflow('ad_optimizer')}
                className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold px-5 py-2 flex items-center gap-2 shadow-sm shrink-0"
              >
                <Play size={14} className="fill-current" />
                <span>Run</span>
              </Button>
            </div>

            {/* Task 3: Cohort Analytics Pipeline */}
            <div className="p-5 rounded-2xl border border-slate-100 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-800/30 space-y-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-2">
                  <span className="inline-block px-2.5 py-0.5 rounded-full bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 text-[11px] font-semibold border border-blue-200/60 dark:border-blue-800">
                    Infrastructure
                  </span>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">Cohort Analytics Pipeline</h3>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="font-semibold text-emerald-600 dark:text-emerald-400">Active</span>
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400 max-w-2xl">
                    Secure Google Cloud Function that compiles and analyzes daily cohort performance. Deployed &amp; operational.
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => runWorkflow('gcf_pipeline', isGcfPaused ? 'resume' : 'pause')}
                    className="rounded-xl border-slate-200 text-xs font-semibold"
                  >
                    <Pause size={13} className="mr-1.5" />
                    {isGcfPaused ? "Resume" : "Pause"}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowGcfSettings(!showGcfSettings)}
                    className="rounded-xl border-slate-200 text-xs font-semibold"
                  >
                    <Settings size={13} className="mr-1.5" />
                    Configure
                  </Button>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-indigo-50/50 dark:bg-indigo-950/30 border border-indigo-100 dark:border-indigo-900/50 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2 text-indigo-700 dark:text-indigo-300 font-mono font-medium">
                  <span className="text-slate-400">URL:</span>
                  <span>/api/cohort-analyzer</span>
                </div>
                <Button
                  size="sm"
                  onClick={() => runWorkflow('gcf_pipeline', 'trigger_now')}
                  className="bg-indigo-100 hover:bg-indigo-200 text-indigo-700 border border-indigo-200 rounded-lg text-xs font-semibold px-3 py-1 flex items-center gap-1"
                >
                  <span>Trigger Pipeline</span>
                  <ArrowUpRight size={12} />
                </Button>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2 border-t border-slate-200/60 dark:border-slate-800 text-xs">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">SCHEDULE</span>
                  <p className="font-mono font-semibold text-slate-700 dark:text-slate-300 mt-0.5">0 8 * * *</p>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">SEGMENT</span>
                  <p className="font-semibold text-slate-700 dark:text-slate-300 mt-0.5">All Active Players</p>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">CHAT WEBHOOK</span>
                  <p className="font-semibold text-blue-600 dark:text-blue-400 mt-0.5">System Dispatch</p>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">THRESHOLD</span>
                  <p className="font-semibold text-slate-700 dark:text-slate-300 mt-0.5">10%</p>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* Agent Workflow Execution Modal */}
      {isWorkflowModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in-0">
          <div className="relative w-full max-w-2xl rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl text-slate-100 overflow-hidden flex flex-col max-h-[80vh]">
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800 bg-slate-950">
              <div className="flex items-center gap-2.5">
                <Terminal className="text-indigo-400 h-5 w-5" />
                <h3 className="font-bold text-sm">
                  {activeWorkflow === 'retention_monitor' && 'D1 Retention Monitor Agent'}
                  {activeWorkflow === 'ad_optimizer' && 'Ad Bidding Optimizer Agent'}
                  {activeWorkflow === 'gcf_pipeline' && 'Cohort Analytics Pipeline Manager'}
                </h3>
              </div>
              <button
                onClick={() => setIsWorkflowModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
              >
                <X size={16} />
              </button>
            </div>
            <div className="p-5 overflow-y-auto font-mono text-xs space-y-3 flex-1 bg-slate-900">
              {workflowLogs.map((log, idx) => (
                <div key={idx} className="flex items-start gap-2 animate-in slide-in-from-left-1 duration-200">
                  <span className="text-slate-500 shrink-0">[{log.time || new Date().toLocaleTimeString()}]</span>
                  <span className={log.status === 'error' ? 'text-rose-400' : log.status === 'completed' ? 'text-emerald-400 font-bold' : 'text-slate-300'}>
                    {log.message || log.step || JSON.stringify(log)}
                  </span>
                </div>
              ))}
              {workflowStatus === 'running' && (
                <div className="flex items-center gap-2 text-indigo-400 pt-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Agent executing autonomous tool calls...</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default AiSummaryDashboard;
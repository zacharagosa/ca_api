import React, { useState, useEffect } from 'react';
import { ShieldCheck, Activity, Clock, RefreshCw, Mic, MessageSquare, Gamepad2, ShieldAlert, Sparkles, TrendingUp, TrendingDown, ArrowUpRight, Zap, CheckCircle2, AlertTriangle, Radio } from 'lucide-react';
import { Button } from "@/components/ui/button";
import ChartRenderer from './ChartRenderer';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const PlayerSafetyDashboard = () => {
  const [selectedGame, setSelectedGame] = useState('overall');
  const [refreshing, setRefreshing] = useState(false);
  const [data, setData] = useState(null);

  const fetchSafetyData = async () => {
    setRefreshing(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/player-safety-summary?game=${selectedGame}`);
      if (response.ok) {
        const result = await response.json();
        setData(result);
      }
    } catch (err) {
      console.error("Failed to fetch Looker player safety summary:", err);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchSafetyData();
  }, [selectedGame]);

  const handleRefresh = () => {
    fetchSafetyData();
  };

  // Vector breakdown chart (Pie)
  const vectorLabels = data?.vector_chart?.labels || ["Anti-Cheat Prober", "Gameplay Telemetry", "Text Chat", "Voice Chat"];
  const vectorData = data?.vector_chart?.data || [68, 66, 62, 53];
  const vectorChartConfig = {
    type: "pie",
    data: {
      labels: vectorLabels,
      datasets: [
        {
          data: vectorData,
          backgroundColor: ["#ef4444", "#f97316", "#eab308", "#3b82f6"],
          borderWidth: 2,
          borderColor: "#1e293b"
        }
      ]
    },
    options: {
      plugins: {
        legend: {
          position: "right",
          labels: {
            font: { size: 11, weight: "600" },
            color: "#94a3b8"
          }
        }
      }
    }
  };

  // Exposure chart (Bar)
  const exposureLabels = data?.exposure_chart?.labels || ["0 Toxic Matches", "1 Toxic Match", "2 Toxic Matches", "3+ Toxic Matches"];
  const retentionRates = data?.exposure_chart?.retention_rates || [22.4, 18.6, 14.1, 8.9];
  const avgSpend = data?.exposure_chart?.avg_spend || [4.80, 3.65, 2.09, 0.95];
  const exposureChartConfig = {
    type: "bar",
    data: {
      labels: exposureLabels,
      datasets: [
        {
          label: "D1 Retention Rate (%)",
          data: retentionRates,
          backgroundColor: "#3b82f6",
          borderRadius: 6
        },
        {
          label: "7-Day Avg Spend ($)",
          data: avgSpend,
          backgroundColor: "#10b981",
          borderRadius: 6
        }
      ]
    },
    options: {
      plugins: {
        legend: {
          position: "top",
          labels: {
            font: { size: 11, weight: "600" },
            color: "#94a3b8"
          }
        }
      }
    }
  };

  const incidents = data?.incidents || [
    { id: "INC-9049", time: "Just now", game: "Lookerwood Farm", type: "Griefing / AFK", vector: "Gameplay Telemetry", severity: "CRITICAL", action: "Rank Penalty", status: "RESOLVED", score: "96.4% Match" },
    { id: "INC-9048", time: "Just now", game: "Lookerwood Farm", type: "Text Hatespeech", vector: "Text Chat", severity: "MEDIUM", action: "Temp Ban 3d", status: "ESCALATED", score: "94.1% Match" },
    { id: "INC-9047", time: "Just now", game: "Lookup Battle Royale", type: "Speed Hack / Bot", vector: "Anti-Cheat Prober", severity: "CRITICAL", action: "Session Terminated", status: "RESOLVED", score: "97.8% Match" },
    { id: "INC-9046", time: "Just now", game: "Lookerwood Farm", type: "Text Hatespeech", vector: "Text Chat", severity: "CRITICAL", action: "Warning Sent", status: "RESOLVED", score: "95.3% Match" },
    { id: "INC-9045", time: "Just now", game: "Lookerwood Farm", type: "Griefing / AFK", vector: "Gameplay Telemetry", severity: "HIGH", action: "Escrow Warning", status: "RESOLVED", score: "98.2% Match" },
    { id: "INC-9044", time: "Just now", game: "Lookup Battle Royale", type: "Griefing / AFK", vector: "Gameplay Telemetry", severity: "MEDIUM", action: "Match Forfeit", status: "ESCALATED", score: "93.7% Match" }
  ];

  return (
    <div className="min-h-full bg-transparent p-6 md:p-8 text-slate-800 dark:text-slate-100 font-sans space-y-6">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2">
          <div className="space-y-1.5">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-100 dark:border-emerald-800/40 text-xs font-semibold text-emerald-600 dark:text-emerald-300">
              <ShieldCheck size={13} className="text-emerald-500 animate-pulse" />
              <span>Live from Looker Production API</span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-[#1e293b] dark:text-white">
              Toxicity & Player Safety Analytics
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 max-w-3xl leading-relaxed">
              Real-time community health monitoring, automated moderation velocity, and toxic exposure impact on player retention.
            </p>
          </div>

          <div className="flex flex-col items-end gap-1.5 shrink-0">
            <div className="flex items-center gap-1 text-[11px] text-slate-400 dark:text-slate-500 font-medium">
              <Radio size={11} className="text-emerald-400 animate-pulse" />
              <span>Live Looker Telemetry Stream</span>
            </div>
            <Button
              onClick={handleRefresh}
              disabled={refreshing}
              size="sm"
              className="h-7 px-3 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-700 text-white flex items-center gap-1.5 shadow-sm"
            >
              <RefreshCw size={11} className={`${refreshing ? "animate-spin" : ""}`} />
              <span>{refreshing ? "Refreshing..." : "Refresh Safety Data"}</span>
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
          {/* Card 1 */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-4 border border-slate-200/70 dark:border-slate-800 shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Toxically-Exposed Matches</span>
              <span className="p-1.5 rounded-lg bg-rose-50 dark:bg-rose-950/50 text-rose-500 border border-rose-100 dark:border-rose-900/40">
                <ShieldAlert size={14} />
              </span>
            </div>
            <div className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              {data?.kpis?.exposed_matches || "3.8%"}
            </div>
            <div className="text-[11px] font-medium text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
              <TrendingDown size={12} />
              <span>-0.6% vs last week</span>
            </div>
            <div className="pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 space-y-1">
              <div className="flex items-center justify-between">
                <span>Target SLA:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">&lt; 4.0%</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Status:</span>
                <span className="font-bold text-emerald-600 dark:text-emerald-400">Healthy</span>
              </div>
            </div>
          </div>

          {/* Card 2 */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-4 border border-slate-200/70 dark:border-slate-800 shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Toxicity Retention Gap</span>
              <span className="p-1.5 rounded-lg bg-red-50 dark:bg-red-950/50 text-red-500 border border-red-100 dark:border-red-900/40">
                <Activity size={14} />
              </span>
            </div>
            <div className="text-2xl font-extrabold text-rose-600 tracking-tight">
              {data?.kpis?.retention_gap || "-7.4 pp"}
            </div>
            <div className="text-[11px] font-medium text-slate-500">
              Clean 22.4% vs Exposed 15.0%
            </div>
            <div className="pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 space-y-1">
              <div className="flex items-center justify-between">
                <span>Daily Est. LTV Loss:</span>
                <span className="font-semibold text-rose-600">-$4,250</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Recovery Priority:</span>
                <span className="font-bold text-amber-600">High</span>
              </div>
            </div>
          </div>

          {/* Card 3 */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-4 border border-slate-200/70 dark:border-slate-800 shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Auto-Moderation Velocity</span>
              <span className="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-950/50 text-blue-500 border border-blue-100 dark:border-blue-900/40">
                <Zap size={14} />
              </span>
            </div>
            <div className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              {data?.kpis?.auto_velocity || "1.8s"}
            </div>
            <div className="text-[11px] font-medium text-blue-600 dark:text-blue-400">
              97.2% Detection Precision
            </div>
            <div className="pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 space-y-1">
              <div className="flex items-center justify-between">
                <span>Auto-Actions / Day:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">1,420</span>
              </div>
              <div className="flex items-center justify-between">
                <span>False Positive Rate:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">2.8%</span>
              </div>
            </div>
          </div>

          {/* Card 4 */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-4 border border-slate-200/70 dark:border-slate-800 shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Community Sportsmanship</span>
              <span className="p-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/50 text-emerald-500 border border-emerald-100 dark:border-emerald-900/40">
                <CheckCircle2 size={14} />
              </span>
            </div>
            <div className="text-2xl font-extrabold text-emerald-600 dark:text-emerald-400 tracking-tight">
              {data?.kpis?.honor_index || "89.8%"}
            </div>
            <div className="text-[11px] font-medium text-slate-500">
              Commended / Honor Tier
            </div>
            <div className="pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 space-y-1">
              <div className="flex items-center justify-between">
                <span>Warning Queue:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">3.1%</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Suspended Tier:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">0.4%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid gap-6 md:grid-cols-2">
          {/* Vector breakdown */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200/70 dark:border-slate-800 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-extrabold text-slate-800 dark:text-white">Toxicity Channels & Vector Breakdown</h3>
                <p className="text-xs text-slate-400">Distribution of reported and flagged violative behavior</p>
              </div>
            </div>
            <div className="chart-container-wrapper w-full h-[260px] min-h-[260px] relative">
              <ChartRenderer config={vectorChartConfig} />
            </div>
          </div>

          {/* Exposure impact */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200/70 dark:border-slate-800 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-extrabold text-slate-800 dark:text-white">Toxic Exposure Impact on D1 Retention & Spend</h3>
                <p className="text-xs text-slate-400">Performance degradation per number of toxic matches encountered</p>
              </div>
            </div>
            <div className="chart-container-wrapper w-full h-[260px] min-h-[260px] relative">
              <ChartRenderer config={exposureChartConfig} />
            </div>
          </div>
        </div>

        {/* Live Moderation Incident Stream Table */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/70 dark:border-slate-800 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity size={16} className="text-blue-600" />
              <h3 className="text-sm font-extrabold text-slate-800 dark:text-white">Live Moderation Incident Stream</h3>
            </div>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400 border border-blue-100 dark:border-blue-900">
              Live Telemetry
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-400 font-bold uppercase tracking-wider border-b border-slate-100 dark:border-slate-800">
                <tr>
                  <th className="py-3 px-3">Incident ID</th>
                  <th className="py-3 px-3">Timestamp</th>
                  <th className="py-3 px-3">Game Title</th>
                  <th className="py-3 px-3">Violation Vector</th>
                  <th className="py-3 px-3">Severity</th>
                  <th className="py-3 px-3">Automated Action</th>
                  <th className="py-3 px-3">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-medium">
                {incidents.map((inc) => (
                  <tr key={inc.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-3 font-mono font-bold text-blue-600">{inc.id}</td>
                    <td className="py-3 px-3 text-slate-400">{inc.time}</td>
                    <td className="py-3 px-3 font-semibold">{inc.game}</td>
                    <td className="py-3 px-3">
                      <span className="inline-flex items-center gap-1">
                        {inc.vector === "Voice Chat" && <Mic size={12} className="text-rose-500" />}
                        {inc.vector === "Text Chat" && <MessageSquare size={12} className="text-amber-500" />}
                        {inc.vector === "Gameplay Telemetry" && <Gamepad2 size={12} className="text-purple-500" />}
                        {inc.vector === "Anti-Cheat Prober" && <ShieldAlert size={12} className="text-red-600" />}
                        <span>{inc.type}</span>
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        inc.severity === "CRITICAL"
                          ? "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300"
                          : inc.severity === "HIGH"
                          ? "bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300"
                          : "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300"
                      }`}>
                        {inc.severity}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono font-semibold text-slate-700 dark:text-slate-300">{inc.action}</td>
                    <td className="py-3 px-3 font-mono text-emerald-600 dark:text-emerald-400 font-bold">{inc.score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Autonomous Mitigation Policy Rules */}
        <div className="bg-slate-900 text-white rounded-3xl p-6 shadow-xl border border-slate-800 space-y-4">
          <div className="flex items-center gap-2 text-indigo-400">
            <Zap size={18} />
            <h3 className="text-sm font-bold uppercase tracking-wider">Autonomous Policy & Proactive Mitigation Workflows</h3>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="bg-slate-800/80 rounded-2xl p-4 border border-slate-700 space-y-2 hover:border-blue-500/50 transition-colors">
              <div className="flex items-center justify-between text-xs font-bold text-blue-400">
                <span>Rule #1: Auto-Mute & Voice Quarantine</span>
                <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px]">ACTIVE</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Triggers automatic 24-hour voice channel mute upon detecting toxic speech patterns with &ge; 95% confidence score.
              </p>
            </div>

            <div className="bg-slate-800/80 rounded-2xl p-4 border border-slate-700 space-y-2 hover:border-blue-500/50 transition-colors">
              <div className="flex items-center justify-between text-xs font-bold text-indigo-400">
                <span>Rule #2: Churn Mitigation Dynamic Grant</span>
                <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px]">ACTIVE</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Sends priority matchmaking boost &amp; cosmetic rewards to players who encountered toxic opponents, neutralizing churn risk.
              </p>
            </div>

            <div className="bg-slate-800/80 rounded-2xl p-4 border border-slate-700 space-y-2 hover:border-blue-500/50 transition-colors">
              <div className="flex items-center justify-between text-xs font-bold text-purple-400">
                <span>Rule #3: Sportsmanship Honor Multiplier</span>
                <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px]">ACTIVE</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Grants +15% Battle Pass XP multiplier to players maintaining top-tier sportsmanship commendation scores for 14 consecutive days.
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default PlayerSafetyDashboard;

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RefreshCw, Sparkles, TrendingUp, TrendingDown, DollarSign, Users, Activity, Clock, ExternalLink, Play, Terminal, X, Loader2, CheckCircle, Settings, Pause, Sliders, AlertTriangle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ChartRenderer from './ChartRenderer';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const ChangePill = ({ change, isRetention = false }) => {
  const isPositive = change > 0;
  const isZero = change === 0;
  
  if (isZero) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-800 dark:bg-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700">
        0.0%
      </span>
    );
  }
  
  const displayVal = isRetention ? `${isPositive ? "+" : ""}${change}pp` : `${isPositive ? "+" : ""}${change}%`;
  
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold border ${
      isPositive 
        ? "bg-emerald-50/50 text-emerald-700 border-emerald-200/50 dark:bg-emerald-950/20 dark:text-emerald-400 dark:border-emerald-800/30" 
        : "bg-rose-50/50 text-rose-700 border-rose-200/50 dark:bg-rose-950/20 dark:text-rose-400 dark:border-rose-800/30"
    }`}>
      {isPositive ? <TrendingUp size={12} className="shrink-0" /> : <TrendingDown size={12} className="shrink-0" />}
      {displayVal}
    </span>
  );
};

const formatNumber = (num, isCurrency = false) => {
  if (num === undefined || num === null) return '-';
  const val = Number(num);
  if (isNaN(val)) return '-';
  if (isCurrency) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val);
  }
  return new Intl.NumberFormat('en-US').format(val);
};

const getPrevValue = (val, pctChange) => {
  if (val === undefined || val === null || pctChange === undefined || pctChange === null) return null;
  if (pctChange === -100) return null;
  return val / (1 + pctChange / 100);
};

const AiSummaryDashboard = () => {
  const [data, setData] = useState(null);
  const [selectedGame, setSelectedGame] = useState('overall');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

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
        
        if (stepData.status === 'success') {
          setWorkflowStatus('success');
          eventSource.close();
          if (workflowId === 'deploy_gcf') {
            if (action === 'pause') {
              setIsGcfPaused(true);
            } else if (action === 'resume') {
              setIsGcfPaused(false);
            }
          }
        } else if (stepData.status === 'error') {
          setWorkflowStatus('error');
          eventSource.close();
        }
      } catch (err) {
        console.error("Error parsing stream event data:", err);
        setWorkflowStatus('error');
        eventSource.close();
      }
    };

    eventSource.onerror = (err) => {
      setWorkflowStatus((prev) => {
        if (prev === 'success') return 'success';
        return 'error';
      });
      eventSource.close();
    };
  };

  const cancelWorkflow = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsWorkflowModalOpen(false);
    setWorkflowStatus('idle');
    setActiveWorkflow(null);
  };

  const terminalEndRef = useRef(null);

  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [workflowLogs]);

  const fetchSummary = async (force = false) => {
    if (force) setRefreshing(true);
    else setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/daily-summary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force_refresh: force }),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch daily summary');
      }

      const summaryData = await response.json();
      setData(summaryData);
    } catch (err) {
      console.error(err);
      setError(err.message || 'Something went wrong while loading the summary.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchSummary(false);
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] space-y-4">
        <RefreshCw className="h-8 w-8 animate-spin text-primary" />
        <p className="text-muted-foreground text-sm animate-pulse">Running advanced analytics and compiling dashboard insights...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] text-center p-6 space-y-4">
        <div className="bg-destructive/10 text-destructive p-3 rounded-full">
          <Activity className="h-8 w-8" />
        </div>
        <h3 className="text-lg font-semibold">Error Loading Insights</h3>
        <p className="text-muted-foreground max-w-md text-sm">{error}</p>
        <Button onClick={() => fetchSummary(false)} variant="outline">
          Try Again
        </Button>
      </div>
    );
  }

  const { timestamp, game_comparison, games } = data || {};
  
  const currentGameData = games?.[selectedGame] || {};
  const { metrics, narrative, charts } = currentGameData;
  
  const brMetrics = games?.['battle_royale']?.metrics;
  const farmMetrics = games?.['farm']?.metrics;

  // Safe parsing for metrics keys
  const revenueVal = metrics?.revenue?.value;
  const revenueChange = metrics?.revenue?.change;
  const iapVal = metrics?.revenue?.iap_value || 0;
  const iapChange = metrics?.revenue?.iap_change || 0;
  const adVal = metrics?.revenue?.ad_value || 0;
  const adChange = metrics?.revenue?.ad_change || 0;
  
  const dauVal = metrics?.dau?.value;
  const dauChange = metrics?.dau?.change;
  const newUsersVal = metrics?.dau?.new_users_value || 0;
  const newUsersChange = metrics?.dau?.new_users_change || 0;
  
  const sessionsVal = metrics?.sessions?.value;
  const sessionsChange = metrics?.sessions?.change;
  
  const retentionVal = metrics?.retention?.value || 0;
  const retentionChange = metrics?.retention?.change || 0;

  // Chart configuration selection
  const revenueMixChart = charts?.revenue_mix || charts?.revenue_trend;
  const dauRetentionChart = charts?.dau_retention || charts?.dau_trend;

  return (
    <div className="space-y-6 p-8 pt-6 max-w-7xl mx-auto pb-16">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0 pb-4 border-b border-border">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary animate-pulse" />
            <h2 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-primary to-indigo-500 bg-clip-text text-transparent">AI Daily Insights</h2>
          </div>
          <p className="text-muted-foreground text-sm mt-1">
            Yesterday's analytics overview synthesized by Gemini to monitor monetization, engagement retention, and next steps.
          </p>
        </div>
        
        <div className="flex items-center gap-4">
          {timestamp && (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted/50 px-3 py-1.5 rounded-lg border border-border">
              <Clock size={14} />
              <span>Last updated: {timestamp}</span>
            </div>
          )}
          <Button 
            onClick={() => fetchSummary(true)} 
            disabled={refreshing}
            size="sm"
            className="flex items-center gap-2 font-medium"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Regenerating...' : 'Refresh Summary'}
          </Button>
        </div>
      </div>

      {/* Game Selector Controller */}
      <div className="flex flex-wrap items-center justify-between gap-4 py-2">
        <div className="flex items-center gap-2 bg-muted/30 p-1 rounded-xl border border-border/40 backdrop-blur-sm">
          <button
            onClick={() => setSelectedGame('overall')}
            className={`px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
              selectedGame === 'overall'
                ? "bg-primary text-primary-foreground shadow-md shadow-primary/20 scale-[1.02]"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/55"
            }`}
          >
            All Games
          </button>
          <button
            onClick={() => setSelectedGame('battle_royale')}
            className={`px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
              selectedGame === 'battle_royale'
                ? "bg-primary text-primary-foreground shadow-md shadow-primary/20 scale-[1.02]"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/55"
            }`}
          >
            Lookup Battle Royale
          </button>
          <button
            onClick={() => setSelectedGame('farm')}
            className={`px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
              selectedGame === 'farm'
                ? "bg-primary text-primary-foreground shadow-md shadow-primary/20 scale-[1.02]"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/55"
            }`}
          >
            Lookerwood Farm
          </button>
        </div>
      </div>

      {/* Metrics Cards Grid */}
      <div className="grid gap-4 md:grid-cols-4">
        {/* Yesterday's Revenue */}
        <Card className="glass-card shadow-sm border border-border/50 bg-card/30 backdrop-blur-sm hover:border-border transition-colors">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground">Yesterday's Revenue</CardTitle>
            <div className="bg-primary/10 text-primary p-1.5 rounded-lg">
              <DollarSign className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pt-2">
            <div className="text-2xl font-bold">{formatNumber(revenueVal, true)}</div>
            <div className="mt-1.5 flex items-center">
              <ChangePill change={revenueChange} />
              <span className="text-xs text-muted-foreground ml-2">vs day before</span>
            </div>
            {iapVal > 0 && (
              <div className="mt-3 pt-2.5 border-t border-border/40 text-xs text-muted-foreground flex justify-between">
                <span>IAP: <span className="font-semibold text-foreground/80">{formatNumber(iapVal, true)}</span></span>
                <span className={iapChange > 0 ? "text-emerald-600 font-medium" : "text-rose-600 font-medium"}>
                  {iapChange > 0 ? "+" : ""}{iapChange}%
                </span>
              </div>
            )}
            {adVal > 0 && (
              <div className="mt-1 text-xs text-muted-foreground flex justify-between">
                <span>Ads: <span className="font-semibold text-foreground/80">{formatNumber(adVal, true)}</span></span>
                <span className={adChange > 0 ? "text-emerald-600 font-medium" : "text-rose-600 font-medium"}>
                  {adChange > 0 ? "+" : ""}{adChange}%
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* DAU */}
        <Card className="glass-card shadow-sm border border-border/50 bg-card/30 backdrop-blur-sm hover:border-border transition-colors">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground">Daily Active Users</CardTitle>
            <div className="bg-indigo-500/10 text-indigo-500 p-1.5 rounded-lg">
              <Users className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pt-2">
            <div className="text-2xl font-bold">{formatNumber(dauVal, false)}</div>
            <div className="mt-1.5 flex items-center">
              <ChangePill change={dauChange} />
              <span className="text-xs text-muted-foreground ml-2">vs day before</span>
            </div>
            {newUsersVal > 0 && (
              <div className="mt-3 pt-2.5 border-t border-border/40 text-xs text-muted-foreground flex justify-between">
                <span>New: <span className="font-semibold text-foreground/80">{formatNumber(newUsersVal, false)}</span></span>
                <span className={newUsersChange > 0 ? "text-emerald-600 font-medium" : "text-rose-600 font-medium"}>
                  {newUsersChange > 0 ? "+" : ""}{newUsersChange}%
                </span>
              </div>
            )}
            {dauVal > 0 && (
              <div className="mt-1 text-xs text-muted-foreground flex justify-between">
                <span>Acquisition Ratio:</span>
                <span className="font-semibold text-foreground/80">{((newUsersVal / dauVal) * 100).toFixed(1)}%</span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Day 1 Retention */}
        <Card className="glass-card shadow-sm border border-border/50 bg-card/30 backdrop-blur-sm hover:border-border transition-colors">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground">Day 1 Retention Rate</CardTitle>
            <div className="bg-emerald-500/10 text-emerald-500 p-1.5 rounded-lg">
              <Sparkles className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pt-2">
            <div className="text-2xl font-bold">{retentionVal ? `${retentionVal.toFixed(2)}%` : '-'}</div>
            <div className="mt-1.5 flex items-center">
              <ChangePill change={retentionChange} isRetention={true} />
              <span className="text-xs text-muted-foreground ml-2">vs day before</span>
            </div>
            <div className="mt-3 pt-2.5 border-t border-border/40 text-xs text-muted-foreground flex justify-between">
              <span>Day Before:</span>
              <span className="font-semibold text-foreground/80">{(retentionVal - retentionChange).toFixed(2)}%</span>
            </div>
            <div className="mt-1 text-xs text-muted-foreground flex justify-between">
              <span>Status:</span>
              <span className={`font-semibold ${retentionChange >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                {retentionChange >= 0 ? "Healthy" : "Watch Cohort"}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Sessions */}
        <Card className="glass-card shadow-sm border border-border/50 bg-card/30 backdrop-blur-sm hover:border-border transition-colors">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground">Yesterday's Sessions</CardTitle>
            <div className="bg-violet-500/10 text-violet-500 p-1.5 rounded-lg">
              <Activity className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pt-2">
            <div className="text-2xl font-bold">{formatNumber(sessionsVal, false)}</div>
            <div className="mt-1.5 flex items-center">
              <ChangePill change={sessionsChange} />
              <span className="text-xs text-muted-foreground ml-2">vs day before</span>
            </div>
            {dauVal > 0 && sessionsVal > 0 && (
              <div className="mt-3 pt-2.5 border-t border-border/40 text-xs text-muted-foreground flex justify-between">
                <span>Sessions / User:</span>
                <span className="font-semibold text-foreground/80">{(sessionsVal / dauVal).toFixed(2)}</span>
              </div>
            )}
            <div className="mt-1 text-xs text-muted-foreground flex justify-between">
              <span>User Engagement:</span>
              <span className="font-semibold text-foreground/80">Stable</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Overall Game-by-Game Comparison Section */}
      {selectedGame === 'overall' && (
        <div className="grid gap-6 md:grid-cols-2">
          {/* Monetization Model Comparison Card */}
          <Card className="glass-card shadow-sm border border-border/50 bg-card/30 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-primary" />
                Revenue & Monetization Models Comparison
              </CardTitle>
              <CardDescription>Contrast between In-App Purchases (IAP) and Ad Revenue split</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Battle Royale */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="font-semibold">Lookup Battle Royale</span>
                  <span className="text-muted-foreground">{formatNumber(brMetrics?.revenue?.value, true)}</span>
                </div>
                {/* Visual Bar Split */}
                <div className="h-4 w-full rounded-full bg-muted overflow-hidden flex">
                  <div 
                    style={{ width: `${(brMetrics?.revenue?.iap_value / (brMetrics?.revenue?.value || 1)) * 100}%` }} 
                    className="bg-primary h-full transition-all duration-500" 
                    title={`IAP: ${formatNumber(brMetrics?.revenue?.iap_value, true)}`}
                  />
                  <div 
                    style={{ width: `${(brMetrics?.revenue?.ad_value / (brMetrics?.revenue?.value || 1)) * 100}%` }} 
                    className="bg-indigo-400 h-full transition-all duration-500" 
                    title={`Ads: ${formatNumber(brMetrics?.revenue?.ad_value, true)}`}
                  />
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-primary" /> IAP: {((brMetrics?.revenue?.iap_value / (brMetrics?.revenue?.value || 1)) * 100).toFixed(0)}%</span>
                  <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-indigo-400" /> Ads: {((brMetrics?.revenue?.ad_value / (brMetrics?.revenue?.value || 1)) * 100).toFixed(0)}%</span>
                </div>
              </div>

              {/* Lookerwood Farm */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="font-semibold">Lookerwood Farm</span>
                  <span className="text-muted-foreground">{formatNumber(farmMetrics?.revenue?.value, true)}</span>
                </div>
                {/* Visual Bar Split */}
                <div className="h-4 w-full rounded-full bg-muted overflow-hidden flex">
                  <div 
                    style={{ width: `${(farmMetrics?.revenue?.iap_value / (farmMetrics?.revenue?.value || 1)) * 100}%` }} 
                    className="bg-primary h-full transition-all duration-500" 
                    title={`IAP: ${formatNumber(farmMetrics?.revenue?.iap_value, true)}`}
                  />
                  <div 
                    style={{ width: `${(farmMetrics?.revenue?.ad_value / (farmMetrics?.revenue?.value || 1)) * 100}%` }} 
                    className="bg-indigo-400 h-full transition-all duration-500" 
                    title={`Ads: ${formatNumber(farmMetrics?.revenue?.ad_value, true)}`}
                  />
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-primary" /> IAP: {((farmMetrics?.revenue?.iap_value / (farmMetrics?.revenue?.value || 1)) * 100).toFixed(0)}%</span>
                  <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-indigo-400" /> Ads: {((farmMetrics?.revenue?.ad_value / (farmMetrics?.revenue?.value || 1)) * 100).toFixed(0)}%</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Scale & Retention Comparison Card */}
          <Card className="glass-card shadow-sm border border-border/50 bg-card/30 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Users className="h-4 w-4 text-indigo-500" />
                Player Engagement & Retention Cohorts
              </CardTitle>
              <CardDescription>Scale (DAU) and cohort stickiness (Day 1 Retention) comparison</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Scale Comparison */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="font-semibold text-muted-foreground">Daily Active Users Split</span>
                  <span className="text-xs font-medium bg-indigo-500/10 text-indigo-400 px-2 py-0.5 rounded-full">Active Players</span>
                </div>
                <div className="flex items-center gap-4">
                  <div className="w-1/2 space-y-1">
                    <span className="text-xs text-muted-foreground block">Battle Royale</span>
                    <span className="text-lg font-bold">{formatNumber(brMetrics?.dau?.value)}</span>
                  </div>
                  <div className="w-1/2 space-y-1 border-l border-border/40 pl-4">
                    <span className="text-xs text-muted-foreground block">Lookerwood Farm</span>
                    <span className="text-lg font-bold">{formatNumber(farmMetrics?.dau?.value)}</span>
                  </div>
                </div>
                {/* Horizontal Progress comparing the two */}
                <div className="h-2 w-full rounded-full bg-muted overflow-hidden flex">
                  <div 
                    style={{ width: `${(brMetrics?.dau?.value / ((brMetrics?.dau?.value || 1) + (farmMetrics?.dau?.value || 0))) * 100}%` }} 
                    className="bg-indigo-500 h-full"
                  />
                  <div 
                    style={{ width: `${(farmMetrics?.dau?.value / ((brMetrics?.dau?.value || 1) + (farmMetrics?.dau?.value || 0))) * 100}%` }} 
                    className="bg-indigo-300 h-full"
                  />
                </div>
              </div>

              {/* Retention Comparison */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="font-semibold text-muted-foreground">Day 1 Retention Quality</span>
                  <span className="text-xs font-medium bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full">Sticky Cohorts</span>
                </div>
                <div className="flex items-center gap-4">
                  <div className="w-1/2 space-y-1">
                    <span className="text-xs text-muted-foreground block">Battle Royale</span>
                    <span className="text-lg font-bold text-rose-500">{brMetrics?.retention?.value?.toFixed(2)}%</span>
                  </div>
                  <div className="w-1/2 space-y-1 border-l border-border/40 pl-4">
                    <span className="text-xs text-muted-foreground block">Lookerwood Farm</span>
                    <span className="text-lg font-bold text-emerald-500">{farmMetrics?.retention?.value?.toFixed(2)}%</span>
                  </div>
                </div>
                {/* Horizontal progress comparing retention rates */}
                <div className="h-2 w-full rounded-full bg-muted overflow-hidden flex">
                  <div 
                    style={{ width: `${(brMetrics?.retention?.value / ((brMetrics?.retention?.value || 1) + (farmMetrics?.retention?.value || 0))) * 100}%` }} 
                    className="bg-rose-500 h-full"
                  />
                  <div 
                    style={{ width: `${(farmMetrics?.retention?.value / ((brMetrics?.retention?.value || 1) + (farmMetrics?.retention?.value || 0))) * 100}%` }} 
                    className="bg-emerald-500 h-full"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Game Model Comparison Commentary Card */}
      {selectedGame === 'overall' && game_comparison && (
        <Card className="border border-indigo-500/20 bg-gradient-to-br from-indigo-950/10 via-card/30 to-background/50 backdrop-blur-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-bold flex items-center gap-2 text-indigo-400">
              <Sparkles className="h-4 w-4 animate-pulse text-indigo-400" />
              Strategic Game Comparison Commentary
            </CardTitle>
          </CardHeader>
          <CardContent className="prose prose-sm dark:prose-invert max-w-none text-muted-foreground/90 leading-relaxed italic border-t border-indigo-500/10 pt-3">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {game_comparison}
            </ReactMarkdown>
          </CardContent>
        </Card>
      )}

      {/* Comparative Metrics Table */}
      <Card className="border border-border/50 bg-card/10 shadow-sm backdrop-blur-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold">Comparative Metrics Breakdown</CardTitle>
          <CardDescription>Side-by-side comparison of Yesterday's metrics against the Day Before</CardDescription>
        </CardHeader>
        <CardContent className="p-0 border-t border-border/40">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left border-collapse">
              <thead>
                <tr className="border-b border-border bg-muted/30 text-muted-foreground font-semibold text-xs uppercase tracking-wider">
                  <th className="py-3 px-6">Gaming Performance Metric</th>
                  <th className="py-3 px-6 text-right">Yesterday</th>
                  <th className="py-3 px-6 text-right">Previous Day</th>
                  <th className="py-3 px-6 text-right">Day-over-Day Shift</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/30">
                {/* Total Revenue */}
                <tr className="hover:bg-muted/10 transition-colors">
                  <td className="py-3 px-6 font-semibold text-foreground">Total Revenue</td>
                  <td className="py-3 px-6 text-right font-bold text-foreground">{formatNumber(revenueVal, true)}</td>
                  <td className="py-3 px-6 text-right text-muted-foreground font-medium">
                    {formatNumber(getPrevValue(revenueVal, revenueChange), true)}
                  </td>
                  <td className="py-3 px-6 text-right flex justify-end">
                    <ChangePill change={revenueChange} />
                  </td>
                </tr>
                {/* IAP Revenue */}
                <tr className="hover:bg-muted/10 transition-colors">
                  <td className="py-3 px-6 pl-10 text-muted-foreground text-xs font-medium">↳ In-App Purchases (IAP)</td>
                  <td className="py-3 px-6 text-right font-medium text-foreground">{formatNumber(iapVal, true)}</td>
                  <td className="py-3 px-6 text-right text-muted-foreground">
                    {formatNumber(getPrevValue(iapVal, iapChange), true)}
                  </td>
                  <td className="py-3 px-6 text-right flex justify-end">
                    <ChangePill change={iapChange} />
                  </td>
                </tr>
                {/* Ad Revenue */}
                <tr className="hover:bg-muted/10 transition-colors">
                  <td className="py-3 px-6 pl-10 text-muted-foreground text-xs font-medium">↳ Advertising Ad Revenue</td>
                  <td className="py-3 px-6 text-right font-medium text-foreground">{formatNumber(adVal, true)}</td>
                  <td className="py-3 px-6 text-right text-muted-foreground">
                    {formatNumber(getPrevValue(adVal, adChange), true)}
                  </td>
                  <td className="py-3 px-6 text-right flex justify-end">
                    <ChangePill change={adChange} />
                  </td>
                </tr>
                {/* DAU */}
                <tr className="hover:bg-muted/10 transition-colors">
                  <td className="py-3 px-6 font-semibold text-foreground">Daily Active Users (DAU)</td>
                  <td className="py-3 px-6 text-right font-bold text-foreground">{formatNumber(dauVal, false)}</td>
                  <td className="py-3 px-6 text-right text-muted-foreground font-medium">
                    {formatNumber(getPrevValue(dauVal, dauChange), false)}
                  </td>
                  <td className="py-3 px-6 text-right flex justify-end">
                    <ChangePill change={dauChange} />
                  </td>
                </tr>
                {/* New Users */}
                <tr className="hover:bg-muted/10 transition-colors">
                  <td className="py-3 px-6 pl-10 text-muted-foreground text-xs font-medium">↳ New Player Registrations</td>
                  <td className="py-3 px-6 text-right font-medium text-foreground">{formatNumber(newUsersVal, false)}</td>
                  <td className="py-3 px-6 text-right text-muted-foreground">
                    {formatNumber(getPrevValue(newUsersVal, newUsersChange), false)}
                  </td>
                  <td className="py-3 px-6 text-right flex justify-end">
                    <ChangePill change={newUsersChange} />
                  </td>
                </tr>
                {/* Sessions */}
                <tr className="hover:bg-muted/10 transition-colors">
                  <td className="py-3 px-6 font-semibold text-foreground">Total Sessions</td>
                  <td className="py-3 px-6 text-right font-bold text-foreground">{formatNumber(sessionsVal, false)}</td>
                  <td className="py-3 px-6 text-right text-muted-foreground font-medium">
                    {formatNumber(getPrevValue(sessionsVal, sessionsChange), false)}
                  </td>
                  <td className="py-3 px-6 text-right flex justify-end">
                    <ChangePill change={sessionsChange} />
                  </td>
                </tr>
                {/* Day 1 Retention */}
                <tr className="hover:bg-muted/10 transition-colors">
                  <td className="py-3 px-6 font-semibold text-foreground">Day 1 Retention Rate</td>
                  <td className="py-3 px-6 text-right font-bold text-foreground">{retentionVal ? `${retentionVal.toFixed(2)}%` : '-'}</td>
                  <td className="py-3 px-6 text-right text-muted-foreground font-medium">
                    {retentionVal !== undefined && retentionChange !== undefined ? `${(retentionVal - retentionChange).toFixed(2)}%` : '-'}
                  </td>
                  <td className="py-3 px-6 text-right flex justify-end">
                    <ChangePill change={retentionChange} isRetention={true} />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Narrative & Charts Grid */}
      <div className="grid gap-6 md:grid-cols-12">
        {/* Narrative Analysis Column */}
        <div className="md:col-span-6 space-y-6">
          {/* Executive Narrative */}
          <Card className="border border-border/50 bg-card/10">
            <CardHeader>
              <CardTitle className="text-base font-semibold flex items-center gap-1.5">
                <Sparkles size={16} className="text-primary" />
                Executive Narrative Analysis
              </CardTitle>
              <CardDescription>Qualitative synthesis of product health metrics</CardDescription>
            </CardHeader>
            <CardContent className="prose prose-sm dark:prose-invert max-w-none text-muted-foreground leading-relaxed">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {narrative?.executive_summary || 'No narrative summary generated.'}
              </ReactMarkdown>
            </CardContent>
          </Card>

          {/* Highlights */}
          <Card className="border border-border/50 bg-card/10">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold">Key Highlights & Trends</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {narrative?.highlights && narrative.highlights.length > 0 ? (
                  narrative.highlights.map((highlight, idx) => (
                    <li key={idx} className="flex gap-2.5 text-sm text-muted-foreground leading-relaxed">
                      <span className="text-primary font-bold shrink-0">•</span>
                      <span>{highlight}</span>
                    </li>
                  ))
                ) : (
                  <li className="text-sm text-muted-foreground">No highlights recorded.</li>
                )}
              </ul>
            </CardContent>
          </Card>

          {/* Action Items */}
          <Card className="border border-border/50 bg-card/10">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold">Recommended Action Items</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {narrative?.action_items && narrative.action_items.length > 0 ? (
                  narrative.action_items.map((item, idx) => {
                    const itemText = typeof item === 'object' ? item.text : item;
                    const exploreUrl = typeof item === 'object' ? item.explore_url : null;

                    return (
                      <div 
                        key={idx} 
                        className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-3.5 rounded-xl border border-border/40 bg-card/30 hover:border-border/80 hover:bg-card/45 transition-all duration-300 shadow-sm"
                      >
                        <div className="flex gap-3 text-sm text-muted-foreground leading-relaxed">
                          <span className="text-indigo-400 font-bold shrink-0 mt-0.5">{idx + 1}.</span>
                          <span>{itemText}</span>
                        </div>
                        {exploreUrl && (
                          <a 
                            href={exploreUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 justify-center rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 px-3.5 py-1.5 text-xs font-semibold text-indigo-400 border border-indigo-500/20 hover:border-indigo-500/40 transition-all shrink-0 active:scale-95"
                          >
                            <span>Explore in Looker</span>
                            <ExternalLink size={12} className="shrink-0" />
                          </a>
                        )}
                      </div>
                    );
                  })
                ) : (
                  <div className="text-sm text-muted-foreground text-center py-4">No recommended actions.</div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* AI Agent Automation Hub */}
          <Card className="border border-border/50 bg-card/10">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold flex items-center gap-1.5">
                <Terminal size={16} className="text-indigo-400" />
                AI Agent Automation Hub
              </CardTitle>
              <CardDescription>Launch autonomous agent tasks to monitor metrics, optimize operations, or deploy infrastructure.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* D1 Retention Monitor */}
                <div className="p-3.5 rounded-xl border border-border/40 bg-card/25 hover:border-indigo-500/40 hover:bg-card/35 transition-all duration-300">
                  <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                          KPI Tracking
                        </span>
                        <h4 className="text-sm font-semibold text-foreground">D1 Retention Monitor</h4>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        Spawns a periodic cron-driven agent to query user retention and dispatch Slack alerts if stickiness drops.
                      </p>
                    </div>
                    <Button 
                      onClick={() => runWorkflow('kpi_monitor')}
                      className="inline-flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-xs px-3.5 py-1.5 h-8 font-semibold text-white transition-all active:scale-95 shrink-0 self-end sm:self-center"
                    >
                      <Play size={10} className="fill-current" />
                      <span>Launch</span>
                    </Button>
                  </div>
                </div>

                {/* Ad Bidding Optimizer */}
                <div className="p-3.5 rounded-xl border border-border/40 bg-card/25 hover:border-indigo-500/40 hover:bg-card/35 transition-all duration-300">
                  <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                          System Action
                        </span>
                        <h4 className="text-sm font-semibold text-foreground">Ad Bidding Optimizer</h4>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        Queries hourly network yields and makes automated bid updates via the AdNetwork API to stabilize ad revenue.
                      </p>
                    </div>
                    <Button 
                      onClick={() => runWorkflow('ad_optimizer')}
                      className="inline-flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-xs px-3.5 py-1.5 h-8 font-semibold text-white transition-all active:scale-95 shrink-0 self-end sm:self-center"
                    >
                      <Play size={10} className="fill-current" />
                      <span>Run</span>
                    </Button>
                  </div>
                </div>

                {/* Analytics GCF Pipeline Manager */}
                <div className="p-4 rounded-xl border border-border/40 bg-card/25 hover:border-indigo-500/40 transition-all duration-300 space-y-4">
                  <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4 border-b border-border/20 pb-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                          Infrastructure
                        </span>
                        <h4 className="text-sm font-semibold text-foreground">Cohort Analytics Pipeline</h4>
                        <div className="flex items-center gap-1.5 ml-2">
                          <span className={`h-2 w-2 rounded-full ${isGcfPaused ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400 animate-pulse'}`} />
                          <span className="text-[10px] font-medium text-muted-foreground">
                            {isGcfPaused ? 'Paused' : 'Active'}
                          </span>
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        Secure Google Cloud Function that compiles and analyzes daily cohort performance. Deployed & operational.
                      </p>
                    </div>

                    <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                      <Button
                        onClick={() => runWorkflow('deploy_gcf', isGcfPaused ? 'resume' : 'pause')}
                        variant="outline"
                        className={`text-xs px-3 py-1.5 h-8 font-semibold transition-all active:scale-95 border-border/60 ${isGcfPaused ? 'hover:bg-emerald-500/10 hover:text-emerald-400 hover:border-emerald-500/20' : 'hover:bg-amber-500/10 hover:text-amber-400 hover:border-amber-500/20'}`}
                      >
                        {isGcfPaused ? (
                          <>
                            <Play size={10} className="fill-current mr-1.5" />
                            <span>Resume</span>
                          </>
                        ) : (
                          <>
                            <Pause size={10} className="fill-current mr-1.5" />
                            <span>Pause</span>
                          </>
                        )}
                      </Button>
                      <Button 
                        onClick={() => setShowGcfSettings(!showGcfSettings)}
                        variant={showGcfSettings ? "secondary" : "outline"}
                        className="text-xs px-3 py-1.5 h-8 font-semibold transition-all active:scale-95 border-border/60"
                      >
                        <Settings size={11} className="mr-1.5" />
                        <span>{showGcfSettings ? 'Close' : 'Configure'}</span>
                      </Button>
                    </div>
                  </div>

                  {/* Active Endpoint Info */}
                  <div className="text-[11px] font-mono text-indigo-400/80 bg-indigo-500/5 border border-indigo-500/10 rounded-lg p-2 flex items-center justify-between">
                    <span className="truncate">URL: /api/cohort-analyzer</span>
                    <a 
                      href={`/api/cohort-analyzer?schedule=${encodeURIComponent(gcfSchedule)}&target=${encodeURIComponent(gcfTargetSegment)}&webhook=${encodeURIComponent(gcfAlertEmail)}&threshold=${encodeURIComponent(gcfThreshold)}`}
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="ml-2 hover:text-indigo-300 transition-colors flex items-center gap-1 text-[10px] text-indigo-400 border border-indigo-500/25 px-2 py-0.5 rounded bg-indigo-500/10 font-sans font-semibold active:scale-95 transition-all"
                    >
                      <span>Trigger Pipeline</span>
                      <ExternalLink size={10} />
                    </a>
                  </div>

                  {/* Display Pipeline Settings */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs bg-muted/20 border border-border/20 rounded-xl p-3">
                    <div>
                      <span className="text-[10px] text-muted-foreground block uppercase font-mono">Schedule</span>
                      <span className="font-semibold text-foreground truncate block">{gcfSchedule}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-muted-foreground block uppercase font-mono">Segment</span>
                      <span className="font-semibold text-foreground truncate block">{gcfTargetSegment}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-muted-foreground block uppercase font-mono">Chat Webhook</span>
                      <span className="font-semibold text-foreground truncate block text-indigo-400" title={gcfAlertEmail || 'System Default'}>{gcfAlertEmail ? 'Configured' : 'System Default'}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-muted-foreground block uppercase font-mono">Threshold</span>
                      <span className="font-semibold text-foreground truncate block">{gcfThreshold}</span>
                    </div>
                  </div>

                  {/* Expandable Settings Form */}
                  {showGcfSettings && (
                    <div className="border border-border/30 bg-muted/10 rounded-xl p-4 space-y-4 animate-in slide-in-from-top-2 duration-300">
                      <h5 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                        <Sliders size={12} className="text-indigo-400" />
                        <span>Pipeline Configuration</span>
                      </h5>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                          <label className="text-[10px] font-medium text-muted-foreground">Trigger Schedule (Cron)</label>
                          <input 
                            type="text" 
                            value={gcfSchedule} 
                            onChange={(e) => setGcfSchedule(e.target.value)}
                            className="w-full bg-background/50 border border-border/60 text-xs text-foreground rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500/80 transition-colors"
                          />
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-[10px] font-medium text-muted-foreground">Target User Segment</label>
                          <select 
                            value={gcfTargetSegment} 
                            onChange={(e) => setGcfTargetSegment(e.target.value)}
                            className="w-full bg-background/50 border border-border/60 text-xs text-foreground rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500/80 transition-colors"
                          >
                            <option value="All Active Players">All Active Players</option>
                            <option value="Paying Users (IAP)">Paying Users (IAP)</option>
                            <option value="New Players (D1-D7)">New Players (D1-D7)</option>
                            <option value="Churn Risks">Churn Risks</option>
                          </select>
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-[10px] font-medium text-muted-foreground">Chat Webhook URL (Google Chat / Slack)</label>
                          <input 
                            type="text" 
                            value={gcfAlertEmail} 
                            placeholder="https://chat.googleapis.com/v1/spaces/..."
                            onChange={(e) => setGcfAlertEmail(e.target.value)}
                            className="w-full bg-background/50 border border-border/60 text-xs text-foreground rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500/80 transition-colors"
                          />
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-[10px] font-medium text-muted-foreground">Correlation Threshold</label>
                          <input 
                            type="text" 
                            value={gcfThreshold} 
                            onChange={(e) => setGcfThreshold(e.target.value)}
                            className="w-full bg-background/50 border border-border/60 text-xs text-foreground rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500/80 transition-colors"
                          />
                        </div>
                      </div>
                      <div className="flex justify-end gap-2 pt-2 border-t border-border/10">
                        <Button 
                          onClick={() => setShowGcfSettings(false)}
                          variant="ghost" 
                          className="text-xs px-3.5 h-8 font-semibold hover:bg-muted active:scale-95"
                        >
                          Cancel
                        </Button>
                        <Button 
                          onClick={() => {
                            runWorkflow('deploy_gcf', 'update_settings');
                            setShowGcfSettings(false);
                          }}
                          className="bg-indigo-600 hover:bg-indigo-500 text-xs px-3.5 h-8 font-semibold text-white transition-all active:scale-95"
                        >
                          Apply Configuration
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Charts Column */}
        <div className="md:col-span-6 space-y-6">
          {/* Revenue stacked mix area chart */}
          <Card className="border border-border/50 bg-card/10">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold">Revenue Trend (IAP vs. Ad Revenue)</CardTitle>
              <CardDescription>7-day stacked visualization of total income generation</CardDescription>
            </CardHeader>
            <CardContent className="h-72 pt-2">
              {revenueMixChart ? (
                <ChartRenderer config={revenueMixChart} />
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground text-sm border border-dashed rounded-lg">
                  Revenue trend data not available
                </div>
              )}
            </CardContent>
          </Card>

          {/* Dual Axis DAU & D1 Retention combo chart */}
          <Card className="border border-border/50 bg-card/10">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold">Active Players & Retention Rate</CardTitle>
              <CardDescription>7-day comparison of DAU (bars) vs Day 1 Retention (line)</CardDescription>
            </CardHeader>
            <CardContent className="h-72 pt-2">
              {dauRetentionChart ? (
                <ChartRenderer config={dauRetentionChart} />
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground text-sm border border-dashed rounded-lg">
                  DAU & Retention trend data not available
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Workflow Modal Overlay */}
      {isWorkflowModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-2xl rounded-2xl border border-border bg-card/90 shadow-2xl backdrop-blur-xl animate-in scale-in duration-300 overflow-hidden">
            
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-border/60 p-4">
              <div className="flex items-center gap-2">
                <Terminal size={18} className="text-primary animate-pulse" />
                <h3 className="font-semibold text-foreground">
                  {activeWorkflow === 'kpi_monitor' && 'D1 Retention Monitor'}
                  {activeWorkflow === 'ad_optimizer' && 'Ad Bidding Optimizer'}
                  {activeWorkflow === 'deploy_gcf' && (
                    gcfAction === 'pause' ? 'Pausing Cloud Function Pipeline' :
                    gcfAction === 'resume' ? 'Resuming Cloud Function Pipeline' :
                    gcfAction === 'update_settings' ? 'Updating Pipeline Configuration' :
                    'Cloud Function Provisioner'
                  )}
                </h3>
              </div>
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={cancelWorkflow}
                disabled={workflowStatus === 'running'}
                className="h-8 w-8 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted active:scale-95 disabled:opacity-30 disabled:pointer-events-none"
              >
                <X size={16} />
              </Button>
            </div>

            {/* Modal Content */}
            <div className="p-5 space-y-4">
              
              {/* Status Bar */}
              <div className="flex items-center justify-between p-3 rounded-xl border border-border/40 bg-muted/40">
                <div className="flex items-center gap-3">
                  {workflowStatus === 'running' && (
                    <Loader2 size={16} className="text-indigo-400 animate-spin" />
                  )}
                  {workflowStatus === 'success' && (
                    <CheckCircle size={16} className="text-emerald-400" />
                  )}
                  {workflowStatus === 'error' && (
                    <X size={16} className="text-destructive" />
                  )}
                  <span className="text-sm font-medium text-muted-foreground">
                    Status: {' '}
                    <span className={`font-semibold ${
                      workflowStatus === 'running' ? 'text-indigo-400' :
                      workflowStatus === 'success' ? 'text-emerald-400' :
                      workflowStatus === 'error' ? 'text-destructive font-bold' : 'text-foreground'
                    }`}>
                      {workflowStatus.toUpperCase()}
                    </span>
                  </span>
                </div>
                {workflowStatus === 'running' && (
                  <span className="text-xs text-indigo-400/80 animate-pulse">Agent is reasoning...</span>
                )}
              </div>

              {/* Terminal Logs */}
              <div className="flex flex-col h-64 bg-black/90 rounded-xl border border-border/40 p-4 font-mono text-[11px] leading-relaxed text-emerald-400 overflow-y-auto space-y-1.5 shadow-inner">
                {workflowLogs.map((log, index) => {
                  let statusColor = "text-emerald-400";
                  if (log.status === "error") statusColor = "text-red-400 font-bold";
                  if (log.status === "success") statusColor = "text-indigo-400 font-semibold";
                  if (log.status === "querying") statusColor = "text-cyan-400";
                  if (log.status === "analyzing") statusColor = "text-yellow-400";
                  if (log.status === "planning") statusColor = "text-pink-400";
                  if (log.status === "executing") statusColor = "text-purple-400 animate-pulse";

                  return (
                    <div key={index} className="flex gap-2">
                      <span className="text-muted-foreground shrink-0 select-none">[{index + 1}]</span>
                      <span className={statusColor}>{log.message}</span>
                    </div>
                  );
                })}
                {workflowStatus === 'running' && (
                  <div className="flex items-center gap-1.5 text-muted-foreground animate-pulse text-[10px] mt-1 select-none">
                    <span>$ tail -f /var/log/antigravity.log</span>
                    <span className="w-1.5 h-3 bg-emerald-400 animate-blink"></span>
                  </div>
                )}
                <div ref={terminalEndRef} />
              </div>

              {/* Action Buttons */}
              <div className="flex justify-end gap-3 pt-2">
                {workflowStatus === 'running' && (
                  <Button 
                    variant="outline" 
                    onClick={cancelWorkflow}
                    className="border-destructive/30 hover:bg-destructive/10 text-destructive text-xs transition-all active:scale-95 font-semibold"
                  >
                    Abort Workflow
                  </Button>
                )}
                {workflowStatus !== 'running' && (
                  <Button 
                    onClick={cancelWorkflow}
                    className="bg-indigo-600 hover:bg-indigo-500 text-xs px-5 py-2 font-semibold text-white transition-all active:scale-95"
                  >
                    Close Console
                  </Button>
                )}
              </div>

            </div>

          </div>
        </div>
      )}
    </div>
  );
};

export default AiSummaryDashboard;

# Gemini Enterprise (GE) Publishing & Integration Guide for Gaming Analytics

This guide explains how to publish and demo your **Gaming Analytics AI Agent** in **Gemini Enterprise (GE)** while keeping your existing React/Flask web interface fully operational.

---

## 🎯 Architecture Overview: Dual-Surface Availability

```
                          ┌────────────────────────────────────────┐
                          │         Gaming Analytics Core          │
                          │   (Looker + Spanner + Multi-Agent)     │
                          └──────────────────┬─────────────────────┘
                                             │
                      ┌──────────────────────┴──────────────────────┐
                      ▼                                             ▼
        ┌───────────────────────────┐                 ┌───────────────────────────┐
        │    Dedicated Web App      │                 │     Gemini Enterprise     │
        │    (React / Vite UI)      │                 │  (go/ge / Agentspace UI)  │
        │                           │                 │                           │
        │ • Custom 2D force graphs  │                 │ • Corporate AI Hub        │
        │ • Live thinking stream    │                 │ • Natural language chat   │
        │ • Embedded Looker frames  │                 │ • Standard Markdown/Tables│
        │ • Multi-model hot-swap    │                 │ • Organization sharing    │
        └───────────────────────────┘                 └───────────────────────────┘
```

Both surfaces share the same underlying Cloud Run service, LookML models, and Spanner Graph data. Changes made on one surface do not degrade the other.

---

## 🛠️ Step-by-Step Publishing to Gemini Enterprise

### Method 1: Gemini Enterprise Agent Designer (Recommended for Demos)

Gemini Enterprise's **Agent Designer** allows you to configure and publish custom agents using OpenAPI Tool Actions.

#### 1. Deploy the Backend to Cloud Run
Ensure your latest backend is running on Cloud Run:
```bash
./scripts/publish_to_gemini_enterprise.sh
```
*Note your Cloud Run Service URL: `https://ca-api-1094200614711.us-central1.run.app`.*

#### 2. Open Agent Designer in Gemini Enterprise
1. Navigate to **Gemini Enterprise** at [go/ge](https://goto.google.com/ge) or open the **Google Cloud Console** > **Gemini Enterprise** > **Agents**.
2. Click **Create Agent** (or **New Agent** > **Custom Agent**).

#### 3. Fill in Agent Details
- **Agent Name**: `Gaming Analytics AI`
- **Display Name**: `Gaming Analytics Intelligence`
- **Description**: `Autonomous mobile gaming analytics AI agent for Looker metrics, Spanner graph clan hierarchies, and LiveOps dashboards.`
- **Icon**: Select `Gamepad` or `Bar Chart`.

#### 4. Configure Instructions (Persona & Rules)
In the **Instructions / Prompt** pane, paste the contents of `gemini_enterprise_instructions.md`:
```markdown
You are the Gaming Analytics Intelligence Agent in Gemini Enterprise.
Your mission is to provide high-velocity, deeply analytical insights for mobile gaming business leaders, liveops managers, and product teams.
...
```

#### 5. Add OpenAPI Tools / Actions
1. In the **Tools** or **Actions** section, click **Add Tool** > **OpenAPI Specification**.
2. Choose **Import from URL** and enter:
   ```
   https://ca-api-1094200614711.us-central1.run.app/openapi.yaml
   ```
   *(Or upload `gemini_enterprise_openapi.yaml` directly).*
3. The following operations will be automatically recognized:
   - `queryGamingAnalytics`: Multi-agent dispatcher (Metrics, Clans, Dashboards, Research).
   - `getLookerInsights`: Direct Looker Conversational Analytics tool.
   - `getDailySummary`: Executive daily briefing & comparative performance.
   - `getPlayerSafetySummary`: Toxicity metrics & moderation incident stream.
   - `getCohortAnalysis`: Cohort retention lifecycle curves.
   - `generateLookerEmbedUrl`: Signed SSO Looker embed URLs.

#### 6. Configure Conversation Starters
Add the following recommended prompt chips:
1. `What was our total revenue, DAU, and ARPU yesterday broken down by game?`
2. `Compare Lookup Battle Royale vs Lookerwood Farm across monetization and retention.`
3. `Show me the clan hierarchy and leadership roster for Dragonslayers.`
4. `Generate yesterday's Executive Daily Summary briefing.`
5. `What is our player trust & safety incident status and toxicity exposure?`

#### 7. Preview and Publish
1. Test your agent in the live **Preview** pane.
2. Click **Save** and **Publish**.
3. Choose your sharing scope: **Only Me**, **My Team**, or **All Google (Organization)**.

---

### Method 2: Vertex AI Agent Registry (High-Code ADK Import)

For an integrated Agent Platform setup:
1. Deploy the ADK agent to Vertex AI Agent Engine / Reasoning Engine:
   ```bash
   python deploy_gemini_enterprise_agent.py
   ```
2. Open **Gemini Enterprise** > **Agent Management** > **Agent Registry**.
3. Click **Import Agent** and select `Gaming Analytics Intelligence (Gemini Enterprise)`.
4. Configure IAM permissions for who can discover and invoke the agent.

---

## 🎬 Live Demo Script (What to Show in Gemini Enterprise)

When demoing the agent inside Gemini Enterprise:

### Query 1: Quantitative Telemetry (Looker)
> **Prompt**: *"What was our total revenue and DAU yesterday by game?"*  
> **Agent Action**: Calls `queryGamingAnalytics` (routed to `Metrics Analyst`).  
> **Expected Output**: Formatted markdown table comparing *Lookup Battle Royale* and *Lookerwood Farm*, highlighting IAP vs Ad revenue, and providing a clickable `[📊 Open in Looker Explore]` link.

### Query 2: Cross-Game Strategic Comparison
> **Prompt**: *"Compare Lookup Battle Royale vs Lookerwood Farm across monetization mix, D1 retention, and player engagement."*  
> **Agent Action**: Calls `getDailySummary` or `queryGamingAnalytics`.  
> **Expected Output**: Executive briefing contrasting Battle Royale's high-IAP/low-ad model vs Farm's ad-driven model, with retention rates and specific action items.

### Query 3: Social Graph Intelligence (Spanner Graph)
> **Prompt**: *"Who is the leader of the Dragonslayers clan, and what is their officer roster?"*  
> **Agent Action**: Calls `queryGamingAnalytics` (routed to `Social Graph Specialist`).  
> **Expected Output**: Roster broken down into Leader, Officers, and Members, citing *Source: Google Cloud Spanner Graph Database*.

### Query 4: Trust & Safety Telemetry
> **Prompt**: *"What is our player safety incident status and toxicity exposure rate?"*  
> **Agent Action**: Calls `getPlayerSafetySummary`.  
> **Expected Output**: Toxicity KPI metrics (exposure rate, honor index, auto-mitigation velocity) and a table of recent critical incident actions (speed hack bans, griefing forfeits).

---

## 📁 Key File Reference

| File | Description |
|---|---|
| `gemini_enterprise_openapi.yaml` | Full OpenAPI 3.0 specification for Gemini Enterprise tool integration. |
| `gemini_enterprise_agent_config.json` | Complete agent definition and metadata for Gemini Enterprise / Agentspace. |
| `gemini_enterprise_instructions.md` | Persona prompt and instructions for the Agent Designer prompt editor. |
| `deploy_gemini_enterprise_agent.py` | Vertex AI Reasoning Engine / Agent Engine deployment script. |
| `scripts/publish_to_gemini_enterprise.sh` | Automated Cloud Run deployment and publication helper script. |
| `server.py` | Flask backend hosting `/api/query`, `/api/insights`, `/chat`, and the web app. |

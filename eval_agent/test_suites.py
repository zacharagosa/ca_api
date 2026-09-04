"""
Preset Test Suites and Test Case Catalog for the 4 Gaming Analytics Conversation Types.
"""
from typing import List, Dict
from eval_agent.models import (
    TestCase, SubagentCategory, TestDifficulty, ExpectedArtifacts,
    MultiTurnDialogueCase, MultiTurnTurn, PersonaType
)

# -----------------------------------------------------------------------------
# CATEGORY 1: Quantitative Looker Metrics Analyst (`metrics_fast`)
# -----------------------------------------------------------------------------
METRICS_TEST_CASES: List[TestCase] = [
    TestCase(
        id="metrics_01_total_revenue",
        category=SubagentCategory.METRICS_FAST,
        title="Total Revenue Aggregation (30 Days)",
        description="Verify total revenue aggregation over the last 30 days across all gaming titles.",
        difficulty=TestDifficulty.BASIC,
        prompt="What was total revenue over the last 30 days?",
        expected_subagent=SubagentCategory.METRICS_FAST,
        expected_artifacts=ExpectedArtifacts(
            table_required=False,
            link_required=True,
            must_contain_keywords=["$", "revenue"]
        ),
        tags=["revenue", "aggregation", "looker"]
    ),
    TestCase(
        id="metrics_02_revenue_by_game",
        category=SubagentCategory.METRICS_FAST,
        title="Revenue Breakdown by Game Title",
        description="Verify breakdown of total revenue by game title (Lookup Battle Royale vs Lookerwood Farm).",
        difficulty=TestDifficulty.BASIC,
        prompt="What was total revenue by game over the last 30 days?",
        expected_subagent=SubagentCategory.METRICS_FAST,
        expected_artifacts=ExpectedArtifacts(
            table_required=True,
            link_required=True,
            must_contain_keywords=["Lookerwood Farm", "Lookup Battle Royale"]
        ),
        tags=["breakdown", "game_name", "revenue"]
    ),
    TestCase(
        id="metrics_03_dau_trend_chart",
        category=SubagentCategory.METRICS_FAST,
        title="Daily Active Users 30-Day Trend Chart",
        description="Verify daily active users time-series extraction and automatic chart generation.",
        difficulty=TestDifficulty.INTERMEDIATE,
        prompt="Show daily active users over the last 30 days as a line chart",
        expected_subagent=SubagentCategory.METRICS_FAST,
        expected_artifacts=ExpectedArtifacts(
            chart_required=True,
            table_required=True,
            link_required=True,
            must_contain_keywords=["users"]
        ),
        tags=["dau", "time_series", "chart", "vega_lite"]
    ),
    TestCase(
        id="metrics_04_iap_vs_ad_country",
        category=SubagentCategory.METRICS_FAST,
        title="IAP vs Ad Revenue Split by Country",
        description="Verify multi-metric quantitative comparison (IAP vs Ad revenue) partitioned by country.",
        difficulty=TestDifficulty.INTERMEDIATE,
        prompt="Compare total iap revenue and total ad revenue by country over the last 30 days",
        expected_subagent=SubagentCategory.METRICS_FAST,
        expected_artifacts=ExpectedArtifacts(
            table_required=True,
            link_required=True,
            must_contain_keywords=["country", "iap", "ad"]
        ),
        tags=["multi_metric", "country", "monetization"]
    ),
    TestCase(
        id="metrics_05_arpu_retention",
        category=SubagentCategory.METRICS_FAST,
        title="ARPU and D1/D7 Retention Metrics",
        description="Verify accurate retrieval of calculated unit economics (ARPU, ARPPU) and D1 retention percentages.",
        difficulty=TestDifficulty.ADVANCED,
        prompt="What is the average revenue per user (ARPU) and Day 1 retention rate by game title?",
        expected_subagent=SubagentCategory.METRICS_FAST,
        expected_artifacts=ExpectedArtifacts(
            table_required=True,
            link_required=True,
            must_contain_keywords=["ARPU", "%", "retention"]
        ),
        tags=["arpu", "retention", "unit_economics"]
    ),
    TestCase(
        id="metrics_06_platform_breakdown",
        category=SubagentCategory.METRICS_FAST,
        title="Device Platform Performance (iOS vs Android)",
        description="Verify filtering and grouping by device_platform dimension.",
        difficulty=TestDifficulty.BASIC,
        prompt="Break down active users and total sessions by device platform for the last 7 days",
        expected_subagent=SubagentCategory.METRICS_FAST,
        expected_artifacts=ExpectedArtifacts(
            table_required=True,
            link_required=True,
            must_contain_keywords=["iOS", "Android"]
        ),
        tags=["platform", "ios", "android", "sessions"]
    )
]

# -----------------------------------------------------------------------------
# CATEGORY 2: Spanner Social Graph & Clan Intelligence (`social_graph`)
# -----------------------------------------------------------------------------
SOCIAL_GRAPH_TEST_CASES: List[TestCase] = [
    TestCase(
        id="social_01_clan_roster",
        category=SubagentCategory.SOCIAL_GRAPH,
        title="Clan Roster & Member Hierarchy",
        description="Verify query of clan memberships, player gamertags, and leadership roles in Spanner.",
        difficulty=TestDifficulty.BASIC,
        prompt="Who are the members of the Order of Titans clan and what are their roles?",
        expected_subagent=SubagentCategory.SOCIAL_GRAPH,
        expected_artifacts=ExpectedArtifacts(
            table_required=True,
            must_contain_keywords=["Order of Titans", "Leader", "Officer", "Spanner Graph"]
        ),
        tags=["clan", "hierarchy", "spanner", "roles"]
    ),
    TestCase(
        id="social_02_friendship_network",
        category=SubagentCategory.SOCIAL_GRAPH,
        title="Player Friendship Network & Force Graph",
        description="Verify extraction of 2D force-directed friendship graph with column aliases 'player' and 'friend'.",
        difficulty=TestDifficulty.INTERMEDIATE,
        prompt="Show the social connections and friendship network for player DragonSlayer_Ace",
        expected_subagent=SubagentCategory.SOCIAL_GRAPH,
        expected_artifacts=ExpectedArtifacts(
            graph_required=True,
            must_contain_keywords=["friend", "Spanner Graph"]
        ),
        tags=["social_network", "friendships", "graph_viz"]
    ),
    TestCase(
        id="social_03_clan_leadership_levels",
        category=SubagentCategory.SOCIAL_GRAPH,
        title="Cross-Clan Leader & Officer Account Levels",
        description="Verify multi-table join across Players, Clans, and ClanMemberships in Spanner Graph.",
        difficulty=TestDifficulty.ADVANCED,
        prompt="List all clan leaders across all clans with their account level and join date",
        expected_subagent=SubagentCategory.SOCIAL_GRAPH,
        expected_artifacts=ExpectedArtifacts(
            table_required=True,
            must_contain_keywords=["Leader", "account_level", "Spanner Graph"]
        ),
        tags=["clans", "leadership", "account_level"]
    ),
    TestCase(
        id="social_04_shadow_syndicate_members",
        category=SubagentCategory.SOCIAL_GRAPH,
        title="Shadow Syndicate Clan Intelligence",
        description="Verify member discovery and role partitioning for Shadow Syndicate clan.",
        difficulty=TestDifficulty.BASIC,
        prompt="Show me all officers and members in the Shadow Syndicate clan",
        expected_subagent=SubagentCategory.SOCIAL_GRAPH,
        expected_artifacts=ExpectedArtifacts(
            table_required=True,
            must_contain_keywords=["Shadow Syndicate", "Spanner Graph"]
        ),
        tags=["shadow_syndicate", "members", "roles"]
    )
]

# -----------------------------------------------------------------------------
# CATEGORY 3: Looker MCP LiveOps Dashboard Architect (`dashboard_builder`)
# -----------------------------------------------------------------------------
DASHBOARD_TEST_CASES: List[TestCase] = [
    TestCase(
        id="dash_01_create_war_room",
        category=SubagentCategory.DASHBOARD_BUILDER,
        title="Create LiveOps War Room Dashboard",
        description="Verify autonomous creation of a multi-tile Looker dashboard with KPI and chart elements.",
        difficulty=TestDifficulty.INTERMEDIATE,
        prompt="Build a new LiveOps War Room dashboard with DAU and Total Revenue tiles",
        expected_subagent=SubagentCategory.DASHBOARD_BUILDER,
        expected_artifacts=ExpectedArtifacts(
            dashboard_required=True,
            link_required=True,
            must_contain_keywords=["View & Edit Live Dashboard", "/embed/dashboards/"]
        ),
        tags=["create_dashboard", "looker_mcp", "war_room"]
    ),
    TestCase(
        id="dash_02_modify_timeframe",
        category=SubagentCategory.DASHBOARD_BUILDER,
        title="Modify Dashboard Tile Timeframe",
        description="Verify in-place modification of existing dashboard tiles (e.g. extending timeframe to 90 days).",
        difficulty=TestDifficulty.ADVANCED,
        prompt="Modify the timeframe on all tiles on this dashboard to 90 days",
        expected_subagent=SubagentCategory.DASHBOARD_BUILDER,
        expected_artifacts=ExpectedArtifacts(
            dashboard_required=True,
            must_contain_keywords=["90", "dashboard"]
        ),
        tags=["edit_dashboard", "timeframe", "modify_tiles"]
    ),
    TestCase(
        id="dash_03_add_filter_kpi",
        category=SubagentCategory.DASHBOARD_BUILDER,
        title="Add Country Filter and Single-Value KPI Tile",
        description="Verify addition of dashboard-level filters and high-priority KPI summary widgets.",
        difficulty=TestDifficulty.ADVANCED,
        prompt="Add a Country filter and a single-value KPI tile for Total IAP Revenue to this dashboard",
        expected_subagent=SubagentCategory.DASHBOARD_BUILDER,
        expected_artifacts=ExpectedArtifacts(
            dashboard_required=True,
            must_contain_keywords=["filter", "Country", "IAP Revenue"]
        ),
        tags=["add_filter", "kpi_tile", "edit_dashboard"]
    )
]

# -----------------------------------------------------------------------------
# CATEGORY 4: Strategic Deep Research & Cross-Domain Intelligence (`deep_research`)
# -----------------------------------------------------------------------------
DEEP_RESEARCH_TEST_CASES: List[TestCase] = [
    TestCase(
        id="deep_01_whales_clan_synthesis",
        category=SubagentCategory.DEEP_RESEARCH,
        title="Whale Spending & Clan Dynamics Investigation",
        description="Verify multi-hop cross-domain analysis correlating Looker IAP telemetry with Spanner clan hierarchies.",
        difficulty=TestDifficulty.ADVANCED,
        prompt="Analyze the relationship between top spending whales, their clan memberships, and overall revenue trends.",
        expected_subagent=SubagentCategory.DEEP_RESEARCH,
        expected_artifacts=ExpectedArtifacts(
            table_required=True,
            must_contain_keywords=["Executive Summary", "Strategic", "clan", "revenue"]
        ),
        tags=["multi_hop", "whales", "clans", "cross_domain"]
    ),
    TestCase(
        id="deep_02_retention_social_correlation",
        category=SubagentCategory.DEEP_RESEARCH,
        title="Social Density vs D7 Retention Correlation",
        description="Verify root cause synthesis on how in-game friendship clusters impact player retention curves.",
        difficulty=TestDifficulty.ADVANCED,
        prompt="Investigate the correlation between clan social network density and Day 7 player retention across game titles.",
        expected_subagent=SubagentCategory.DEEP_RESEARCH,
        expected_artifacts=ExpectedArtifacts(
            table_required=True,
            must_contain_keywords=["retention", "clan", "recommendations"]
        ),
        tags=["retention", "social_density", "correlation"]
    )
]

# -----------------------------------------------------------------------------
# MULTI-TURN CONVERSATIONAL TEST SUITES
# -----------------------------------------------------------------------------
MULTI_TURN_DIALOGUES: List[MultiTurnDialogueCase] = [
    MultiTurnDialogueCase(
        id="dialogue_metrics_drilldown",
        title="Executive Metrics Follow-Up Drilldown",
        category=SubagentCategory.METRICS_FAST,
        persona=PersonaType.EXECUTIVE_VP,
        description="Multi-turn quantitative drilldown: Revenue -> User Count -> Country Breakdown -> Charting.",
        turns=[
            MultiTurnTurn(
                turn=1,
                prompt="What was total revenue by game over last 30d?",
                expected_subagent=SubagentCategory.METRICS_FAST,
                expected_keywords=["Lookerwood Farm", "Lookup Battle Royale"],
                expected_artifacts=ExpectedArtifacts(table_required=True, link_required=True)
            ),
            MultiTurnTurn(
                turn=2,
                prompt="How many active users did we have for those same games over that period?",
                expected_subagent=SubagentCategory.METRICS_FAST,
                expected_keywords=["users", "Lookerwood Farm", "Lookup Battle Royale"],
                expected_artifacts=ExpectedArtifacts(table_required=True)
            ),
            MultiTurnTurn(
                turn=3,
                prompt="Break down the revenue by country as well",
                expected_subagent=SubagentCategory.METRICS_FAST,
                expected_keywords=["country", "US"],
                expected_artifacts=ExpectedArtifacts(table_required=True)
            ),
            MultiTurnTurn(
                turn=4,
                prompt="Show this as a bar chart",
                expected_subagent=SubagentCategory.METRICS_FAST,
                expected_keywords=[],
                expected_artifacts=ExpectedArtifacts(chart_required=True)
            )
        ]
    ),
    MultiTurnDialogueCase(
        id="dialogue_social_investigation",
        title="Community Lead Clan Investigation",
        category=SubagentCategory.SOCIAL_GRAPH,
        persona=PersonaType.GUILD_MASTER,
        description="Multi-turn social investigation: Clan Roster -> Leadership -> Friendships -> Force Graph.",
        turns=[
            MultiTurnTurn(
                turn=1,
                prompt="Who are the members of the Order of Titans clan?",
                expected_subagent=SubagentCategory.SOCIAL_GRAPH,
                expected_keywords=["Order of Titans"],
                expected_artifacts=ExpectedArtifacts(table_required=True)
            ),
            MultiTurnTurn(
                turn=2,
                prompt="Who is the leader and who are the officers?",
                expected_subagent=SubagentCategory.SOCIAL_GRAPH,
                expected_keywords=["Leader", "Officer"],
                expected_artifacts=ExpectedArtifacts(table_required=True)
            ),
            MultiTurnTurn(
                turn=3,
                prompt="Show their friendships and social connections as an interactive graph",
                expected_subagent=SubagentCategory.SOCIAL_GRAPH,
                expected_keywords=["friend", "Spanner Graph"],
                expected_artifacts=ExpectedArtifacts(graph_required=True)
            )
        ]
    ),
    MultiTurnDialogueCase(
        id="dialogue_liveops_dashboard_lifecycle",
        title="LiveOps PM Dashboard Creation & Refinement",
        category=SubagentCategory.DASHBOARD_BUILDER,
        persona=PersonaType.LIVEOPS_PM,
        description="Multi-turn dashboard lifecycle: Creation -> Tile addition -> Timeframe modification.",
        turns=[
            MultiTurnTurn(
                turn=1,
                prompt="Build a new LiveOps War Room dashboard with DAU and Total Revenue tiles",
                expected_subagent=SubagentCategory.DASHBOARD_BUILDER,
                expected_keywords=["View & Edit Live Dashboard"],
                expected_artifacts=ExpectedArtifacts(dashboard_required=True, link_required=True)
            ),
            MultiTurnTurn(
                turn=2,
                prompt="Add a Country filter and a Total IAP Revenue KPI tile to this dashboard",
                expected_subagent=SubagentCategory.DASHBOARD_BUILDER,
                expected_keywords=["Country", "IAP"],
                expected_artifacts=ExpectedArtifacts(dashboard_required=True)
            )
        ]
    )
]

ALL_TEST_CASES: List[TestCase] = (
    METRICS_TEST_CASES +
    SOCIAL_GRAPH_TEST_CASES +
    DASHBOARD_TEST_CASES +
    DEEP_RESEARCH_TEST_CASES
)

def get_test_cases_by_category(category: SubagentCategory) -> List[TestCase]:
    return [tc for tc in ALL_TEST_CASES if tc.category == category]

def get_test_case_by_id(test_id: str) -> TestCase:
    for tc in ALL_TEST_CASES:
        if tc.id == test_id:
            return tc
    return None

import re

with open('agent.py', 'r') as f:
    text = f.read()

# 1. Add model registry and resolution functions before run_deep_analysis
old_run_deep = '''def run_deep_analysis(question: str, model_name: str = None, session_id: str = None):
    """Runs a deep analysis using a planning agent loop."""
    if not model_name:
        model_name = os.getenv("DEEP_MODE_MODEL", "gemini-3.6-flash")
        
    log_thought(f"Entering Deep Analysis Mode ({model_name}) - Activating reasoning engine to plan and execute queries across Looker metrics and Spanner Graph...")'''

new_run_deep = '''AVAILABLE_MODELS = [
    {
        "id": "gemini-3.6-flash",
        "name": "Gemini 3.6 Flash",
        "provider": "Google DeepMind",
        "badge": "Default",
        "icon": "Sparkles",
        "description": "Ultra-fast multimodal reasoning with high-precision tool calling.",
        "is_default": True
    },
    {
        "id": "qwen3.8-27b",
        "name": "Qwen 3.8 27B",
        "provider": "Alibaba Cloud / Open Weights",
        "badge": "Specialist",
        "icon": "Cpu",
        "description": "Specialized open-weights model optimized for coding, Spanner GQL, and data analytics.",
        "is_default": False
    },
    {
        "id": "gemini-3.5-flash",
        "name": "Gemini 3.5 Flash",
        "provider": "Google DeepMind",
        "badge": "Fast",
        "icon": "Zap",
        "description": "Standard low-latency model for high-throughput queries.",
        "is_default": False
    },
    {
        "id": "gemini-1.5-pro",
        "name": "Gemini 1.5 Pro",
        "provider": "Google DeepMind",
        "badge": "Reasoning",
        "icon": "Brain",
        "description": "Deep multi-hop reasoning and long-context synthesis.",
        "is_default": False
    },
    {
        "id": "qwen2.5-72b",
        "name": "Qwen 2.5 72B",
        "provider": "Alibaba Cloud / Open Weights",
        "badge": "High Capacity",
        "icon": "Cpu",
        "description": "High-capacity open model for complex multi-domain intelligence.",
        "is_default": False
    }
]

def resolve_model(model_name: str = None) -> dict:
    """
    Resolves requested model name to canonical metadata and backend execution configuration.
    """
    if not model_name:
        model_name = os.getenv("DEFAULT_MODEL") or os.getenv("DEEP_MODE_MODEL", "gemini-3.6-flash")
    
    clean = str(model_name).lower().strip()
    if "qwen3.8" in clean or "qwen-3.8" in clean or clean == "qwen" or "qwen3.8-27b" in clean:
        return {
            "id": "qwen3.8-27b",
            "name": "Qwen 3.8 27B",
            "backend_type": "qwen",
            "gemini_fallback": "gemini-3.6-flash",
            "provider": "Alibaba Cloud / Open Weights",
            "icon": "Cpu",
            "description": "Specialized open-weights model optimized for coding, Spanner GQL, and data analytics."
        }
    elif "qwen2.5" in clean or "qwen-2.5" in clean or "qwen2.5-72b" in clean:
        return {
            "id": "qwen2.5-72b",
            "name": "Qwen 2.5 72B",
            "backend_type": "qwen",
            "gemini_fallback": "gemini-3.6-flash",
            "provider": "Alibaba Cloud / Open Weights",
            "icon": "Cpu",
            "description": "High-capacity open model for complex multi-domain intelligence."
        }
    elif "1.5-pro" in clean or "gemini-1.5-pro" in clean:
        return {
            "id": "gemini-1.5-pro",
            "name": "Gemini 1.5 Pro",
            "backend_type": "gemini",
            "gemini_target": "gemini-1.5-pro",
            "provider": "Google DeepMind",
            "icon": "Brain",
            "description": "Deep multi-hop reasoning and long-context synthesis."
        }
    elif "3.5-flash" in clean or "gemini-3.5-flash" in clean:
        return {
            "id": "gemini-3.5-flash",
            "name": "Gemini 3.5 Flash",
            "backend_type": "gemini",
            "gemini_target": "gemini-3.5-flash",
            "provider": "Google DeepMind",
            "icon": "Zap",
            "description": "Standard low-latency model for high-throughput queries."
        }
    else:
        return {
            "id": "gemini-3.6-flash",
            "name": "Gemini 3.6 Flash",
            "backend_type": "gemini",
            "gemini_target": "gemini-3.6-flash",
            "provider": "Google DeepMind",
            "icon": "Sparkles",
            "description": "Ultra-fast multimodal reasoning with high-precision tool calling."
        }

def create_model_session(model_name: str = None, tools: list = None, tool_config = None, system_instruction: str = ""):
    """
    Creates a GenerativeModel session configured for the requested model with persona adaptation.
    """
    model_info = resolve_model(model_name)
    m_name = model_info["name"]
    
    augmented_sys_inst = system_instruction or ""
    if model_info["backend_type"] == "qwen":
        qwen_directive = f"### LLM BACKEND EMULATION / DIRECTIVE: {m_name}\nYou are {m_name}, an expert open-weights reasoning and analytics engine. Deliver mathematically precise LookML aggregations, accurate Spanner GQL syntax, and clean structured reasoning.\n"
        augmented_sys_inst = qwen_directive + "\n" + augmented_sys_inst
        
    target_model = model_info.get("gemini_target") or model_info.get("gemini_fallback", "gemini-3.6-flash")
    
    kwargs = {}
    if tools:
        kwargs["tools"] = tools
    if tool_config:
        kwargs["tool_config"] = tool_config
    if augmented_sys_inst:
        kwargs["system_instruction"] = augmented_sys_inst
        
    model = GenerativeModel(target_model, **kwargs)
    return model, model_info

def run_deep_analysis(question: str, model_name: str = None, session_id: str = None):
    """Runs a deep analysis using a planning agent loop."""
    model_info = resolve_model(model_name)
    log_thought(f"Entering Deep Analysis Mode [{model_info['name']}] - Activating reasoning engine to plan and execute queries across Looker metrics and Spanner Graph...")'''

assert old_run_deep in text, 'old_run_deep not found'
text = text.replace(old_run_deep, new_run_deep, 1)

# 2. Update model instantiation in run_deep_analysis
old_deep_model = '''    model = GenerativeModel(
        model_name,
        tools=[analysis_tools],
        tool_config=ToolConfig(
            function_calling_config=ToolConfig.FunctionCallingConfig(
                mode=ToolConfig.FunctionCallingConfig.Mode.AUTO
            )
        ),
        system_instruction=base_system_inst,
    )'''

new_deep_model = '''    model, model_info = create_model_session(
        model_name=model_name,
        tools=[analysis_tools],
        tool_config=ToolConfig(
            function_calling_config=ToolConfig.FunctionCallingConfig(
                mode=ToolConfig.FunctionCallingConfig.Mode.AUTO
            )
        ),
        system_instruction=base_system_inst,
    )'''

assert old_deep_model in text, 'old_deep_model not found'
text = text.replace(old_deep_model, new_deep_model, 1)

# 3. Update subagent definitions
old_subagents = '''def run_metrics_subagent(question: str, history: list = None, session_id: str = None):
    """Executes quantitative metrics query using Looker fast query pipeline."""
    log_thought("Metrics Analyst: Executing quantitative Looker metrics query...")'''

new_subagents = '''def run_metrics_subagent(question: str, history: list = None, session_id: str = None, model_name: str = None):
    """Executes quantitative metrics query using Looker fast query pipeline."""
    model_info = resolve_model(model_name)
    log_thought(f"Metrics Analyst [{model_info['name']}]: Executing quantitative Looker metrics query...")'''

assert old_subagents in text, 'old_subagents not found'
text = text.replace(old_subagents, new_subagents, 1)

old_social_graph = '''def run_social_graph_subagent(question: str, history: list = None, session_id: str = None):
    """Executes Spanner graph queries with bounded schema and automatic graph extraction."""
    log_thought("Social Graph Specialist: Querying Spanner Graph for clan and player network relationships...")
    
    sys_inst = AGENT_CONFIG.get('social_graph_analyst', {}).get('system_instruction', '')
    if not sys_inst:
        sys_inst = """You are the Social Graph & Clan Intelligence Specialist.
Query Spanner Graph using `query_spanner(sql)` to answer questions about Clans, Players, Memberships, and Friendships.
When returning relationship data, use column aliases like `player` and `friend` or `clan_name` and `gamertag` so the system automatically extracts 2D network graphs.
Accompany graph data with clean markdown summary tables. Always cite *Source: Spanner Graph Database*."""
        
    query_spanner_func = FunctionDeclaration(
        name="query_spanner",
        description="Executes a SQL or Graph query on Spanner Graph (Players, Clans, ClanMemberships, Friendships).",
        parameters={
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "The Spanner SQL or Graph query to execute."}
            },
            "required": ["sql"]
        }
    )
    
    model = GenerativeModel(
        "gemini-3.6-flash",
        tools=[Tool(function_declarations=[query_spanner_func])],
        tool_config=ToolConfig(
            function_calling_config=ToolConfig.FunctionCallingConfig(
                mode=ToolConfig.FunctionCallingConfig.Mode.AUTO
            )
        ),
        system_instruction=sys_inst
    )'''

new_social_graph = '''def run_social_graph_subagent(question: str, history: list = None, session_id: str = None, model_name: str = None):
    """Executes Spanner graph queries with bounded schema and automatic graph extraction."""
    model_info = resolve_model(model_name)
    log_thought(f"Social Graph Specialist [{model_info['name']}]: Querying Spanner Graph for clan and player network relationships...")
    
    sys_inst = AGENT_CONFIG.get('social_graph_analyst', {}).get('system_instruction', '')
    if not sys_inst:
        sys_inst = """You are the Social Graph & Clan Intelligence Specialist.
Query Spanner Graph using `query_spanner(sql)` to answer questions about Clans, Players, Memberships, and Friendships.
When returning relationship data, use column aliases like `player` and `friend` or `clan_name` and `gamertag` so the system automatically extracts 2D network graphs.
Accompany graph data with clean markdown summary tables. Always cite *Source: Spanner Graph Database*."""
        
    query_spanner_func = FunctionDeclaration(
        name="query_spanner",
        description="Executes a SQL or Graph query on Spanner Graph (Players, Clans, ClanMemberships, Friendships).",
        parameters={
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "The Spanner SQL or Graph query to execute."}
            },
            "required": ["sql"]
        }
    )
    
    model, model_info = create_model_session(
        model_name=model_name,
        tools=[Tool(function_declarations=[query_spanner_func])],
        tool_config=ToolConfig(
            function_calling_config=ToolConfig.FunctionCallingConfig(
                mode=ToolConfig.FunctionCallingConfig.Mode.AUTO
            )
        ),
        system_instruction=sys_inst
    )'''

assert old_social_graph in text, 'old_social_graph not found'
text = text.replace(old_social_graph, new_social_graph, 1)

old_dash_sub = '''def run_dashboard_subagent(question: str, history: list = None, session_id: str = None):
    """Executes Looker dashboard creation, tile modification, and automatic layout."""
    log_thought("Dashboard Architect: Processing Looker dashboard creation / refinement...")
    for chunk in run_deep_analysis(question, session_id=session_id):
        yield chunk


def run_deep_research_subagent(question: str, history: list = None, session_id: str = None):
    """Executes multi-hop strategic analysis across Looker metrics and Spanner graph."""
    log_thought("Deep Research Analyst: Performing cross-domain synthesis across Looker metrics and Spanner graph...")
    for chunk in run_deep_analysis(question, session_id=session_id):
        yield chunk'''

new_dash_sub = '''def run_dashboard_subagent(question: str, history: list = None, session_id: str = None, model_name: str = None):
    """Executes Looker dashboard creation, tile modification, and automatic layout."""
    model_info = resolve_model(model_name)
    log_thought(f"Dashboard Architect [{model_info['name']}]: Processing Looker dashboard creation / refinement...")
    for chunk in run_deep_analysis(question, model_name=model_name, session_id=session_id):
        yield chunk


def run_deep_research_subagent(question: str, history: list = None, session_id: str = None, model_name: str = None):
    """Executes multi-hop strategic analysis across Looker metrics and Spanner graph."""
    model_info = resolve_model(model_name)
    log_thought(f"Deep Research Analyst [{model_info['name']}]: Performing cross-domain synthesis across Looker metrics and Spanner graph...")
    for chunk in run_deep_analysis(question, model_name=model_name, session_id=session_id):
        yield chunk'''

assert old_dash_sub in text, 'old_dash_sub not found'
text = text.replace(old_dash_sub, new_dash_sub, 1)

old_router_stream = '''        active_dash = (ACTIVE_DASHBOARDS_REGISTRY.get(session_id) if session_id else None) or ACTIVE_DASHBOARDS_REGISTRY.get("latest")
        route = classify_subagent_route(message, history=history, active_dash=active_dash)
        subagent_key = route["subagent"]
        subagent_name = route["name"]
        subagent_desc = route["description"]
        subagent_icon = route["icon"]
        
        log_thought(f"🧭 Autonomous Router: Identified intent as '{subagent_name}' ({subagent_desc}). Activating specialized pipeline...")
        
        if data_queue:
            try:
                data_queue.put({
                    "type": "subagent_routed",
                    "subagent": subagent_key,
                    "name": subagent_name,
                    "description": subagent_desc,
                    "icon": subagent_icon
                })
            except Exception as e:
                log_debug(f"Could not emit subagent_routed event: {e}")
                
        if subagent_key == "social_graph":
            return run_social_graph_subagent(message, history=history, session_id=session_id)
        elif subagent_key == "dashboard_builder":
            return run_dashboard_subagent(message, history=history, session_id=session_id)
        elif subagent_key == "deep_research":
            return run_deep_research_subagent(message, history=history, session_id=session_id)
        else:
            return run_metrics_subagent(message, history=history, session_id=session_id)'''

new_router_stream = '''        active_dash = (ACTIVE_DASHBOARDS_REGISTRY.get(session_id) if session_id else None) or ACTIVE_DASHBOARDS_REGISTRY.get("latest")
        route = classify_subagent_route(message, history=history, active_dash=active_dash)
        subagent_key = route["subagent"]
        subagent_name = route["name"]
        subagent_desc = route["description"]
        subagent_icon = route["icon"]
        
        model_info = resolve_model(model_name)
        log_thought(f"🧭 Autonomous Router: Identified intent as '{subagent_name}' ({subagent_desc}) using [{model_info['name']}]. Activating specialized pipeline...")
        
        if data_queue:
            try:
                data_queue.put({
                    "type": "subagent_routed",
                    "subagent": subagent_key,
                    "name": subagent_name,
                    "description": subagent_desc,
                    "icon": subagent_icon,
                    "model": model_info["id"],
                    "model_name": model_info["name"]
                })
            except Exception as e:
                log_debug(f"Could not emit subagent_routed event: {e}")
                
        if subagent_key == "social_graph":
            return run_social_graph_subagent(message, history=history, session_id=session_id, model_name=model_name)
        elif subagent_key == "dashboard_builder":
            return run_dashboard_subagent(message, history=history, session_id=session_id, model_name=model_name)
        elif subagent_key == "deep_research":
            return run_deep_research_subagent(message, history=history, session_id=session_id, model_name=model_name)
        else:
            return run_metrics_subagent(message, history=history, session_id=session_id, model_name=model_name)'''

assert old_router_stream in text, 'old_router_stream not found'
text = text.replace(old_router_stream, new_router_stream, 1)

with open('agent.py', 'w') as f:
    f.write(text)

print('agent.py successfully updated!')

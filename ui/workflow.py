# ui/workflow.py
import streamlit as st
import graphviz

def render():
    st.subheader("📐 Project Workflow")

    dot = graphviz.Digraph("workflow", graph_attr={
        "rankdir": "LR",
        "splines": "spline",
        "fontsize": "10",
        "labelloc": "t",
        "pad": "0.2",
    })

    # Styles
    cluster_style = {"style": "rounded", "color": "#888", "penwidth": "1"}
    node_style = {"shape": "box", "style": "rounded,filled", "fillcolor": "#1f2937", "color": "#374151", "fontcolor": "white"}

    # ── Sources ───────────────────────────────────────────────────────────
    with dot.subgraph(name="cluster_sources") as c:
        c.attr(label="Sources", **cluster_style)
        c.node("scrapingdog", "ScrapingDog API\n(extraction.py)", **node_style)
        c.node("demo", "Demo / Upload\n(JSON/CSV)", **node_style)
        c.node("synthetic", "Synthetic Generator\n(from teste.json)", **node_style)

    # ── Processing ────────────────────────────────────────────────────────
    with dot.subgraph(name="cluster_processing") as c:
        c.attr(label="Processing (ui/data_processing.py)", **cluster_style)
        c.node("normalize", "normalize_enhanced_columns()\n• flatten extracted_info → enhanced_*", **node_style)
        c.node("quality", "apply_quality_normalization()\n• location fix & typos\n• type → {remote|on-site|hybrid}\n• split natural/programming\n• tool synonyms\n• unknowns → CSV", **node_style)

    # ── Storage & Config ──────────────────────────────────────────────────
    with dot.subgraph(name="cluster_storage") as c:
        c.attr(label="Storage & Config", **cluster_style)
        c.node("exports", "exports/\n• li_jobs_*.csv\n• li_jobs_*.json", **node_style)
        c.node("unknowns", "exports/unknowns/\n• languages_unknown.csv\n• tools_unknown.csv", **node_style)
        c.node("config", "ui/config.py\n• synonyms\n• thresholds\n• Top-N\n• columns", **node_style)

    # ── UI ────────────────────────────────────────────────────────────────
    with dot.subgraph(name="cluster_ui") as c:
        c.attr(label="UI (streamlit_app.py)", **cluster_style)
        c.node("explore", "Explore (table)\ncomponents.py", **node_style)
        c.node("insights", "Insights (cards)\nvisualization.py", **node_style)
        c.node("graphs", "Graphs (mini-tabs)\nui/graphs.py", **node_style)

    # ── Edges ─────────────────────────────────────────────────────────────
    dot.edge("scrapingdog", "normalize", label="JSON rows")
    dot.edge("demo", "normalize", label="CSV/JSON")
    dot.edge("synthetic", "normalize", label="200+ rows")

    dot.edge("normalize", "quality")
    dot.edge("config", "quality", label="rules & vocab", fontsize="9")

    dot.edge("quality", "exports", label="clean DataFrame → CSV/JSON")
    dot.edge("quality", "unknowns", label="unmapped tokens")

    # Same cleaned df flows into UI tabs
    dot.edge("quality", "explore", label="df")
    dot.edge("quality", "insights", label="df")
    dot.edge("quality", "graphs", label="df")

    st.graphviz_chart(dot, use_container_width=True)

def render_page():
    render()

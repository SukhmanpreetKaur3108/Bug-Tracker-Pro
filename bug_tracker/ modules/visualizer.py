"""
modules/visualizer.py  —  Plotly Visualization Module
======================================================
All chart-generating functions used by the Analytics Dashboard.
Returns Plotly figure objects that Streamlit renders with st.plotly_chart().
"""

import plotly.graph_objects as go
import plotly.express as px
from collections import Counter
from datetime import datetime

# Colour palette — consistent across all charts
_PALETTE = {
    "Open":        "#2980B9",
    "In Progress": "#8E44AD",
    "Resolved":    "#27AE60",
    "Closed":      "#95A5A6",
    "Low":         "#27AE60",
    "Medium":      "#F39C12",
    "High":        "#E67E22",
    "Critical":    "#E74C3C",
}


# ---------------------------------------------------------------------------
# Status doughnut chart
# ---------------------------------------------------------------------------

def status_donut(bugs: list) -> go.Figure:
    """Doughnut chart of bugs grouped by status."""
    counts = Counter(b["status"] for b in bugs)
    labels = list(counts.keys())
    values = list(counts.values())
    colours = [_PALETTE.get(l, "#BDC3C7") for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.55,
        marker=dict(colors=colours, line=dict(color="#ffffff", width=2)),
        textinfo="label+percent",
    ))
    fig.update_layout(
        title="Bugs by Status",
        showlegend=True,
        margin=dict(t=40, b=10, l=10, r=10),
        height=320,
    )
    return fig


# ---------------------------------------------------------------------------
# Severity bar chart
# ---------------------------------------------------------------------------

def severity_bar(bugs: list) -> go.Figure:
    """Horizontal bar chart of bugs grouped by severity."""
    order = ["Critical", "High", "Medium", "Low"]
    counts = Counter(b["severity"] for b in bugs)
    values = [counts.get(s, 0) for s in order]
    colours = [_PALETTE.get(s, "#BDC3C7") for s in order]

    fig = go.Figure(go.Bar(
        x=values, y=order,
        orientation="h",
        marker_color=colours,
        text=values, textposition="outside",
    ))
    fig.update_layout(
        title="Bugs by Severity",
        xaxis_title="Count",
        margin=dict(t=40, b=20, l=10, r=20),
        height=280,
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#EAECEE"),
    )
    return fig


# ---------------------------------------------------------------------------
# Priority score scatter plot
# ---------------------------------------------------------------------------

def priority_scatter(bugs: list) -> go.Figure:
    """Scatter plot: priority score vs. days open, coloured by severity."""
    if not bugs:
        return go.Figure()

    now = datetime.utcnow()
    x_vals, y_vals, labels, colours, hovers = [], [], [], [], []

    for b in bugs:
        try:
            created = datetime.strptime(b["created_at"], "%Y-%m-%dT%H:%M:%S")
            age = max((now - created).days, 0)
        except Exception:
            age = 0

        x_vals.append(age)
        y_vals.append(b.get("priority_score", 0))
        labels.append(f"#{b['id']}: {b['title'][:30]}")
        colours.append(_PALETTE.get(b.get("severity", ""), "#BDC3C7"))
        hovers.append(
            f"<b>#{b['id']}</b> {b['title']}<br>"
            f"Severity: {b['severity']}<br>"
            f"Score: {b.get('priority_score', 0)}<br>"
            f"Age: {age} days"
        )

    fig = go.Figure(go.Scatter(
        x=x_vals, y=y_vals,
        mode="markers+text",
        text=labels,
        textposition="top center",
        marker=dict(color=colours, size=12, line=dict(color="white", width=1)),
        hovertext=hovers,
        hoverinfo="text",
    ))
    fig.update_layout(
        title="Priority Score vs. Age (days)",
        xaxis_title="Days Since Reported",
        yaxis_title="Priority Score (0–100)",
        height=380,
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#EAECEE"),
        yaxis=dict(showgrid=True, gridcolor="#EAECEE", range=[0, 105]),
    )
    return fig


# ---------------------------------------------------------------------------
# Bug timeline (Gantt-style)
# ---------------------------------------------------------------------------

def bug_timeline(bugs: list) -> go.Figure:
    """
    Gantt-style timeline showing each bug from creation to last update.
    Colour-coded by current status.
    """
    if not bugs:
        return go.Figure()

    sorted_bugs = sorted(bugs, key=lambda b: b.get("created_at", ""), reverse=True)[:20]

    fig = go.Figure()
    for b in sorted_bugs:
        try:
            start = datetime.strptime(b["created_at"], "%Y-%m-%dT%H:%M:%S")
            end   = datetime.strptime(b["updated_at"], "%Y-%m-%dT%H:%M:%S")
            if start == end:
                end = datetime.utcnow() if b["status"] != "Closed" else end
        except Exception:
            continue

        label = f"#{b['id']} {b['title'][:25]}"
        colour = _PALETTE.get(b["status"], "#BDC3C7")

        fig.add_trace(go.Bar(
            x=[(end - start).total_seconds() / 3600],   # hours
            y=[label],
            orientation="h",
            base=[(start - datetime(2026, 1, 1)).total_seconds() / 3600],
            marker_color=colour,
            hovertext=f"Status: {b['status']} | Score: {b.get('priority_score', 0)}",
            hoverinfo="text",
            showlegend=False,
        ))

    fig.update_layout(
        title="Bug Timeline (last 20 bugs, hover for details)",
        barmode="overlay",
        height=max(300, len(sorted_bugs) * 28 + 60),
        xaxis_title="Hours since Jan 1 2026",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#EAECEE"),
        margin=dict(l=200, r=20, t=40, b=30),
    )
    return fig


# ---------------------------------------------------------------------------
# Module clustering bar chart
# ---------------------------------------------------------------------------

def module_cluster_chart(clusters: dict) -> go.Figure:
    """Bar chart of bug counts per software module."""
    modules = list(clusters.keys())
    counts  = [len(v) for v in clusters.values()]

    fig = go.Figure(go.Bar(
        x=modules, y=counts,
        marker_color="#2980B9",
        text=counts, textposition="outside",
    ))
    fig.update_layout(
        title="Module-wise Bug Distribution",
        xaxis_title="Module",
        yaxis_title="Bug Count",
        height=320,
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=True, gridcolor="#EAECEE"),
    )
    return fig


# ---------------------------------------------------------------------------
# Trend line — bugs reported per day
# ---------------------------------------------------------------------------

def daily_trend(bugs: list) -> go.Figure:
    """Line chart of bugs reported per day over the last 30 days."""
    from collections import defaultdict
    daily = defaultdict(int)
    for b in bugs:
        day = b.get("created_at", "")[:10]
        if day:
            daily[day] += 1

    if not daily:
        return go.Figure()

    sorted_days = sorted(daily.keys())
    counts = [daily[d] for d in sorted_days]

    fig = go.Figure(go.Scatter(
        x=sorted_days, y=counts,
        mode="lines+markers",
        line=dict(color="#2980B9", width=2),
        marker=dict(size=7, color="#2980B9"),
        fill="tozeroy",
        fillcolor="rgba(41,128,185,0.1)",
    ))
    fig.update_layout(
        title="Daily Bug Reports",
        xaxis_title="Date",
        yaxis_title="Bugs Reported",
        height=280,
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#EAECEE"),
        yaxis=dict(showgrid=True, gridcolor="#EAECEE"),
    )
    return fig

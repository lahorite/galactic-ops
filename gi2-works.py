# app.py — Galactic Operations Dashboard (Plotly Gauges)
import time
from datetime import datetime
import random
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Galactic Ops Dashboard", page_icon="🛰️", layout="wide")

# -----------------------------
# Settings
# -----------------------------
st.title("🛰️ Galactic Operations Dashboard")
st.caption("Health panel for a single spacecraft — fuel, solar, battery, thermal, and comms (with Plotly gauges)")

with st.sidebar:
    st.header("Simulation Controls")
    autoupdate = st.toggle("Auto-update every 2 sec", value=False)
    jitter = st.slider("Telemetry jitter (%)", 0, 10, 2)
    st.divider()
    st.header("Alert Thresholds")
    th_fuel = st.slider("Fuel low threshold", 0, 100, 25)
    th_batt = st.slider("Battery low threshold", 0, 100, 30)
    th_solar = st.slider("Solar output low threshold (kW)", 0, 200, 60)
    th_temp_hi = st.slider("Coolant temp HIGH (°C)", 40, 200, 120)
    th_comm = st.selectbox("Comms minimum status", ["Outage","Degraded","Nominal"], index=1)

# -----------------------------
# Telemetry (demo)
# -----------------------------
@st.cache_data(show_spinner=False)
def initial_state():
    return {
        "ship": "GI-01 ORION",
        "fuel_pct": 76.0,
        "battery_pct": 88.0,
        "solar_kw": 95.0,
        "coolant_c": 87.0,
        "comms": "Nominal",
    }

state = initial_state().copy()

def apply_jitter(val, pct):
    if pct <= 0: return val
    span = val * pct / 100.0
    return max(0, val + random.uniform(-span, span))

state["fuel_pct"] = round(apply_jitter(state["fuel_pct"], jitter), 1)
state["battery_pct"] = round(apply_jitter(state["battery_pct"], jitter), 1)
state["solar_kw"] = round(apply_jitter(state["solar_kw"], jitter), 1)
state["coolant_c"] = round(apply_jitter(state["coolant_c"], jitter), 1)
state["comms"] = random.choice(["Nominal","Nominal","Nominal","Degraded"])  # biased toward Nominal

# Derived metric: map solar (0–200 kW) to 0–100 scale for a dial, and thermal margin
solar_pct = max(0, min(100, (state["solar_kw"] / 200.0) * 100.0))
thermal_margin = max(0, min(100, 200.0 - state["coolant_c"]))  # 200°C = 0 margin, 100% = cool

# -----------------------------
# Plotly Gauge helpers
# -----------------------------
def radial_gauge(title: str, value: float, vmin: float = 0, vmax: float = 100,
                 red_max: float | None = None, yellow_max: float | None = None,
                 units: str = "%", threshold: float | None = None):
    """Make a pretty radial gauge with green/yellow/red bands and a threshold marker."""
    steps = []
    # Bands: green -> yellow -> red (optional if provided)
    if yellow_max is not None:
        steps.append(dict(range=[vmin, yellow_max], color="#2ecc71"))
    if red_max is not None and yellow_max is not None:
        steps.append(dict(range=[yellow_max, red_max], color="#f1c40f"))
        steps.append(dict(range=[red_max, vmax], color="#e74c3c"))
    else:
        steps.append(dict(range=[vmin, vmax], color="#2ecc71"))

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={'suffix': f" {units}"},
        title={'text': f"<b>{title}</b>"},
        gauge={
            'axis': {'range': [vmin, vmax]},
            'bar': {'color': "#1f77b4"},
            'steps': [{'range': s['range'], 'color': s['color']} for s in steps],
            'threshold': ({
                'line': {'color': "#8e44ad", 'width': 4},
                'thickness': 0.75,
                'value': threshold
            } if threshold is not None else None)
        }
    ))
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=260)
    return fig

def bullet_gauge(title: str, value: float, vmin: float, vmax: float, zones: list[tuple[float, float, str]]):
    """Horizontal bullet gauge for categorical/quality signals (e.g., comms)."""
    shapes = []
    for low, high, color in zones:
        shapes.append(dict(type="rect", x0=low, x1=high, y0=0, y1=1, fillcolor=color, line=dict(width=0)))
    fig = go.Figure()
    fig.add_shape(type="line", x0=vmin, x1=value, y0=0.5, y1=0.5, line=dict(width=14))
    for s in shapes:
        fig.add_shape(**s)
    fig.update_xaxes(range=[vmin, vmax], showgrid=False, ticks="", showticklabels=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(
        title=f"<b>{title}</b> — {value:.0f}%",
        margin=dict(l=10, r=10, t=50, b=10),
        height=120
    )
    return fig

# -----------------------------
# Top KPIs (numbers)
# -----------------------------
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("⛽ Fuel", f"{state['fuel_pct']} %")
k2.metric("🔋 Battery", f"{state['battery_pct']} %")
k3.metric("☀️ Solar Output", f"{state['solar_kw']} kW")
k4.metric("❄️ Coolant Temp", f"{state['coolant_c']} °C")
k5.metric("📡 Comms", state["comms"])
st.divider()

# -----------------------------
# Snapshot chart
# -----------------------------
left, right = st.columns([2, 1])
with left:
    st.markdown("#### Systems Snapshot")
    if "ts_hist" not in st.session_state:
        st.session_state.ts_hist = pd.DataFrame(columns=["t","Fuel%","Battery%","Solar(kW)","Coolant(°C)"])
    st.session_state.ts_hist = pd.concat([st.session_state.ts_hist, pd.DataFrame([{
        "t": datetime.utcnow().strftime("%H:%M:%S"),
        "Fuel%": state["fuel_pct"],
        "Battery%": state["battery_pct"],
        "Solar(kW)": state["solar_kw"],
        "Coolant(°C)": state["coolant_c"],
    }])], ignore_index=True)
    st.line_chart(st.session_state.ts_hist.set_index("t"))

# -----------------------------
# Plotly Gauges (right column)
# -----------------------------
with right:
    st.markdown("#### Gauges")
    gcol1, gcol2 = st.columns(2)

    with gcol1:
        st.plotly_chart(
            radial_gauge("Fuel", state["fuel_pct"], 0, 100, red_max=30, yellow_max=60, units="%", threshold=th_fuel),
            use_container_width=True
        )
        st.plotly_chart(
            radial_gauge("Solar (scaled)", solar_pct, 0, 100, red_max=30, yellow_max=60, units="%", threshold=(th_solar/200)*100),
            use_container_width=True
        )

    with gcol2:
        st.plotly_chart(
            radial_gauge("Battery", state["battery_pct"], 0, 100, red_max=30, yellow_max=60, units="%", threshold=th_batt),
            use_container_width=True
        )
        st.plotly_chart(
            radial_gauge("Thermal Margin", thermal_margin, 0, 100, red_max=30, yellow_max=60, units="%", threshold=(200 - th_temp_hi)),
            use_container_width=True
        )

    # Comms bullet gauge (Nominal/Degraded/Outage → 100/50/0)
    comm_val = {"Nominal": 100, "Degraded": 50, "Outage": 0}[state["comms"]]
    comm_min_required = {"Outage": 0, "Degraded": 50, "Nominal": 100}[th_comm]
    st.plotly_chart(
        bullet_gauge(
            f"Comms (min {th_comm})",
            comm_val, 0, 100,
            zones=[(0, 33, "#e74c3c"), (33, 67, "#f1c40f"), (67, 100, "#2ecc71")]
        ),
        use_container_width=True
    )
    if comm_val < comm_min_required:
        st.warning(f"Comms below minimum: {state['comms']} < {th_comm}")

# -----------------------------
# Alerts
# -----------------------------
def status_bad():
    msgs = []
    if state["fuel_pct"] <= th_fuel: msgs.append(f"Fuel low: {state['fuel_pct']}% ≤ {th_fuel}%")
    if state["battery_pct"] <= th_batt: msgs.append(f"Battery low: {state['battery_pct']}% ≤ {th_batt}%")
    if state["solar_kw"] <= th_solar: msgs.append(f"Solar output low: {state['solar_kw']} kW ≤ {th_solar} kW")
    if state["coolant_c"] >= th_temp_hi: msgs.append(f"Coolant temp high: {state['coolant_c']} °C ≥ {th_temp_hi} °C")
    comm_order = {"Outage":0,"Degraded":1,"Nominal":2}
    if comm_order[state["comms"]] < comm_order[th_comm]:
        msgs.append(f"Comms below minimum: {state['comms']} < {th_comm}")
    return msgs

issues = status_bad()
if issues:
    st.error("⚠️ Alerts detected:\n- " + "\n- ".join(issues))
else:
    st.success("All systems nominal.")

# -----------------------------
# Auto-update loop (optional)
# -----------------------------
if autoupdate:
    time.sleep(2)
    st.rerun()


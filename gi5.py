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
st.caption("Health panel for a single spacecraft — fuel, solar, battery, thermal, and comms (with Plotly charts)")

with st.sidebar:
    st.header("Simulation Controls")
    autoupdate = st.toggle("Auto-update every 3 sec", value=False)
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

# live jitter for demo
state["fuel_pct"] = round(apply_jitter(state["fuel_pct"], jitter), 1)
state["battery_pct"] = round(apply_jitter(state["battery_pct"], jitter), 1)
state["solar_kw"] = round(apply_jitter(state["solar_kw"], jitter), 1)
state["coolant_c"] = round(apply_jitter(state["coolant_c"], jitter), 1)
state["comms"] = random.choice(["Nominal","Nominal","Nominal","Degraded"])  # biased toward Nominal

# Derived metric: map solar (0–200 kW) to 0–100 scale for dial, and thermal margin
solar_pct = max(0, min(100, (state["solar_kw"] / 200.0) * 100.0))
thermal_margin = max(0, min(100, 200.0 - state["coolant_c"]))  # 200°C = 0 margin, 100% = cool

# -----------------------------
# Plotly Gauge helper
# -----------------------------
def radial_gauge(title: str, value: float, vmin: float = 0, vmax: float = 100,
                 red_max: float | None = None, yellow_max: float | None = None,
                 units: str = "%", threshold: float | None = None):
    steps = []
    # color bands
    if yellow_max is not None:
        steps.append(dict(range=[vmin, yellow_max], color="#2ecc71"))
    if red_max is not None and yellow_max is not None:
        steps.append(dict(range=[yellow_max, red_max], color="#f1c40f"))
        steps.append(dict(range=[red_max, vmax], color="#e74c3c"))
    if not steps:
        steps.append(dict(range=[vmin, vmax], color="#2ecc71"))

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={'suffix': f" {units}"},
        title={'text': f"<b>{title}</b>"},
        gauge={
            'axis': {'range': [vmin, vmax]},
            'bar': {'color': "#1f77b4"},
            'steps': steps,
            'threshold': ({
                'line': {'color': "#8e44ad", 'width': 4},
                'thickness': 0.75,
                'value': threshold
            } if threshold is not None else None)
        }
    ))
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=260)
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
# Time Series (Plotly LINE)
# -----------------------------
st.markdown("### 📈 Realtime Trends (Line)")
if "ts_hist" not in st.session_state:
    st.session_state.ts_hist = pd.DataFrame(columns=[
        "t","Fuel%","Battery%","Solar%","ThermalMargin%"
    ])

st.session_state.ts_hist = pd.concat([st.session_state.ts_hist, pd.DataFrame([{
    "t": datetime.utcnow().strftime("%H:%M:%S"),
    "Fuel%": state["fuel_pct"],
    "Battery%": state["battery_pct"],
    "Solar%": round(solar_pct, 1),
    "ThermalMargin%": round(thermal_margin, 1),
}])], ignore_index=True)

fig_line = go.Figure()
for col in ["Fuel%","Battery%","Solar%","ThermalMargin%"]:
    fig_line.add_trace(go.Scatter(
        x=st.session_state.ts_hist["t"],
        y=st.session_state.ts_hist[col],
        mode="lines+markers",
        name=col
    ))
fig_line.update_layout(
    height=350,
    margin=dict(l=10, r=10, t=30, b=10),
    yaxis_title="Percent",
    xaxis_title="UTC Time"
)
st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# -----------------------------
# Snapshot (Plotly BAR + PIE)
# -----------------------------
st.markdown("### 📊 Snapshot")

colA, colB, colC = st.columns([2,1,1])

# BAR: current % metrics side-by-side
with colA:
    bar_fig = go.Figure(data=[
        go.Bar(name="Fuel%", x=["Fuel"], y=[state["fuel_pct"]]),
        go.Bar(name="Battery%", x=["Battery"], y=[state["battery_pct"]]),
        go.Bar(name="Solar%", x=["Solar"], y=[solar_pct]),
        go.Bar(name="ThermalMargin%", x=["Thermal"], y=[thermal_margin]),
    ])
    bar_fig.update_layout(
        barmode="group",
        height=350,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis=dict(range=[0, 100], title="Percent")
    )
    st.plotly_chart(bar_fig, use_container_width=True)

# PIE: Fuel remaining vs consumed
with colB:
    fuel_pie = go.Figure(data=[go.Pie(
        labels=["Remaining","Consumed"],
        values=[state["fuel_pct"], max(0, 100 - state["fuel_pct"])],
        hole=0.45
    )])
    fuel_pie.update_layout(title="Fuel", height=350, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fuel_pie, use_container_width=True)

# PIE: Battery remaining vs empty
with colC:
    batt_pie = go.Figure(data=[go.Pie(
        labels=["SOC","Empty"],
        values=[state["battery_pct"], max(0, 100 - state["battery_pct"])],
        hole=0.45
    )])
    batt_pie.update_layout(title="Battery", height=350, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(batt_pie, use_container_width=True)

st.divider()

# -----------------------------
# Gauges (Plotly radial)
# -----------------------------
st.markdown("### 🧭 Gauges")

g1, g2 = st.columns(2)
with g1:
    st.plotly_chart(
        radial_gauge("Fuel", state["fuel_pct"], 0, 100, red_max=30, yellow_max=60, units="%", threshold=th_fuel),
        use_container_width=True
    )
    st.plotly_chart(
        radial_gauge("Battery", state["battery_pct"], 0, 100, red_max=30, yellow_max=60, units="%", threshold=th_batt),
        use_container_width=True
    )
with g2:
    st.plotly_chart(
        radial_gauge("Solar (scaled)", solar_pct, 0, 100, red_max=30, yellow_max=60, units="%", threshold=(th_solar/200)*100),
        use_container_width=True
    )
    st.plotly_chart(
        radial_gauge("Thermal Margin", thermal_margin, 0, 100, red_max=30, yellow_max=60, units="%", threshold=(200 - th_temp_hi)),
        use_container_width=True
    )

st.divider()

# -----------------------------
# Alerts (black background + green text + blinking cursor)
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

# Inject blinking cursor CSS
st.markdown("""
<style>
.terminal {
    background-color: #000;
    color: #00FF00;
    font-family: 'Courier New', monospace;
    padding: 15px;
    border-radius: 8px;
    border: 1px solid #00FF00;
    font-size: 16px;
}
@keyframes blink {
    0%, 49% { opacity: 1; }
    50%, 100% { opacity: 0; }
}
.cursor {
    display: inline-block;
    width: 10px;
    height: 1em;
    background: #00FF00;
    margin-left: 4px;
    animation: blink 1s step-start infinite;
}
</style>
""", unsafe_allow_html=True)

issues = status_bad()
if issues:
    alert_html = f"""
    <div class="terminal">
        <b>⚠️ ALERTS DETECTED</b><br>
        {"<br>".join(f"- {msg}" for msg in issues)}
    </div>
    """
else:
    alert_html = """
    <div class="terminal">
        ✅ All systems nominal<span class="cursor"></span>
    </div>
    """

st.markdown(alert_html, unsafe_allow_html=True)

# -----------------------------
# Auto-update loop
# -----------------------------
if autoupdate:
    time.sleep(3)
    st.rerun()


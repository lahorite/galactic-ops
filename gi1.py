# app.py — Galactic Operations Dashboard (Minimal)
import time
from datetime import datetime
import random
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Galactic Ops Dashboard", page_icon="🛰️", layout="wide")

# -----------------------------
# Settings
# -----------------------------
st.title("🛰️ Galactic Operations Dashboard")
st.caption("Minimal health panel for a single spacecraft — fuel, solar, battery, thermal, and comms")

with st.sidebar:
    st.header("Simulation Controls")
    autoupdate = st.toggle("Auto-update every 1 sec", value=False)
    jitter = st.slider("Telemetry jitter (%)", 0, 10, 2)
    st.divider()
    st.header("Alert Thresholds")
    th_fuel = st.slider("Fuel low threshold", 0, 100, 25)
    th_batt = st.slider("Battery low threshold", 0, 100, 30)
    th_solar = st.slider("Solar output low threshold (kW)", 0, 200, 60)
    th_temp_hi = st.slider("Coolant temp HIGH (°C)", 40, 200, 120)
    th_comm = st.selectbox("Comms minimum status", ["Outage","Degraded","Nominal"], index=1)

# -----------------------------
# Telemetry Source (demo)
# -----------------------------
@st.cache_data(show_spinner=False)
def initial_state():
    return {
        "ship": "GI-01 ORION",
        "fuel_pct": 76,
        "battery_pct": 88,
        "solar_kw": 95,
        "coolant_c": 87,
        "comms": "Nominal",
    }

state = initial_state().copy()

def apply_jitter(val, pct):
    if pct <= 0: return val
    span = val * pct / 100.0
    return max(0, val + random.uniform(-span, span))

# One-shot jitter per render (keep deterministic per run)
state["fuel_pct"] = round(apply_jitter(state["fuel_pct"], jitter), 1)
state["battery_pct"] = round(apply_jitter(state["battery_pct"], jitter), 1)
state["solar_kw"] = round(apply_jitter(state["solar_kw"], jitter), 1)
state["coolant_c"] = round(apply_jitter(state["coolant_c"], jitter), 1)
state["comms"] = random.choice(["Nominal","Nominal","Nominal","Degraded"])  # biased toward Nominal

# -----------------------------
# KPIs
# -----------------------------
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("⛽ Fuel", f"{state['fuel_pct']} %", help="Remaining propellant")
k2.metric("🔋 Battery", f"{state['battery_pct']} %", help="Main bus SOC")
k3.metric("☀️ Solar Output", f"{state['solar_kw']} kW", help="Array instantaneous output")
k4.metric("❄️ Coolant Temp", f"{state['coolant_c']} °C", help="Primary loop temperature")
k5.metric("📡 Comms", state["comms"], help="Link status to ground")

st.divider()

# -----------------------------
# Visuals
# -----------------------------
c1, c2 = st.columns([2,1])

with c1:
    st.markdown("#### Systems Snapshot")
    # Small time series buffer stored in session_state for the session lifetime
    if "ts_hist" not in st.session_state:
        st.session_state.ts_hist = pd.DataFrame(columns=["t","Fuel%","Battery%","Solar(kW)","Coolant(°C)"])
    new_row = {
        "t": datetime.utcnow().strftime("%H:%M:%S"),
        "Fuel%": state["fuel_pct"],
        "Battery%": state["battery_pct"],
        "Solar(kW)": state["solar_kw"],
        "Coolant(°C)": state["coolant_c"],
    }
    st.session_state.ts_hist = pd.concat([st.session_state.ts_hist, pd.DataFrame([new_row])], ignore_index=True)
    st.line_chart(st.session_state.ts_hist.set_index("t"))

with c2:
    st.markdown("#### Gauges")
    st.progress(int(state["fuel_pct"]), text="Fuel")
    st.progress(int(state["battery_pct"]), text="Battery")
    st.progress(int(min(100, state["solar_kw"])), text="Solar (scaled)")
    st.progress(int(min(100, 200 - state["coolant_c"])), text="Thermal Margin (derived)")

st.divider()

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
    time.sleep(1)
    st.rerun()


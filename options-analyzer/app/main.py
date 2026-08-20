"""
Options Strategy Analyzer -- MVP
Run with: streamlit run app/main.py
"""

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from pricing import OptionType
from strategy import OptionLeg, Strategy

st.set_page_config(page_title="Options Strategy Analyzer", layout="wide")

st.title("Options Strategy Analyzer")
st.caption("Payoff diagrams, Greeks, breakevens, and probability of profit -- built on Black-Scholes.")

# ---------- Sidebar: market inputs ----------
with st.sidebar:
    st.header("Market Inputs")
    spot = st.number_input("Underlying price ($)", value=100.0, min_value=0.01, step=1.0)
    rate = st.number_input("Risk-free rate (%)", value=4.5, step=0.1) / 100
    vol = st.number_input("Implied volatility (%)", value=30.0, min_value=0.1, step=1.0) / 100
    days_to_expiry = st.number_input("Days to expiration", value=30, min_value=1, step=1)
    t = days_to_expiry / 365

    st.divider()
    st.header("Strategy")
    preset = st.selectbox(
        "Start from a preset",
        ["Custom", "Long Call", "Long Put", "Bull Call Spread", "Iron Condor", "Straddle"],
    )

# ---------- Build legs from preset or manual entry ----------
def preset_legs(name: str, spot: float, t: float) -> list[dict]:
    if name == "Long Call":
        return [dict(type="call", strike=round(spot * 1.02, 2), qty=1)]
    if name == "Long Put":
        return [dict(type="put", strike=round(spot * 0.98, 2), qty=1)]
    if name == "Bull Call Spread":
        return [
            dict(type="call", strike=round(spot, 2), qty=1),
            dict(type="call", strike=round(spot * 1.08, 2), qty=-1),
        ]
    if name == "Iron Condor":
        return [
            dict(type="put", strike=round(spot * 0.90, 2), qty=1),
            dict(type="put", strike=round(spot * 0.95, 2), qty=-1),
            dict(type="call", strike=round(spot * 1.05, 2), qty=-1),
            dict(type="call", strike=round(spot * 1.10, 2), qty=1),
        ]
    if name == "Straddle":
        return [
            dict(type="call", strike=round(spot, 2), qty=1),
            dict(type="put", strike=round(spot, 2), qty=1),
        ]
    return [dict(type="call", strike=round(spot, 2), qty=1)]


if "legs" not in st.session_state or st.session_state.get("_preset") != preset:
    st.session_state.legs = preset_legs(preset, spot, t)
    st.session_state["_preset"] = preset

st.subheader("Legs")
legs_to_remove = []
for i, leg in enumerate(st.session_state.legs):
    cols = st.columns([2, 2, 2, 1])
    leg["type"] = cols[0].selectbox("Type", ["call", "put"], index=["call", "put"].index(leg["type"]), key=f"type_{i}")
    leg["strike"] = cols[1].number_input("Strike", value=float(leg["strike"]), key=f"strike_{i}")
    leg["qty"] = cols[2].number_input("Qty (+long / -short)", value=int(leg["qty"]), step=1, key=f"qty_{i}")
    if cols[3].button("Remove", key=f"remove_{i}"):
        legs_to_remove.append(i)

for i in reversed(legs_to_remove):
    st.session_state.legs.pop(i)

if st.button("Add leg"):
    st.session_state.legs.append(dict(type="call", strike=round(spot, 2), qty=1))

if not st.session_state.legs:
    st.info("Add at least one leg to see analysis.")
    st.stop()

# ---------- Build Strategy object ----------
option_legs = [
    OptionLeg(
        option_type=OptionType(leg["type"]),
        strike=leg["strike"],
        expiry_years=t,
        quantity=leg["qty"],
    )
    for leg in st.session_state.legs
]
strat = Strategy(legs=option_legs)

entry_cost = strat.net_entry_cost(spot, rate, vol)
greeks = strat.net_greeks(spot, rate, vol)
breakevens = strat.breakevens(spot, rate, vol)
pop = strat.probability_of_profit(spot, rate, vol, t)

# ---------- Results ----------
st.divider()
col1, col2, col3 = st.columns(3)
col1.metric("Net cost (debit +/credit -)", f"${entry_cost:,.2f}")
col2.metric("Probability of profit", f"{pop*100:.1f}%")
col3.metric("Breakeven(s)", ", ".join(f"${b:,.2f}" for b in breakevens) if breakevens else "None found")

st.subheader("Greeks (position-level)")
g_cols = st.columns(5)
g_cols[0].metric("Delta", f"{greeks['delta']:.2f}")
g_cols[1].metric("Gamma", f"{greeks['gamma']:.4f}")
g_cols[2].metric("Theta / day", f"${greeks['theta']:.2f}")
g_cols[3].metric("Vega / 1vol pt", f"${greeks['vega']:.2f}")
g_cols[4].metric("Rho / 1% rate", f"${greeks['rho']:.2f}")

# ---------- Payoff diagram ----------
st.subheader("Payoff at Expiration")
strikes = [leg.strike for leg in option_legs]
lo = min(strikes) * 0.7
hi = max(strikes) * 1.3
price_range = np.linspace(lo, hi, 500)
pnl = strat.payoff_at_expiry(price_range, entry_cost)

fig = go.Figure()
fig.add_trace(go.Scatter(x=price_range, y=pnl, mode="lines", name="P&L", line=dict(width=3)))
fig.add_hline(y=0, line_dash="dash", line_color="gray")
fig.add_vline(x=spot, line_dash="dot", line_color="blue", annotation_text="Current price")
for be in breakevens:
    fig.add_vline(x=be, line_dash="dot", line_color="green", annotation_text=f"BE ${be:.2f}")

fig.update_layout(
    xaxis_title="Underlying price at expiration ($)",
    yaxis_title="Profit / Loss ($)",
    height=500,
)
st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Model: Black-Scholes (European exercise, no dividends). "
    "Probability of profit assumes lognormal price distribution at the given volatility. "
    "For educational use -- not investment advice."
)

"""
Live market data via yfinance.

Kept as a thin, isolated layer so the pricing/strategy engine stays
testable without network calls, and so this can be swapped for a paid
feed (Polygon.io, Tradier) later without touching the math.
"""

from datetime import datetime, date

import pandas as pd
import streamlit as st
import yfinance as yf


@st.cache_data(ttl=300)  # 5 min cache -- avoid hammering Yahoo on every rerun
def get_spot_price(ticker: str) -> float | None:
    """Current/last-close price for the underlying. None if ticker invalid."""
    try:
        tk = yf.Ticker(ticker)
        price = tk.fast_info.get("lastPrice")
        if price is None or price <= 0:
            hist = tk.history(period="1d")
            if hist.empty:
                return None
            price = float(hist["Close"].iloc[-1])
        return float(price)
    except Exception:
        return None


@st.cache_data(ttl=300)
def get_expirations(ticker: str) -> list[str]:
    """Available option expiration dates (YYYY-MM-DD strings) for a ticker."""
    try:
        tk = yf.Ticker(ticker)
        return list(tk.options)
    except Exception:
        return []


@st.cache_data(ttl=300)
def get_option_chain(ticker: str, expiration: str) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """
    Returns (calls_df, puts_df) for a given ticker/expiration.
    Each df has columns including strike, lastPrice, bid, ask, impliedVolatility.
    """
    try:
        tk = yf.Ticker(ticker)
        chain = tk.option_chain(expiration)
        return chain.calls, chain.puts
    except Exception:
        return None


def years_to_expiry(expiration: str) -> float:
    """Convert an 'YYYY-MM-DD' expiration string to years-from-today."""
    exp_date = datetime.strptime(expiration, "%Y-%m-%d").date()
    days = (exp_date - date.today()).days
    return max(days, 1) / 365


def nearest_strike_row(chain_df: pd.DataFrame, target_strike: float) -> pd.Series | None:
    """Find the chain row whose strike is closest to target_strike."""
    if chain_df is None or chain_df.empty:
        return None
    idx = (chain_df["strike"] - target_strike).abs().idxmin()
    return chain_df.loc[idx]


def estimate_atm_iv(calls_df: pd.DataFrame, puts_df: pd.DataFrame, spot: float) -> float | None:
    """
    Rough ATM implied vol estimate: average of the closest-to-spot
    call and put IVs reported by Yahoo. Used as a sane default vol
    input, not a substitute for a real vol surface.
    """
    call_row = nearest_strike_row(calls_df, spot)
    put_row = nearest_strike_row(puts_df, spot)
    ivs = []
    for row in (call_row, put_row):
        if row is not None and pd.notna(row.get("impliedVolatility")):
            iv = float(row["impliedVolatility"])
            if iv > 0:
                ivs.append(iv)
    if not ivs:
        return None
    return sum(ivs) / len(ivs)
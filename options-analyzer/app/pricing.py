"""
Black-Scholes options pricing and Greeks.

Core quant engine for the app. Kept dependency-free (numpy + scipy only)
so it's easy to unit test and easy to port to a faster backend later.
"""

from dataclasses import dataclass
from enum import Enum

import numpy as np
from scipy.stats import norm


class OptionType(str, Enum):
    CALL = "call"
    PUT = "put"


@dataclass
class OptionLeg:
    """A single option leg in a strategy."""
    option_type: OptionType
    strike: float
    expiry_years: float          # time to expiration, in years
    quantity: int = 1            # positive = long, negative = short
    premium_paid: float | None = None  # actual fill price, if known


def _d1_d2(spot: float, strike: float, rate: float, vol: float, t: float) -> tuple[float, float]:
    if t <= 0 or vol <= 0:
        raise ValueError("time to expiry and volatility must be > 0")
    d1 = (np.log(spot / strike) + (rate + 0.5 * vol**2) * t) / (vol * np.sqrt(t))
    d2 = d1 - vol * np.sqrt(t)
    return d1, d2


def bs_price(spot: float, strike: float, rate: float, vol: float, t: float,
             option_type: OptionType) -> float:
    """Black-Scholes price for a European option (no dividends)."""
    if t <= 0:
        # at/past expiry -> intrinsic value
        if option_type == OptionType.CALL:
            return max(spot - strike, 0.0)
        return max(strike - spot, 0.0)

    d1, d2 = _d1_d2(spot, strike, rate, vol, t)
    if option_type == OptionType.CALL:
        return spot * norm.cdf(d1) - strike * np.exp(-rate * t) * norm.cdf(d2)
    return strike * np.exp(-rate * t) * norm.cdf(-d2) - spot * norm.cdf(-d1)


def bs_greeks(spot: float, strike: float, rate: float, vol: float, t: float,
              option_type: OptionType) -> dict[str, float]:
    """
    Returns delta, gamma, theta (per calendar day), vega (per 1 vol point),
    and rho (per 1% rate move). Standard per-contract (i.e. per 1 unit
    of underlying) Greeks -- multiply by contract multiplier (100) and
    quantity in the aggregator layer.
    """
    if t <= 0:
        return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}

    d1, d2 = _d1_d2(spot, strike, rate, vol, t)
    pdf_d1 = norm.pdf(d1)

    gamma = pdf_d1 / (spot * vol * np.sqrt(t))
    vega = spot * pdf_d1 * np.sqrt(t) / 100  # per 1 vol point (1.00 = 100%)

    if option_type == OptionType.CALL:
        delta = norm.cdf(d1)
        theta = (
            -(spot * pdf_d1 * vol) / (2 * np.sqrt(t))
            - rate * strike * np.exp(-rate * t) * norm.cdf(d2)
        ) / 365
        rho = strike * t * np.exp(-rate * t) * norm.cdf(d2) / 100
    else:
        delta = norm.cdf(d1) - 1
        theta = (
            -(spot * pdf_d1 * vol) / (2 * np.sqrt(t))
            + rate * strike * np.exp(-rate * t) * norm.cdf(-d2)
        ) / 365
        rho = -strike * t * np.exp(-rate * t) * norm.cdf(-d2) / 100

    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega, "rho": rho}


def implied_volatility(market_price: float, spot: float, strike: float, rate: float,
                        t: float, option_type: OptionType,
                        tol: float = 1e-6, max_iter: int = 100) -> float:
    """Newton-Raphson solve for IV, falling back to bisection if it misbehaves."""
    vol = 0.3  # initial guess
    for _ in range(max_iter):
        price = bs_price(spot, strike, rate, vol, t, option_type)
        vega = bs_greeks(spot, strike, rate, vol, t, option_type)["vega"] * 100
        diff = price - market_price
        if abs(diff) < tol:
            return vol
        if vega < 1e-8:
            break
        vol -= diff / vega
        vol = max(vol, 1e-4)

    # Bisection fallback
    lo, hi = 1e-4, 5.0
    for _ in range(200):
        mid = (lo + hi) / 2
        price = bs_price(spot, strike, rate, mid, t, option_type)
        if abs(price - market_price) < tol:
            return mid
        if price > market_price:
            hi = mid
        else:
            lo = mid
    return mid

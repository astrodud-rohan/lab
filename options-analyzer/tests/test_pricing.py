"""
Sanity tests for the pricing engine.

Reference values are standard textbook Black-Scholes checks (Hull-style
parameters) so we can catch sign errors / formula mistakes early.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import numpy as np
import pytest
from pricing import OptionType, bs_greeks, bs_price, implied_volatility
from strategy import OptionLeg, Strategy


def test_call_put_parity():
    """C - P = S - K*exp(-rT) must hold exactly (within float tolerance)."""
    spot, strike, rate, vol, t = 100, 100, 0.05, 0.2, 1.0
    call = bs_price(spot, strike, rate, vol, t, OptionType.CALL)
    put = bs_price(spot, strike, rate, vol, t, OptionType.PUT)
    lhs = call - put
    rhs = spot - strike * np.exp(-rate * t)
    assert lhs == pytest.approx(rhs, abs=1e-8)


def test_atm_call_price_reasonable():
    # ATM call, 1yr, 20% vol, 5% rate -> known ballpark ~$10.45
    price = bs_price(100, 100, 0.05, 0.2, 1.0, OptionType.CALL)
    assert price == pytest.approx(10.45, abs=0.05)


def test_deep_itm_call_delta_near_one():
    greeks = bs_greeks(200, 100, 0.05, 0.2, 0.5, OptionType.CALL)
    assert greeks["delta"] > 0.95


def test_deep_otm_put_delta_near_zero():
    greeks = bs_greeks(200, 50, 0.05, 0.2, 0.1, OptionType.PUT)
    assert greeks["delta"] > -0.05


def test_implied_vol_roundtrip():
    spot, strike, rate, t = 100, 105, 0.03, 0.5
    true_vol = 0.25
    price = bs_price(spot, strike, rate, true_vol, t, OptionType.CALL)
    recovered = implied_volatility(price, spot, strike, rate, t, OptionType.CALL)
    assert recovered == pytest.approx(true_vol, abs=1e-4)


def test_long_call_breakeven():
    """Long call breakeven should equal strike + premium paid."""
    spot, rate, vol, t = 100, 0.05, 0.2, 0.25
    leg = OptionLeg(option_type=OptionType.CALL, strike=100, expiry_years=t, quantity=1)
    strat = Strategy(legs=[leg])
    entry_cost = strat.net_entry_cost(spot, rate, vol)
    premium_per_share = entry_cost / 100
    expected_be = 100 + premium_per_share
    bes = strat.breakevens(spot, rate, vol)
    assert len(bes) == 1
    assert bes[0] == pytest.approx(expected_be, abs=0.05)


def test_iron_condor_has_two_breakevens():
    t = 30 / 365
    legs = [
        OptionLeg(OptionType.PUT, 90, t, 1),
        OptionLeg(OptionType.PUT, 95, t, -1),
        OptionLeg(OptionType.CALL, 105, t, -1),
        OptionLeg(OptionType.CALL, 110, t, 1),
    ]
    strat = Strategy(legs=legs)
    bes = strat.breakevens(100, 0.05, 0.3)
    assert len(bes) == 2
    assert bes[0] < 100 < bes[1]


def test_probability_of_profit_bounded():
    t = 30 / 365
    leg = OptionLeg(OptionType.CALL, 100, t, 1)
    strat = Strategy(legs=[leg])
    pop = strat.probability_of_profit(100, 0.05, 0.3, t)
    assert 0.0 <= pop <= 1.0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

"""
Aggregates individual OptionLegs into a strategy: net payoff curve,
net Greeks, breakeven points, and probability of profit at expiry.
"""

from dataclasses import dataclass, field

import numpy as np
from scipy.stats import norm

from pricing import OptionLeg, OptionType, bs_greeks, bs_price

CONTRACT_MULTIPLIER = 100  # standard US equity option multiplier


@dataclass
class Strategy:
    legs: list[OptionLeg] = field(default_factory=list)

    def net_entry_cost(self, spot: float, rate: float, vol: float) -> float:
        """
        Net debit (positive) or credit (negative) to enter the position,
        in dollars, using theoretical BS price if no fill price was given.
        """
        total = 0.0
        for leg in self.legs:
            price = leg.premium_paid
            if price is None:
                price = bs_price(spot, leg.strike, rate, vol, leg.expiry_years, leg.option_type)
            total += price * leg.quantity * CONTRACT_MULTIPLIER
        return total

    def payoff_at_expiry(self, spot_prices: np.ndarray, entry_cost: float) -> np.ndarray:
        """
        P&L at expiration across a range of underlying prices.
        entry_cost: positive = net debit paid, negative = net credit received.
        """
        payoff = np.zeros_like(spot_prices, dtype=float)
        for leg in self.legs:
            if leg.option_type == OptionType.CALL:
                intrinsic = np.maximum(spot_prices - leg.strike, 0.0)
            else:
                intrinsic = np.maximum(leg.strike - spot_prices, 0.0)
            payoff += intrinsic * leg.quantity * CONTRACT_MULTIPLIER
        return payoff - entry_cost

    def net_greeks(self, spot: float, rate: float, vol: float) -> dict[str, float]:
        totals = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}
        for leg in self.legs:
            g = bs_greeks(spot, leg.strike, rate, vol, leg.expiry_years, leg.option_type)
            for k in totals:
                totals[k] += g[k] * leg.quantity * CONTRACT_MULTIPLIER
        return totals

    def breakevens(self, spot: float, rate: float, vol: float,
                    price_range: tuple[float, float] | None = None,
                    resolution: int = 20_000) -> list[float]:
        """
        Finds underlying prices at expiry where P&L crosses zero,
        via dense grid search + sign-change detection (robust for
        multi-leg strategies with several breakevens, e.g. iron condors).
        """
        if price_range is None:
            strikes = [leg.strike for leg in self.legs]
            lo = min(strikes) * 0.5
            hi = max(strikes) * 1.5
        else:
            lo, hi = price_range

        grid = np.linspace(lo, hi, resolution)
        entry_cost = self.net_entry_cost(spot, rate, vol)
        pnl = self.payoff_at_expiry(grid, entry_cost)

        sign_changes = np.where(np.diff(np.sign(pnl)) != 0)[0]
        breakevens = []
        for idx in sign_changes:
            x0, x1 = grid[idx], grid[idx + 1]
            y0, y1 = pnl[idx], pnl[idx + 1]
            # linear interpolation to the zero-crossing
            root = x0 - y0 * (x1 - x0) / (y1 - y0)
            breakevens.append(round(root, 2))
        return breakevens

    def probability_of_profit(self, spot: float, rate: float, vol: float,
                               t: float) -> float:
        """
        Probability the strategy is profitable at expiry, assuming the
        underlying follows GBM with the given implied vol (risk-neutral
        measure). Approximate for multi-leg strategies: integrates the
        lognormal density over the profitable region found via breakevens.
        """
        entry_cost = self.net_entry_cost(spot, rate, vol)
        bes = self.breakevens(spot, rate, vol)

        # Determine profitable region(s) by testing midpoints between
        # breakevens (and the extremes) against the payoff function.
        boundaries = sorted([0.0] + bes + [spot * 10])
        mu = np.log(spot) + (rate - 0.5 * vol**2) * t
        sigma = vol * np.sqrt(t)

        prob_profit = 0.0
        for lo, hi in zip(boundaries[:-1], boundaries[1:]):
            mid = (lo + hi) / 2
            pnl_mid = self.payoff_at_expiry(np.array([mid]), entry_cost)[0]
            if pnl_mid > 0:
                lo_clamped = max(lo, 1e-6)
                cdf_hi = norm.cdf((np.log(hi) - mu) / sigma) if hi < spot * 10 else 1.0
                cdf_lo = norm.cdf((np.log(lo_clamped) - mu) / sigma)
                prob_profit += cdf_hi - cdf_lo
        return float(np.clip(prob_profit, 0.0, 1.0))

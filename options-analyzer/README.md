# Options Strategy Analyzer

A web tool for analyzing multi-leg options strategies: payoff diagrams,
Greeks, breakevens, and probability of profit — built on Black-Scholes.

## Why this exists

Retail options traders mostly cobble this together from spreadsheets, or
pay $30–50/mo for tools like OptionStrat. This is a from-scratch quant
implementation: no black-box libraries for the pricing math, so it doubles
as a portfolio piece demonstrating derivatives pricing, not just UI work.

## Quickstart

```bash
pip install -r requirements.txt
streamlit run app/main.py
```

Then open the local URL Streamlit prints (usually `http://localhost:8501`).

## Running tests

```bash
python -m pytest tests/ -v
```

8 tests currently cover: put-call parity, ATM pricing sanity check, deep
ITM/OTM delta bounds, implied-vol solver roundtrip, single-leg breakeven,
multi-leg (iron condor) breakeven detection, and PoP bounding.

## Project structure

```
app/
  pricing.py    # Black-Scholes price, Greeks, implied vol solver
  strategy.py   # Multi-leg aggregation: payoff, net Greeks, breakevens, PoP
  main.py       # Streamlit UI
tests/
  test_pricing.py
```

## Current scope (v1 / MVP)

- European-exercise Black-Scholes pricing (no dividends)
- Presets: long call/put, bull call spread, iron condor, straddle
- Arbitrary custom multi-leg construction
- Payoff diagram at expiration
- Net position Greeks (delta/gamma/theta/vega/rho)
- Breakeven detection (handles multiple breakevens)
- Probability of profit (lognormal approximation under risk-neutral measure)
- **Live market data** via `yfinance`: real spot price, real expiration
  dates, real option chain quotes. When a leg's strike has a live quote,
  the strategy uses that actual last-traded price instead of theoretical
  BS price; legs without a quote fall back to BS pricing (and the app
  tells you which is which). ATM implied vol is estimated from the chain
  as a sensible default, editable by hand.
- Manual mode still available for stress-testing hypothetical scenarios
  (e.g. "what if vol spikes to 60%") that don't reflect current market data.

## Known limitations / roadmap

- **yfinance data quality** — Yahoo's option chain data can be stale or
  thin for illiquid strikes (wide bid/ask, zero volume). `lastPrice` can
  reflect a trade from earlier in the session. A v2 should show bid/ask
  alongside last price and warn on wide spreads.
- **No rate limit / caching hardening** — currently a 5-min TTL cache
  per ticker/expiration. Fine for personal use; would need review before
  many concurrent users hit it (Yahoo has historically throttled/blocked
  scrapers under heavy load).
- **European exercise only** — American early-exercise (matters for puts,
  dividend-paying stocks) would need a binomial/trinomial tree; Black-Scholes
  is the right MVP simplification.
- **No dividends** — add a continuous dividend yield term (Merton model)
  before this goes near real equity positions.
- **PoP is an approximation** for multi-leg strategies — exact for
  single/double breakeven cases, integrates correctly, but hasn't been
  validated against a Monte Carlo simulation yet. Worth adding that
  cross-check before advertising this number to paying users.
- **No IV skew/smile** — uses flat volatility across strikes, which is
  unrealistic for real markets (especially index options). A real v2
  would fit a vol surface per expiration.
- **No auth/persistence** — v1 is stateless; "saved positions" (the
  paid-tier feature from the plan) needs a database + user accounts.

## Monetization path (from planning discussion)

- Free tier: this — single/multi-leg calculator, no saved state
- Paid tier ($9–15/mo): live option chains, saved positions, price alerts

## Disclaimer

Educational tool. Not investment advice. Model assumptions (no dividends,
constant volatility, European exercise) are simplifications that will
diverge from real market prices, especially for American-style equity
options near dividend dates.

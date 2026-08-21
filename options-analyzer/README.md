# Options Strategy Analyzer
 
A web tool for analyzing multi-leg options strategies: payoff diagrams,
Greeks, breakevens, and probability of profit — built on Black-Scholes.
 
## Live demo
 
option-analyzer.streamlit.app
 
## Why this exists
 
Retail options traders mostly cobble this together from spreadsheets, or
pay $30–50/mo for tools like OptionStrat. This is a from-scratch quant
implementation: no black-box libraries for the pricing math, so it doubles
as a portfolio piece demonstrating derivatives pricing, not just UI work.
 
## Case study: quantifying theta/gamma acceleration on a live SPY iron condor
 
To validate the tool against a real, well-known options phenomenon —
time decay accelerating as expiration approaches — I built the same iron
condor on live SPY data at two different expirations and compared the
Greeks directly, rather than just trusting the textbook explanation.
 
**Setup:** SPY iron condor, live market data, strikes roughly ±5% from
spot (long put / short put / short call / long call), spot ≈ $762.60.
 
| Metric | 30 days to expiry | 7 days to expiry | Change |
|---|---|---|---|
| Net cost (credit received) | $217 | $18 | Smaller credit near expiry |
| Probability of profit | 47.6% | 80.9% | Higher — less time to breach breakevens |
| Delta | -0.90 | -1.96 | More negative |
| **Gamma** | -0.4389 | **-1.0719** | **~2.4x larger** |
| **Theta / day** | +$31.38 | **+$77.00** | **~2.5x larger** |
| Vega | -$58.75 | -$30.74 | Roughly halved |
| Breakevens | $722.30 / $802.90 | $724.29 / $800.91 | Slightly tighter |
 
**Takeaway:** gamma and theta both roughly doubled going from 30 days to
7 days to expiry — a direct, quantified confirmation of time-decay
acceleration, with vega correspondingly compressing as there's less time
left for implied vol changes to matter. The jump in probability of profit
(47.6% → 80.9%) reflects less time for the underlying to travel outside
the breakeven range, not a change in the position's structural risk.
 
This also surfaced and fixed real bugs along the way: Yahoo's option
chain occasionally reports a near-zero implied volatility for
stale/illiquid quotes, which was silently producing degenerate Greeks
(all zeros) and a nonsensical 100% probability of profit before being
caught and filtered out (see `market_data.py::estimate_atm_iv`) — and
before that, the same near-zero value was crashing the app outright by
falling below a UI widget's minimum bound.
 
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
 
- **Single expiration per strategy** — all legs share one expiration date,
  so calendar spreads and diagonal spreads aren't supported. Entering
  mismatched-expiration legs isn't currently blocked or flagged, so the
  output would be silently wrong; worth adding a same-expiration guard.
- **yfinance data quality** — Yahoo's option chain data can be stale or
  thin for illiquid strikes (wide bid/ask, zero volume). `lastPrice` can
  reflect a trade from earlier in the session. Already caught one real
  instance of this in practice (near-zero IV readings breaking the
  Greeks — see case study above); a v2 should show bid/ask alongside
  last price and warn on wide spreads more generally.
- **No rate limit / caching hardening** — currently a 5-min TTL cache
  per ticker/expiration. Fine for personal use; would need review before
  many concurrent users hit it (Yahoo has historically throttled/blocked
  scrapers under heavy load).
- **European exercise only** — American early-exercise (matters for puts,
  dividend-paying stocks) would need a binomial/trinomial tree; Black-Scholes
  is the right MVP simplification.
- **No dividends** — add a continuous dividend yield term (Merton model)
  before this goes near real equity positions or high-yield tickers.
- **PoP is an approximation** for multi-leg strategies — exact for
  single/double breakeven cases, integrates correctly, but hasn't been
  validated against a Monte Carlo simulation yet. Worth adding that
  cross-check before advertising this number to paying users.
- **No IV skew/smile** — uses flat volatility across strikes, which is
  unrealistic for real markets (especially index options). A real v2
  would fit a vol surface per expiration.
- **No auth/persistence** — v1 is stateless; "saved positions" (the
  paid-tier feature from the plan) needs a database + user accounts.
## Disclaimer
 
Educational tool. Not investment advice. Model assumptions (no dividends,
constant volatility, European exercise) are simplifications that will
diverge from real market prices, especially for American-style equity
options near dividend dates.

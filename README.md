# lab

A collection of standalone technical projects — quant finance, astrophysics,
software tooling, and whatever else I'm building. Each subdirectory is
self-contained with its own README, dependencies, and (where applicable)
tests.

## Projects

| Project | Description |
|---|---|
| [`options-analyzer/`](./options-analyzer) | Multi-leg options strategy analyzer — payoff diagrams, Greeks, breakevens, PoP. Black-Scholes pricing engine built from scratch, live market data via yfinance. |

## Structure

Each project directory is independent — its own `requirements.txt` (or
equivalent), its own tests, its own README with setup instructions. Nothing
here is meant to be installed as a single package; treat each folder as its
own mini-repo living under one roof.
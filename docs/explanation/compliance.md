# Compliance & Responsible Operation Policy

This document outlines the system's operational boundaries, jurisdictional constraints, exchange Terms of Service (ToS) alignments, and scraping etiquettes.

---

## 1. Jurisdictional Eligibility Notes

* **Kalshi**: A CFTC-regulated designated contract market (DCM). Automated market making is officially supported for US residents using Developer API credentials. The system uses official REST and WebSocket endpoints.
* **Polymarket**: Restricted for US residents under the CFTC settlement agreement. The system's Polymarket adapter (Gamma CLOB integration) must be disabled (`polymarket_enabled: false`) if the deployment machine is physically located or operated within the United States.
* **Betfair**: Disabled due to licensing, geo-restrictions, and cash transfer complexities.

---

## 2. Exchange Terms of Service (ToS) Alignment

* **Authorized Automation API Usage**: The system strictly interacts with official API gateways (`api.kalshi.com`, `clob.polymarket.com`). It does not run headless browsers to bypass recaptchas or scraping blocks, aligning with exchange developer guidelines.
* **Account-Level Throttle Enforcement**: The API client implements token bucket rate-limiters matching Kalshi (10 req/sec) and Polymarket (100 req/sec) thresholds to prevent IP rate-limiting.

---

## 3. Web Scraping Etiquette

To ensure ethical scraping of third-party public sites (such as `eloratings.net`), the ingestion module enforces the following policies:
* **Separated Crawl Schedule**: Ratings are crawled at most once per day.
* **Aggressive Caching**: Every downloaded page is saved to the local `data/raw/` store. If the file exists, the system does not hit the network.
* **User-Agent Declaration**: Every request transmits a descriptive header identifying the scraper and contact email.
* **Politeness Timeout**: The parser waits 2.0 seconds between multi-page requests.

---

## 4. Risk Limits and Safety Fences

The risk constraints configured in the Pydantic schema enforce strict protective bounds:
* **The USD 100 Position Cap**: Limits maximum capital exposure to $2\%$ of bankroll per contract event, preventing single-match outliers from causing catastrophic drawdowns.
* **Daily USD 250 Stop-Loss**: Halts all quoting immediately if cumulative realized loss in the ledger exceeds \$250, forcing manual operator review before re-arming.
* **Double-Sided Quote Pause**: If orderbook spreads tighten past normal levels, the quoting engine Pauses affected tickers to avoid execution during adverse market conditions.

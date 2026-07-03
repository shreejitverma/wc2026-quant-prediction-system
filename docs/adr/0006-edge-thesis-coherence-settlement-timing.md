# ADR-0006: Edge thesis — coherence, settlement precision, information timing (not out-leveling the sharp)

- **Status**: Accepted
- **Date**: 2026-07-01
- **Deciders**: Shreejit Verma

---

## Context

**The sharpest closing prices are empirically very hard to beat head-to-head.**

Hvattum & Arntzen (2010) and the broader academic literature show that Elo-family and Poisson goal models struggle to add *additional* information above what is already embedded in closing lines from sharp bookmakers (Pinnacle, Betfair exchange closing price).

A solo operator whose only strategy is *"I can predict France vs Argentina better than the market"* faces:

1. **Adverse selection**: Every counterparty willing to take the other side of a bet against a solo operator has *also* done their homework. The easy liquidity is gone.
2. **Vig friction**: Even with a true 1% edge, the exchange fee (2–4% round-trip) eats the signal.
3. **Resource asymmetry**: Quantitative funds have faster data feeds, more computing power, larger datasets, and dedicated researchers. A solo operator grinding against closing lines with a Poisson model is bringing a knife to a tank fight.

**But the market is not a single, coherent oracle.** It is assembled by many participants who each price marginal contracts *independently*. This creates three structural inefficiencies that are exploitable by a solo operator with a joint probabilistic model:

1. **Incoherence across correlated contracts**: If Brazil's price to top Group G is 68% and their price to win each of three group matches is 85%, 75%, and 80%, the product of these (~51%) should be approximately equal to the joint "top group" probability after accounting for tournament path effects. It rarely is.
2. **Settlement rule misreading**: Prediction market contracts are written in natural language. "Brazil advances from Group G" is not the same as "Brazil wins Group G" — but market participants frequently conflate them, creating pricing errors.
3. **Information timing**: Expected lineups versus *confirmed* lineups at kickoff represent an information asymmetry exploitable in the 60 minutes before the match starts.

---

## Decision

We will treat the durable edge for a solo quantitative operator as three structural sources, in priority order:

### Edge Class 1: Cross-venue + internal-coherence pricing

**What it is**: Using the joint tournament simulator (100k-path Monte Carlo) to price *all* contracts in a single internally consistent probability space, then comparing against *independently-priced* individual contracts on exchanges.

**How it works**:
- Our simulator says Brazil's probability of winning the World Cup is 14.2%.
- This implies Brazil wins their Quarterfinal with probability ~40.1%, given they've reached the Semis.
- If the QF-specific "Brazil beats Argentina" contract trades at 45% on Polymarket, there is a pricing inconsistency. We can sell Brazil/buy the tournament win market (or vice versa) to capture the spread.

**Why it's the safest edge class**: We are not trying to out-model the sharp on any single event. We are catching the *inconsistency between markets* that arises because human traders price each contract in isolation.

### Edge Class 2: Settlement-definition precision

**What it is**: Reading contract resolution text more carefully than the average market participant.

**Examples of settlement traps**:
- *"Brazil reaches the Quarterfinals"*: Does this include via 3rd-place advancement? Not always.
- *"Top scorer scores in the match"*: Does an own goal count? Must it be in 90 minutes only?
- *"France wins the tournament"*: Does a penalty shootout win count? Yes for FIFA, not always for contract language.

**How we exploit it**: Our contract mapper (`pricing.mapper`) ingests raw contract text and applies a settlement rule taxonomy (see ADR-0013). Markets systematically mispriced via rule misreading are safe to trade once correctly identified.

### Edge Class 3: Information timing

**What it is**: The M4 Player-Aggregation model builds up expected goals from individual player-level statistics. When a team's confirmed lineup is released (~60 minutes before kickoff), it updates M4's prediction. If a key striker is injured, the model's prediction drops significantly. This 60-minute window before the market fully prices the news is the information timing edge.

**Importantly**: We are not trading on *non-public* information. Lineups are publicly announced — we are simply processing the public announcement faster and more precisely (with per-player xG weights) than retail traders.

---

## What is *Not* an Edge Source (Alternatives Rejected)

| Strategy | Why Rejected |
|----------|-------------|
| **"Beat the sharp on 1X2 match outcome"** | Lowest and possibly *negative* expected edge class. The sharpest closing prices are the market's best probability estimate. Grinding against them with a standard Poisson model is a losing proposition. This is a **benchmark to calibrate against**, not a market to beat. |
| **Pure cross-venue stat-arb ignoring settlement text** | Classic trap. The "edge" appears to be a pricing gap, but it is actually a definition mismatch. At resolution, both sides settle the same way and the "arb" evaporates. |
| **In-play as the primary battlefield** | The 60-second window after a goal is scored is where firms with official low-latency feeds (Bloomberg, Sportradar) operate. A solo operator with a Python process and a residential internet connection cannot compete on speed in-play. The correct posture in-play is defensive: quote wide or pull. |

---

## Consequences

### Positive
- The joint simulator and contract mapper become the **primary alpha engine**, not plumbing.
- Edge is focused where it is structurally durable (coherence) rather than where it is structurally absent (1X2 marginal vs sharp).
- Settlement mapping is now a first-class investment area.

### Negative
- The joint simulator must be correct and fast. An error in the tournament bracket topology produces systematically wrong coherence prices.
- Settlement mapping is labor-intensive: each new contract's resolution text must be parsed and classified.

### Ongoing verification
**This is a thesis to be *tested*, not assumed.** Phase 7 measures realized Closing Line Value (CLV) by edge class. If the data shows that coherence pricing produces negative CLV consistently, the thesis is revised. Pre-registration gates (PR-LIVE-0001) enforce that this revision is driven by data, not emotion.

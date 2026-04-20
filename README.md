# chainlink-node-operator-intel

> Node operators securing the majority of DeFi can't easily answer two questions:
> *How am I performing relative to the network?* and *Do I trust what I'm being paid?*
> This project builds the methodology layer to answer both.

---

## The problem worth solving

Chainlink's Node Operator network is one of the most economically significant pieces of 
infrastructure in crypto. Operators collectively secure tens of trillions in transaction 
value — yet the feedback loop between their operational behaviour and their economic 
outcomes is opaque.

In a well-designed incentive system, operators should be able to observe their performance, 
understand how it translates to compensation, and make rational infrastructure investment 
decisions as a result. Today, that loop is incomplete.

Three specific gaps drive this:

**No standardised performance scorecard.** Uptime, latency, and deviation accuracy are all 
measurable onchain — but there is no single authoritative view that aggregates them into a 
signal operators can act on. Without a shared methodology, operators can't benchmark 
themselves, and Chainlink can't make principled feed allocation decisions.

**Flat compensation reduces investment incentives.** When a high-performing operator and a 
mediocre one earn the same for servicing a feed, the rational decision is to invest minimally 
in infrastructure. Performance-based systems fix this — but only if the scoring is trusted. 
Operators won't accept compensation tied to a methodology they can't inspect.

**Methodology opacity kills trust.** The number matters less than the explanation behind it. 
An operator who understands exactly why their score is 71 and not 80 can act on that 
information. An operator who receives an unexplained score will contest it.

This project addresses all three gaps: a configurable scoring engine, a transparent 
methodology, and operator-facing reports that explain performance in plain terms.

---

## What it does

**Data layer** — Generates realistic node operator submission data across 30 days of ETH/USD 
feed rounds: participation rates, submission latencies, price deviations, and aggregated 
outcomes. Designed to be swapped for real onchain data via The Graph in v2.

**Scoring engine** — A weighted composite model that calculates per-operator scores across 
four metrics, classifies operators into performance tiers, and outputs a ranked leaderboard. 
Weights are fully configurable via `config.yaml` — because the right weights are a product 
decision, not a technical one.

**Operator reports** — Individual markdown reports per operator showing their scores, network 
context, plain-English drivers of their classification, and compensation implications. The 
report is the product — the score alone is not enough.

---

## Scoring methodology

The scoring model is built on four metrics. Each was chosen because it is directly 
measurable onchain, has a clear causal relationship with network reliability, and is 
difficult to game without genuinely improving performance.

| Metric | Weight | Definition | Why it matters |
|---|---|---|---|
| Uptime rate | 30% | % of rounds where operator submitted within the valid window | Primary reliability signal — a node that isn't submitting is not securing the network |
| Latency score | 30% | Submission speed relative to network median, normalised 0–100 | Fast submissions improve aggregation quality and reduce the window for manipulation |
| Deviation accuracy | 25% | Mean absolute deviation of operator price from final aggregated value | Measures data quality — operators fetching from poor or correlated sources show up here |
| Round participation | 15% | % of total rounds participated in over the scoring window | Distinguishes consistent operators from those with intermittent outages |

Composite score = Σ (metric score × weight), scaled 0–100.

**Tier classification:**

| Tier | Score threshold | Meaning |
|---|---|---|
| Tier 1 | ≥ 80 | Eligible for high-value feed allocation and maximum compensation rate |
| Tier 2 | 60–79 | Standard feed allocation, standard compensation |
| At Risk | < 60 | Flagged for review — feed reallocation likely if not improved within 30 days |

---

## Design decisions and trade-offs

These are worth being explicit about — a scoring system you can't critique is a scoring 
system you shouldn't trust.

**Why latency and uptime share equal weight at 30% each.** Uptime is the threshold condition 
— a node that doesn't submit is worthless regardless of how accurate it would have been. 
Latency is the quality differentiator among nodes that do submit. Weighting them equally 
reflects that both are necessary but neither is sufficient alone.

**Why deviation accuracy is not weighted higher.** Deviation from median is an imperfect 
proxy for data quality. An operator fetching from genuinely independent sources may deviate 
more than one anchoring to correlated APIs — and would be penalised for doing the right 
thing. A higher weight on deviation accuracy creates an incentive to anchor to consensus 
rather than fetch independently, which undermines the oracle network's core security 
assumption. 25% reflects this tension deliberately.

**The Goodhart's Law problem.** Any metric that becomes a compensation target will be 
optimised for, not just measured. Latency scoring creates an incentive to submit fast with 
low-confidence data during volatile markets. The mitigation — not yet implemented — is a 
data quality gate that invalidates submissions deviating beyond a threshold before latency 
scoring is applied.

**Weights are a product decision.** The values in `config.yaml` are a starting point, not 
ground truth. The right weights should be derived from empirical analysis of which metrics 
best predict downstream network reliability outcomes. This requires historical data and 
regression analysis — flagged as v2 work.

---

## Limitations and known gaps

Being explicit about what this model doesn't do is as important as what it does.

- **Synthetic data only in v1.** The scoring engine is correct; the data it runs on is 
simulated. Real operator addresses, submission histories, and latency distributions from 
The Graph are the v2 priority.

- **No geographic normalisation.** A node in Tokyo serving Asian market hours has 
structurally different latency characteristics than one in Frankfurt. Scoring them on the 
same absolute latency benchmark is implicitly biased. Peer group normalisation is needed.

- **No appeals mechanism.** A production system needs a process for operators to dispute 
their scores — with a defined review workflow and documented resolution criteria. Trust 
requires recourse.

- **Static scoring window.** This model scores over a fixed 30-day window. It doesn't 
distinguish between an operator who was consistently mediocre and one who had three bad 
days in an otherwise strong month. Time-weighted scoring with decay functions is a 
meaningful improvement.

- **No cross-product view.** An operator serving Price Feeds, CCIP, and VRF has different 
performance profiles across products. This model treats them as a single entity. Product-
level scoring with a composite roll-up is the correct architecture.

---

## Running it

```bash
git clone https://github.com/smitpatel-68/chainlink-node-operator-intel
cd chainlink-node-operator-intel
pip install -r requirements.txt

# Run full pipeline
python main.py

# Generate report for a specific operator
python main.py --operator 0xABC123

# Adjust scoring weights
# Edit config.yaml, then re-run
```

---

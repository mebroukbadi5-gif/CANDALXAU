# CANDALXAU — XAUUSD (Gold) Trading Signal Repository

> **XAUUSD (Gold)** — Real spot gold
> **Minute-level recurring patterns** at specific HH:MM times
> **Movement measured in DOLLARS** (not points)
> All times in **UTC+1 (Algeria)** (already converted from UTC)

## 🎯 What v9.1 Does

For EACH minute of EACH day, scans 974 days of 5m candles:

```
For each (weekday, HH:MM):
  - Look at next 30 minutes of 5m candles (6 candles)
  - entry_price = close at HH:MM
  - max_high = max(high of next 6 candles)
  - min_low  = min(low of next 6 candles)
  - move_up   = max_high - entry_price  (in DOLLARS)
  - move_down = entry_price - min_low   (in DOLLARS)
  
  - if move_up >= move_down: direction = UP (CALL)
  - else: direction = DOWN (PUT)

After 974 days, compute:
  - recurring_rate = % of days with same direction
  - avg_movement_dollars = average $ moved in predicted direction
  - max_movement_dollars = largest historical $ movement
```

## 📊 Signal Counts (TRADABLE filters: ≥$1 movement + recurring rate)

| Day | 80pct | 70pct | 60pct | Notes |
|-----|-------|-------|-------|-------|
| Sunday | 0 | 0 | 0 | Market opens 23:00 Algeria |
| Monday | 0 | 1 | 18 | |
| Tuesday | 0 | 1 | 12 | |
| Wednesday | 1 | 6 | 19 | |
| Thursday | 0 | 1 | 20 | |
| Friday | 5 | 6 | 20 | Best day for high recurring rate |
| Saturday | 0 | 0 | 0 | Market CLOSED |
| **TOTAL** | **6** | **15** | **89** | |

## 📊 Distribution Across Hours (60pct tier)

Signals are distributed across the whole day, NOT concentrated at 23:00:

| Hour (Algeria) | Signals | Peak Movement Time |
|---|---|---|
| 00:00 | 5 | Asian session open |
| 01:00-03:00 | 4 | Asian trading |
| 05:00-09:00 | 6 | London pre-open |
| 11:00-12:00 | 6 | London session |
| 15:00-16:00 | 3 | London/NY overlap (peak volatility) |
| 22:00-23:00 | 8 | NY close / Asia open |

## 📐 Signal Format

```
⭐ 15:15 PUT rate=61% move=$11.74 (avg) max=$81.00 med=$9.05 samples=139
```

- **rate=61%**: in 61% of 974 days, price moved DOWN in this 30-min window
- **move=$11.74**: average dollar movement in DOWN direction
- **max=$81.00**: largest historical DOWN movement
- **med=$9.05**: median (typical) DOWN movement
- **samples=139**: number of historical days analyzed

## 🏆 Top Tradable Signals (high rate × large movement)

### Monday
- 15:15 PUT rate=61% move=$11.74 max=$81.00 (peak London/NY)
- 15:10 PUT rate=62% move=$11.29 max=$114.01
- 01:55 PUT rate=63% move=$9.82 max=$60.33 (Asian session)

### Tuesday
- 16:25 PUT rate=58% move=$14.17 max=$129.42 (BIG movement!)
- 16:30 PUT rate=57% move=$13.44 max=$104.30

### Wednesday
- 23:55 CALL rate=82% move=$4.57 max=$36.76 (highest recurring rate!)
- 23:50 CALL rate=70% move=$5.58 max=$36.76
- 15:45 CALL rate=61% move=$10.03 max=$45.42

### Thursday
- 16:50 PUT rate=55% move=$13.14 max=$228.90 (BIGGEST movement!)
- 07:20 PUT rate=60% move=$8.27 max=$88.28
- 02:05 CALL rate=66% move=$7.23 max=$36.39

### Friday
- 23:35 CALL rate=94% move=$1.15 max=$41.52 (highest rate!)
- 23:40 CALL rate=94% move=$0.98 max=$35.81
- 16:35 CALL rate=60% move=$10.71 max=$69.91

## 🎲 MTG1 Strategy

1. Entry 1: bet 1× → if WIN, take profit & stop
2. Entry 2: bet 2× → if WIN, recover loss & profit
3. Stop: after Entry 2 loss → max drawdown = 3×

## 🌍 Timezone

- All times in **UTC+1 (Algeria)** (already converted from UTC)
- UTC+1 = Algeria, France, Tunisia

## 🕐 Market Hours (XAUUSD)

- **Saturday**: Market CLOSED
- **Sunday**: Opens at 23:00 Algeria (22:00 UTC)
- **Monday-Friday**: 24h trading
- **Peak volatility**: 15:00-17:00 Algeria (London/NY overlap)

## 📂 Repository Structure

```
CANDALXAU/
├── README.md
├── XAUUSD_5m_974d_bd7b33c9.json           ← Gold 5m candles (974 days)
├── XAUUSD_5m_2190d_1a320748.json          ← Gold 5m candles (2190 days)
├── XAUUSD_1m_120d_e6d1e4c3.json           ← Gold 1m candles (120 days)
├── futurequantvexa_v4_xauusd.py          ← XAUUSD movement analyzer
├── generate_xauusd_signals.py             ← v9.1 minute-level scanner
└── signals/
    ├── by_day/{Sunday..Saturday}/         ← Per-day folders with 3 tier files
    ├── SIGNALS_XAUUSD_80pct.txt           ← Ultra-Elite (≥80% recurring)
    ├── SIGNALS_XAUUSD_70pct.txt           ← Elite (≥70% recurring)
    ├── SIGNALS_XAUUSD_60pct.txt           ← High (≥60% recurring)
    ├── SIGNALS_XAUUSD_BIG5.txt            ← Big movement (≥$5 avg)
    ├── SIGNALS_XAUUSD_BIG10.txt           ← Ultra big movement (≥$10 avg)
    ├── SIGNALS_XAUUSD_*.json               ← JSON versions
    ├── xauusd_minute_patterns.csv        ← All 1,452 minute-level patterns
    └── README.md
```

## ⚠️ Why v9.1 is Different

Previous v9.0 had filters that:
- Required ≥70% recurring rate
- Required only ≥$0.50 movement

This caused **late-night concentration** because:
- Late night hours have low volatility → 90%+ recurring rate
- But movement is only $0.50 (not tradable)

v9.1 fixes this:
- ≥60% recurring rate (more inclusive)
- ≥$1.00 movement (TRADABLE only)
- Result: 89 signals spread across all hours, not just 23:00

## ⚠️ Disclaimer

Trading binary options involves significant risk. Movement data reflects
historical patterns — not a guarantee of future results. Use MTG1 strategy.

---

Generated by **CANDALXAU Signal Engine v9.1** (tradable filters, minute-level, dollars, UTC+1 Algeria)

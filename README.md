# CANDALXAU — XAUUSD (Gold) Trading Signal Repository

> **XAUUSD (Gold)** — Real spot gold
> **Minute-level recurring patterns** at specific HH:MM times
> **Movement measured in DOLLARS** (not points)
> All times in **UTC+1 (Algeria)** (already converted from UTC)

## 🎯 What v9.0 Does

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

## 📊 Signal Tiers

### Recurring Rate Tiers (high % same direction)
- ⭐⭐⭐ ≥90% recurring: 5 signals (best: Friday 23:35 CALL 94%)
- ⭐⭐ ≥80% recurring: 29 signals
- ⭐ ≥70% recurring: 38 signals

### Big Movement Tiers (high $ volatility)
- 💥 **BIG5**: ≥$5 avg movement + ≥55% recurring → 337 signals
- 💥 **BIG10**: ≥$10 avg movement + ≥55% recurring → 48 signals

## 📐 Signal Format

```
⭐⭐ 23:25 CALL rate=90% move=$0.94 (avg) max=$34.80 med=$0.00 samples=139
💥 16:25 PUT  rate=58% move=$14.17 (avg) max=$129.42 med=$8.57 samples=140
```

- **rate=90%**: in 90% of 974 days, price moved UP in this 30-min window
- **move=$0.94**: average dollar movement in UP direction
- **max=$34.80**: largest historical UP movement in this window
- **med=$0.00**: median (typical) UP movement
- **samples=139**: number of historical days analyzed

## 🏆 Top ULTRA-ELITE Signals (≥90% recurring)

| Day | Time (Algeria) | Direction | Rate | Avg Move | Max Move |
|-----|----------------|-----------|------|----------|----------|
| Tuesday | 23:15 | CALL | 90% | $0.57 | $13.35 |
| Friday | 23:20 | CALL | 91% | $0.90 | $19.81 |
| Friday | 23:30 | CALL | 91% | $0.94 | $19.20 |
| Friday | 23:35 | CALL | 94% | $1.15 | $41.52 |
| Friday | 23:40 | CALL | 94% | $0.98 | $35.81 |

## 💥 Top BIG MOVEMENT Signals (≥$10 avg)

| Day | Time (Algeria) | Direction | Rate | Avg Move | Max Move |
|-----|----------------|-----------|------|----------|----------|
| Tuesday | 16:25 | PUT | 58% | $14.17 | $129.42 |
| Friday | 15:35 | PUT | 56% | $14.24 | $57.30 |
| Tuesday | 16:30 | PUT | 57% | $13.44 | $104.30 |
| Monday | 02:50 | CALL | 52% | $14.11 | $108.02 |
| Thursday | 16:50 | PUT | 55% | $13.14 | $228.90 |

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
├── generate_xauusd_signals.py             ← v9.0 minute-level scanner
└── signals/
    ├── by_day/{Sunday..Saturday}/         ← Per-day folders with 3 tier files
    ├── SIGNALS_XAUUSD_90pct.txt           ← Ultra-Elite (≥90% recurring)
    ├── SIGNALS_XAUUSD_80pct.txt           ← Elite (≥80% recurring)
    ├── SIGNALS_XAUUSD_70pct.txt           ← High (≥70% recurring)
    ├── SIGNALS_XAUUSD_BIG5.txt            ← Big movement (≥$5 avg)
    ├── SIGNALS_XAUUSD_BIG10.txt           ← Ultra big movement (≥$10 avg)
    ├── SIGNALS_XAUUSD_*.json               ← JSON versions
    ├── xauusd_minute_patterns.csv        ← All minute-level patterns
    └── README.md
```

## 🤖 Telegram Bot Integration

```python
import json
from datetime import datetime

# Load today's signals
today = datetime.now().strftime('%A')
path = f'signals/by_day/{today}/SIGNALS_90pct.txt'
with open(path) as f:
    signals_text = f.read()

# Or use JSON version
with open('signals/SIGNALS_XAUUSD_90pct.json') as f:
    data = json.load(f)
today_signals = [s for s in data['signals'] if s['day'] == today]

# Each signal has:
# - time: "23:35" (UTC+1 Algeria)
# - direction: "CALL" or "PUT"
# - recurring_rate: 94.0 (% of 974 days with same direction)
# - avg_movement_dollars: 1.15 (avg $ moved in predicted direction)
# - max_movement_dollars: 41.52 (largest historical $ movement)
# - samples: 139 (number of days analyzed)
```

## ⚠️ Disclaimer

Trading binary options involves significant risk. The recurring rate reflects
the historical frequency of a directional movement, not a guarantee of future
results. Always use proper bankroll management with MTG1 strategy.

---

Generated by **CANDALXAU Signal Engine v9.0** (minute-level patterns, dollars, UTC+1 Algeria)

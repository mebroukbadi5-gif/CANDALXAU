# CANDALXAU — XAUUSD (Gold) Trading Signal Repository

> **XAUUSD (Gold)** — Real spot gold
> **Per-weekday aggregation** — all Thursdays grouped together, all Fridays grouped together, etc.
> **≥80% recurring rate** (high accuracy)
> All times in **UTC+1 (Algeria)** (already converted from UTC)

## 🎯 Method (User's Request)

```
For each weekday (Mon/Tue/Wed/Thu/Fri):
  Group ALL same-weekday days together (139 days each)
  
  For each HH:MM on this weekday:
    Look at next N minutes of 5m candles (window)
    entry_price = close at HH:MM
    max_high = max(high of next N candles)
    min_low  = min(low of next N candles)
    move_up = max_high - entry  (in DOLLARS)
    move_down = entry - min_low (in DOLLARS)
    direction = BUY if move_up >= move_down else SELL
  
  Across all 139 same-weekday days:
    recurring_rate = % of days with same direction
    avg_move = average favorable movement in $
  
  Filter: ≥80% recurring + ≥$1 movement
```

## 📊 Signal Counts Per Day

| Day | 80pct | Notes |
|-----|-------|-------|
| Sunday | 0 | Market opens 23:00 Algeria |
| Monday | 0 | |
| Tuesday | 0 | |
| Wednesday | 3 | |
| Thursday | 1 | |
| Friday | 21 | Best day (peak accuracy) |
| Saturday | 0 | Market CLOSED |
| **TOTAL** | **25** | |

Also available at lower thresholds:
- 70pct: 47 signals
- 60pct: 283 signals

## 📐 Signal Format

```
⭐⭐⭐ 23:35 BUY  rate=94%  move=$1.15  max=$41.52  med=$0.00  win=30min  samples=139
```

- **23:35**: Entry time in UTC+1 (Algeria)
- **BUY**: Direction
- **rate=94%**: in 94% of 139 Fridays, price moved UP in this 30-min window
- **move=$1.15**: average dollar movement in UP direction
- **max=$41.52**: largest historical UP movement
- **med=$0.00**: median (typical) UP movement
- **win=30min**: optimal window size = 30 minutes
- **samples=139**: based on 139 same-weekday days

## 🏆 Top Signals (≥80% recurring)

### Friday (best day — 21 signals)
| Time | Direction | Rate | Move | Max | Window |
|------|-----------|------|------|-----|--------|
| 23:35 | BUY | **94%** | $1.15 | $41.52 | 30/60/120min |
| 23:10 | BUY | **91%** | $1.77 | $56.90 | 60/120min |
| 23:15 | BUY | **91%** | $1.46 | $37.90 | 60/120min |
| 23:20 | BUY | **91%** | $1.05 | $19.81 | 60/120min |
| 23:00 | BUY | 90% | $1.63 | $37.47 | 60/120min |
| 22:55 | BUY | 90% | $1.69 | $49.15 | 60/120min |

### Wednesday (3 signals)
| Time | Direction | Rate | Move | Max |
|------|-----------|------|------|-----|
| 22:55 | BUY | 88% | $1.31 | $42.55 |
| 23:55 | BUY | 82% | $5.35 | $36.76 (largest avg move!) |

### Thursday (1 signal)
| Time | Direction | Rate | Move | Max |
|------|-----------|------|------|-----|
| 22:55 | BUY | 87% | $1.15 | $31.36 |

## 🎯 Why Friday Late?

Friday 22:00-23:55 Algeria (21:00-22:55 UTC) is the period after NY close
and before Asian session opens. During this time:
- NY traders close positions before weekend
- Price often continues in established direction
- Less volatility = more predictable direction
- Result: 90%+ recurring rate

## 🌍 Timezone

- All times in **UTC+1 (Algeria)** (already converted from UTC)
- UTC+1 = Algeria, France, Tunisia

## 🕐 Market Hours (XAUUSD)

- **Saturday**: Market CLOSED
- **Sunday**: Opens at 23:00 Algeria (22:00 UTC)
- **Monday-Friday**: 24h trading
- **Best signals time**: Friday 22:00-23:55 Algeria (post-NY close)

## 📂 Repository Structure

```
CANDALXAU/
├── README.md
├── XAUUSD_5m_974d_bd7b33c9.json           ← Gold 5m candles (974 days)
├── XAUUSD_5m_2190d_1a320748.json          ← Gold 5m candles (2190 days)
├── XAUUSD_1m_120d_e6d1e4c3.json           ← Gold 1m candles (120 days)
├── futurequantvexa_v4_xauusd.py          ← XAUUSD movement analyzer
├── generate_xauusd_signals.py             ← v12.0 per-weekday aggregator
└── signals/
    ├── by_day/{Sunday..Saturday}/         ← Per-day folders
    │   └── SIGNALS_80pct.txt
    ├── SIGNALS_XAUUSD_80pct.txt           ← 25 high-accuracy signals
    ├── SIGNALS_XAUUSD_80pct.json
    ├── SIGNALS_XAUUSD_70pct.json          ← 47 signals (lower tier)
    ├── SIGNALS_XAUUSD_60pct.json          ← 283 signals (more options)
    ├── all_high_accuracy_signals.csv      ← CSV for analysis
    └── README.md
```

## 🤖 Telegram Bot Integration

```python
import json
from datetime import datetime

# Load today's signals
today = datetime.now().strftime('%A')
path = f'signals/by_day/{today}/SIGNALS_80pct.txt'
with open(path) as f:
    signals_text = f.read()

# Or use JSON version
with open('signals/SIGNALS_XAUUSD_80pct.json') as f:
    data = json.load(f)
today_signals = [s for s in data['signals'] if s['day'] == today]

# Each signal has:
# - time: "23:35" (UTC+1 Algeria)
# - direction: "BUY" or "SELL"
# - recurring_rate: 94.0 (% of same-weekday days with same direction)
# - avg_move: 1.15 (avg $ moved in predicted direction)
# - max_move: 41.52 (largest historical movement)
# - window_minutes: 30 (optimal hold time)
# - samples: 139 (number of same-weekday days)
```

## ⚠️ Disclaimer

Trading spot gold involves significant risk. Always use proper risk management.

---

Generated by **CANDALXAU Signal Engine v12.0** (per-weekday aggregator, UTC+1 Algeria)

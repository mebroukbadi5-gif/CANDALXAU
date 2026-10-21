# CANDALXAU — XAUUSD (Gold) Trading Signal Repository

> **XAUUSD (Gold)** — Real spot gold
> **Per-weekday aggregation** — all Mondays grouped, all Tuesdays grouped, etc.
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
  
  Filter: ≥80% recurring + ≥$0.50 movement
```

## 📊 Signal Counts Per Day (≥80% recurring + ≥$0.50 movement)

| Day | Signals | Best Signal | Notes |
|-----|---------|-------------|-------|
| Sunday | 0 | — | Market opens 23:00 Algeria |
| Monday | 3 | 22:55 BUY rate=89% | |
| Tuesday | 3 | 23:15 BUY rate=90% | |
| Wednesday | 10 | 23:25 BUY rate=90% | Includes 23:55 rate=82% move=$5.35 |
| Thursday | 7 | 22:15 BUY rate=90% | |
| Friday | 33 | 22:35 BUY rate=94% | Best day (peak accuracy) |
| Saturday | 0 | — | Market CLOSED |
| **TOTAL** | **56** | | |

## 📊 Lower Tiers (more signals, lower accuracy)

| Tier | Signals |
|------|---------|
| ≥80% + ≥$0.50 movement | 56 |
| ≥70% + ≥$0.50 movement | 78 |
| ≥60% + ≥$0.50 movement | 314 |

## 📐 Signal Format

```
⭐⭐ 23:25 BUY  rate=90%  move=$0.94  max=$34.80  med=$0.00  win=30min  samples=139
```

- **23:25**: Entry time in UTC+1 (Algeria)
- **BUY**: Direction (BUY = long, SELL = short)
- **rate=90%**: in 90% of 139 same-weekday days, price moved UP in this 30-min window
- **move=$0.94**: average dollar movement in UP direction
- **max=$34.80**: largest historical UP movement
- **med=$0.00**: median (typical) UP movement
- **win=30min**: optimal window size = 30 minutes
- **samples=139**: based on 139 same-weekday days

## 🏆 Top Signals Per Weekday

### Monday (3 signals)
| Time | Direction | Rate | Move | Max | Window |
|------|-----------|------|------|-----|--------|
| 22:55 | BUY | 89% | $0.75 | $34.60 | 30min |
| 22:55 | BUY | 88% | $0.79 | $34.60 | 60min |
| 23:00 | BUY | 88% | $0.66 | $30.83 | 30min |

### Tuesday (3 signals)
| Time | Direction | Rate | Move | Max | Window |
|------|-----------|------|------|-----|--------|
| 23:15 | BUY | 90% | $0.58 | $13.35 | 30min |
| 22:55 | BUY | 86% | $0.78 | $19.76 | 60min |
| 22:55 | BUY | 86% | $0.74 | $19.76 | 30min |

### Wednesday (10 signals)
| Time | Direction | Rate | Move | Max | Window |
|------|-----------|------|------|-----|--------|
| 23:25 | BUY | 90% | $0.94 | $34.80 | 30min |
| 22:55 | BUY | 88% | $1.31 | $42.55 | 60min |
| 23:15 | BUY | 86% | $0.83 | $16.24 | 30min |
| 23:20 | BUY | 86% | $0.80 | $24.77 | 30min |
| 23:05 | BUY | 85% | $0.80 | $23.63 | 30min |
| 22:00 | BUY | 84% | $0.77 | $19.49 | 30min |
| 22:10 | BUY | 84% | $0.74 | $16.71 | 30min |
| 23:10 | BUY | 84% | $0.74 | $16.71 | 30min |
| 22:55 | BUY | 84% | $0.87 | $21.55 | 30min |
| 23:55 | BUY | 82% | $5.35 | $36.76 | 60min |

### Thursday (7 signals)
| Time | Direction | Rate | Move | Max | Window |
|------|-----------|------|------|-----|--------|
| 22:15 | BUY | 90% | $0.68 | $30.76 | 30min |
| 22:25 | BUY | 89% | $0.53 | $15.53 | 30min |
| 21:55 | BUY | 87% | $1.15 | $31.36 | 60min |
| 22:10 | BUY | 88% | $0.76 | $27.15 | 30min |
| 22:00 | BUY | 84% | $0.80 | $26.45 | 30min |
| 22:05 | BUY | 84% | $0.80 | $37.63 | 30min |

### Friday (33 signals — best day)
| Time | Direction | Rate | Move | Max | Window |
|------|-----------|------|------|-----|--------|
| 22:35 | BUY | **94%** | $1.15 | $41.52 | 30min |
| 22:40 | BUY | **94%** | $0.98 | $35.81 | 30min |
| 22:10 | BUY | 91% | $1.77 | $56.90 | 60min |
| 22:30 | BUY | 91% | $0.94 | $19.20 | 30min |
| 22:20 | BUY | 91% | $1.05 | $19.81 | 60min |
| 22:15 | BUY | 91% | $1.46 | $37.90 | 60min |
| 22:05 | BUY | 90% | $1.81 | $51.88 | 60min |
| 22:00 | BUY | 90% | $1.63 | $37.47 | 60min |
| 21:55 | BUY | 90% | $1.69 | $49.15 | 60min |
| ...  | ... | ... | ... | ... | ... |

## 🌍 Timezone

- All times in **UTC+1 (Algeria)** (already converted from UTC)
- UTC+1 = Algeria, France, Tunisia

## 🕐 Market Hours (XAUUSD)

- **Saturday**: Market CLOSED
- **Sunday**: Opens at 23:00 Algeria (22:00 UTC)
- **Monday-Friday**: 24h trading
- **Best signal time**: 21:55-23:55 Algeria (post-NY close, pre-Asia open)

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
    ├── SIGNALS_XAUUSD_80pct.txt           ← 56 high-accuracy signals
    ├── SIGNALS_XAUUSD_80pct.json
    ├── SIGNALS_XAUUSD_70pct.json          ← 78 signals (lower tier)
    ├── SIGNALS_XAUUSD_60pct.json          ← 314 signals (more options)
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
# - time: "23:25" (UTC+1 Algeria)
# - direction: "BUY" or "SELL"
# - recurring_rate: 90.0 (% of same-weekday days with same direction)
# - avg_move: 0.94 (avg $ moved in predicted direction)
# - max_move: 34.80 (largest historical movement)
# - window_minutes: 30 (optimal hold time)
# - samples: 139 (number of same-weekday days)
```

## ⚠️ Disclaimer

Trading spot gold involves significant risk. Always use proper risk management.

---

Generated by **CANDALXAU Signal Engine v12.0** (per-weekday aggregator, UTC+1 Algeria)

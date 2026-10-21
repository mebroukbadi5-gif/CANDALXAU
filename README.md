# CANDALXAU — XAUUSD (Gold) Trading Signal Repository

> **XAUUSD (Gold)** — Real spot gold
> **BUY/SELL with Stop Loss + Take Profit** (NOT binary options, NOT MTG1)
> All times in **UTC+1 (Algeria)** (already converted from UTC)

## 🎯 What v11.0 Does

For each (weekday, HH:MM, window), computes:

```
Entry price = close at HH:MM
For each historical day (974 days):
  Look at next N minutes of 5m candles
  max_high = max(high of next N candles)
  min_low  = min(low of next N candles)
  
  BUY:  favorable = max_high - entry
        adverse   = entry - min_low
  
  SELL: favorable = entry - min_low
        adverse  = max_high - entry

Direction = BUY if median BUY favorable > median SELL favorable
TP = Take Profit level ($0.5, $1, $2, $3, $5)
SL = Stop Loss = median or 75th/90th percentile adverse movement
Win rate = % of days TP was hit
R/R = TP / SL (must be ≥1.0)
EV = (win_rate × TP) - (loss_rate × SL) (must be > 0)
```

## 📊 Signal Counts Per Day

| Day | Signals | Notes |
|-----|---------|-------|
| Sunday | 0 | Market opens 23:00 Algeria |
| Monday | 55 | |
| Tuesday | 113 | Best day (most signals) |
| Wednesday | 84 | |
| Thursday | 89 | |
| Friday | 100 | |
| Saturday | 0 | Market CLOSED |
| **TOTAL** | **441** | |

All 441 signals are PROFITABLE: Win rate ≥55%, R/R ≥1.0, EV > 0

## 📐 Signal Format

```
⭐⭐ 07:40 BUY  TP=$5.00  SL=$3.95  win=67%  R/R=1.27  EV=$2.04  hold=120min  n=139
```

- **07:40**: Entry time in UTC+1 (Algeria)
- **BUY**: Direction (BUY = long, SELL = short)
- **TP=$5.00**: Take Profit = $5.00 from entry price
- **SL=$3.95**: Stop Loss = $3.95 from entry price
- **win=67%**: 67% of historical days hit TP before SL
- **R/R=1.27**: Risk/Reward ratio = 5.00/3.95 = 1.27
- **EV=$2.04**: Expected profit per trade = $2.04
- **hold=120min**: Hold for 120 minutes or until TP/SL hit
- **n=139**: Based on 139 historical samples

## 🏆 Quality Badges

Based on R/R × win_rate:
- ⭐⭐⭐⭐ **Excellent**: ≥1.5 (5 signals)
- ⭐⭐⭐ **Very Good**: 1.0-1.5 (15 signals)
- ⭐⭐ **Good**: 0.7-1.0
- ⭐ **Decent**: 0.5-0.7
- ✓ **Marginal**: <0.5

## 📈 Trading Example

```
Signal: 07:40 BUY  TP=$5.00  SL=$3.95  win=67%  R/R=1.27  EV=$2.04  hold=120min

Current XAUUSD price: $2000.00
  1. Open BUY position at $2000.00
  2. Set Take Profit at $2005.00 (entry + $5.00)
  3. Set Stop Loss at $1996.05 (entry - $3.95)
  4. Hold for 120 minutes OR until TP/SL hit

Outcomes (based on 974 historical days):
  67% of days → TP hit (profit $5.00)
  33% of days → SL hit (loss $3.95)
  Expected profit per trade: $2.04
```

## 🎯 Why This Works

For spot trading (not binary options):
- We can use **Stop Loss** (limit losses)
- We can use **Take Profit** (lock profits)
- We don't need 80%+ win rate
- We need **R/R ≥ 1.0** + **positive EV**

Example:
- Win rate = 55%, R/R = 1.5
- Out of 100 trades: 55 wins × $1.50 - 45 losses × $1.00 = $82.50 - $45.00 = **+$37.50**

This is **realistic and profitable** — no fake 90% accuracy needed.

## 🌍 Timezone

- All times in **UTC+1 (Algeria)** (already converted from UTC)
- UTC+1 = Algeria, France, Tunisia

## 🕐 Market Hours (XAUUSD)

- **Saturday**: Market CLOSED
- **Sunday**: Opens at 23:00 Algeria (22:00 UTC)
- **Monday-Friday**: 24h trading
- **Peak hours**: 13:00-17:00 Algeria (London/NY overlap)

## 📂 Repository Structure

```
CANDALXAU/
├── README.md
├── XAUUSD_5m_974d_bd7b33c9.json           ← Gold 5m candles (974 days)
├── XAUUSD_5m_2190d_1a320748.json          ← Gold 5m candles (2190 days)
├── XAUUSD_1m_120d_e6d1e4c3.json           ← Gold 1m candles (120 days)
├── futurequantvexa_v4_xauusd.py          ← XAUUSD movement analyzer
├── generate_xauusd_signals.py             ← v11.0 BUY/SELL with TP/SL
└── signals/
    ├── by_day/{Sunday..Saturday}/         ← Per-day folders
    │   └── SIGNALS_BUY_SELL.txt
    ├── SIGNALS_XAUUSD_BUY_SELL.txt       ← All signals combined
    ├── SIGNALS_XAUUSD_BUY_SELL.json      ← JSON version
    ├── all_buy_sell_signals.csv          ← CSV for analysis
    └── README.md
```

## 🤖 Telegram Bot Integration

```python
import json
from datetime import datetime

# Load today's signals
today = datetime.now().strftime('%A')
path = f'signals/by_day/{today}/SIGNALS_BUY_SELL.txt'
with open(path) as f:
    signals_text = f.read()

# Or use JSON version
with open('signals/SIGNALS_XAUUSD_BUY_SELL.json') as f:
    data = json.load(f)
today_signals = [s for s in data['signals'] if s['day'] == today]

# Each signal has:
# - time: "07:40" (UTC+1 Algeria)
# - direction: "BUY" or "SELL"
# - tp_dollars: 5.00 (Take Profit)
# - sl_dollars: 3.95 (Stop Loss)
# - win_rate: 67.0 (% of days TP hit)
# - risk_reward: 1.27 (TP/SL ratio)
# - expected_value: 2.04 (EV per trade)
# - window_minutes: 120 (hold time)
```

## ⚠️ Disclaimer

Trading spot gold involves significant risk. Always:
- Use proper position sizing (risk ≤2% per trade)
- Honor Stop Loss (don't move it)
- Be patient — winning trades need time to develop
- Past performance doesn't guarantee future results

---

Generated by **CANDALXAU Signal Engine v11.0** (BUY/SELL + TP/SL, UTC+1 Algeria)

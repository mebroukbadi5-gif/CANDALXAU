# CANDALXAU — XAUUSD Indicator-Based Trading Signal Repository

> **XAUUSD (Gold)** — Real spot gold
> **Pattern + 5 Technical Indicators** (RSI, MACD, EMA, Bollinger, Volume)
> **Target: $5** (covers spread + profit)
> All times in **UTC+1 (Algeria)** (already converted from UTC)

## 🎯 User Request

```
User: "نريد اقل هدف هو 5 دولار لا تستخدم الاوقات
       بل استخدم مؤشرات وبعض من هذه الاشياء"
```

## 📐 Strategy

1. **Detect Double Bottom Breakout pattern** (user-described)
2. **Compute 5 technical indicators:**
   - RSI(14) — rising but not overbought
   - MACD(12/26/9) — bullish cross + histogram rising
   - EMA(9/21) — fast above slow (uptrend)
   - Bollinger Bands(20, 2) — touched lower band recently
   - Volume — spike > 1.5x average
3. **Need ≥3/5 indicators to confirm**
4. BUY when pattern + indicators align
5. **Take Profit at entry + $5**
6. **Stop Loss at entry - $3**
7. Hold max 240 minutes (4 hours)

## 📊 Pattern Statistics

- Total patterns detected: **24,505** (with ≥3 indicator confirmations)
- Overall win rate: **78.7%** (target $5, hold 240min)
- Distribution by confirmations:
  - 3/5 confirmations: 20,100 cases, 78.9% win rate
  - 4/5 confirmations: 4,405 cases, 77.8% win rate
- Average time to target: **43-44 minutes**

## 📊 Signal Counts Per Day

| Day | Signals | Top Win Rate | Net Profit/Trade |
|-----|---------|--------------|------------------|
| Sunday | 2 | **93%** (4/5 confirm) | $2.83 |
| Monday | 2 | 81% (3/5 confirm) | $2.92 |
| Tuesday | 2 | 76% (3/5 confirm) | $2.92 |
| Wednesday | 2 | 80% (3/5 confirm) | $2.92 |
| Thursday | 2 | 79% (3/5 confirm) | $2.92 |
| Friday | 2 | 78% (3/5 confirm) | $2.92 |
| **TOTAL** | **12** | | |

## 📐 Signal Format

```
⭐⭐⭐⭐ BUY  confirm=4/5  win=93%  target=$5  stop=$3  cases=13/14  avg_time=43min  net=$2.83
```

- **BUY**: Direction (always BUY — Double Bottom is bullish reversal)
- **confirm=4/5**: 4 out of 5 indicators confirm bullish
- **win=93%**: 93% of historical cases hit $5 target
- **target=$5**: Take Profit = $5 above entry
- **stop=$3**: Stop Loss = $3 below entry
- **cases=13/14**: 13 wins out of 14 historical cases
- **avg_time=43min**: Average time to hit target
- **net=$2.83**: Net profit per trade (after $0.5 spread)

## 🏆 Top Signals

### Sunday (best day for 4/5 confirmation)
- **BUY confirm=4/5 win=93% cases=13/14** ⭐⭐⭐⭐
- BUY confirm=3/5 win=89% cases=78/88

### Monday (highest case count)
- BUY confirm=4/5 win=79% cases=713/904
- BUY confirm=3/5 win=81% cases=3197/3965

### Wednesday
- BUY confirm=4/5 win=79% cases=707/892
- BUY confirm=3/5 win=80% cases=3373/4194

## 🎯 Why This Works

1. **Pattern (Double Bottom Breakout)** confirms bullish intent
2. **Indicators confirm** the pattern is supported by:
   - Momentum (RSI, MACD)
   - Trend (EMA)
   - Volatility (Bollinger)
   - Volume (participation)
3. **Confluence** = higher probability of success
4. **$5 target** is achievable within 4 hours for gold
5. **$3 stop** gives 1.67:1 R/R ratio

## 🎯 How to Trade Each Signal

```
1. Watch for Double Bottom Breakout pattern:
   - Recent LOW (L1)
   - Bounce up to HIGH (H1) — at least $1 above L1
   - Pullback to L2 (must be ABOVE L1)
   - Price breaks H1

2. Check indicators (need ≥3/5 bullish):
   - RSI rising, not overbought
   - MACD bullish cross, histogram rising
   - EMA9 above EMA21 (uptrend)
   - Price touched lower Bollinger band recently
   - Volume > 1.5x average

3. If ≥3 indicators confirm → BUY
4. Set Take Profit at entry + $5
5. Set Stop Loss at entry - $3
6. Hold max 240 minutes (usually hits in ~43 min)
```

## 🌍 Timezone

- All times in **UTC+1 (Algeria)** (already converted from UTC)

## 📂 Repository Structure

```
CANDALXAU/
├── README.md
├── XAUUSD_5m_974d_bd7b33c9.json           ← 5m candles (974 days)
├── XAUUSD_5m_2190d_1a320748.json          ← 5m candles (2190 days)
├── XAUUSD_1m_120d_e6d1e4c3.json           ← 1m candles (120 days)
├── XAUUSD_1m_400d_613e70e1.json           ← 1m candles (400 days) ← v18.0 uses this
├── generate_xauusd_signals.py             ← v15.0 direct signals
├── generate_xauusd_reversal_signals.py     ← v14.0 reversal signals
├── generate_xauusd_pattern_signals.py      ← v17.0 pattern signals
├── generate_xauusd_indicator_signals.py    ← v18.0 indicator signals (this!)
├── signals/                               ← Direct signals (v15)
├── reversal_signals/                      ← Reversal signals (v14)
├── pattern_signals/                       ← Pattern signals (v17)
└── indicator_signals/                     ← Indicator signals (v18) ← NEW
    ├── by_day/{Sunday..Saturday}/         ← Per-day folders
    │   └── SIGNALS_INDICATOR.txt
    ├── SIGNALS_XAUUSD_INDICATOR.txt       ← 12 indicator signals
    ├── SIGNALS_XAUUSD_INDICATOR.json
    └── README.md
```

## 🤖 Telegram Bot Integration

```python
import json
from datetime import datetime

# Load today's indicator signals
today = datetime.now().strftime('%A')
path = f'indicator_signals/by_day/{today}/SIGNALS_INDICATOR.txt'
with open(path) as f:
    signals_text = f.read()

# Or use JSON version
with open('indicator_signals/SIGNALS_XAUUSD_INDICATOR.json') as f:
    data = json.load(f)
today_signals = [s for s in data['signals'] if s['day'] == today]

# Each signal has:
# - direction: "BUY" (always BUY)
# - confirmations: 4 (out of 5 indicators)
# - win_rate: 93.0 (% of patterns that touched $5 target)
# - target_dollars: 5.0 (Take Profit)
# - stop_dollars: 3.0 (Stop Loss)
# - total_cases: 14 (historical cases tested)
# - avg_time_to_target_min: 43.0 (avg minutes to hit target)
# - net_profit_per_trade: 2.83 (after $0.5 spread)
```

## ⚠️ Disclaimer

Trading spot gold involves significant risk. Pattern + indicator confirmation
improves probability but doesn't guarantee success. Always use proper risk
management.

---

Generated by **CANDALXAU Signal Engine v18.0** (Indicator-based, UTC+1 Algeria)

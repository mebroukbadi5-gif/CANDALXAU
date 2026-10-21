# CANDALXAU — Trading Signal Repository

> FutureQuantVexa v5.2 — Multi-tier trading signals for binary options (OTC pairs + XAUUSD gold)

## 📊 Signal Files (in `signals/`)

| File | Tier | Threshold | Signals | Use Case |
|------|------|-----------|---------|----------|
| `SIGNALS_90pct.txt` | Elite | ≥90% C1+C2 | 6,227 | Maximum accuracy, low frequency |
| `SIGNALS_80pct.txt` | High | ≥80% C1+C2 | 13,875 | Balanced accuracy & frequency |
| `SIGNALS_70pct.txt` | Standard | ≥70% C1+C2 | 13,914 | Higher frequency, lower accuracy |
| `SIGNALS_ALL.txt` | All | All | 13,914 | Maximum frequency (use with caution) |
| `ALL_SIGNALS_v5.txt` | Combined | All | 13,914 | Original master file |
| `ALL_SIGNALS_v5.json` | Combined (JSON) | All | 13,914 | For programmatic use |
| `xauusd_movements.csv` | Stats | — | 170 windows | Movement statistics per day×hour |

## 🎯 Coverage

### OTC Currency Pairs (13 pairs)
BRLUSD, USDARS, USDBDT, USDCOP, USDDZD, USDEGP, USDIDR, USDINR, USDMXN, USDNGN, USDPHP, USDPKR, USDZAR

### Gold
XAUUSD-OTC (movement-based directional signals with adaptive expiry)

### Time Coverage
- 7 weekdays (Sunday → Saturday)
- 24 hours/day (UTC)
- Saturday is closed (gold); Sunday only opens at 22:00 UTC

## 📐 Signal Format

```
⭐ M1  USDARS-OTC   00:02 CALL  acc=91%  [GapRev]
└┬┘ └┬┘ └────┬────┘ └──┬─┘ └┬──┘ └─┬─┘ └──┬──┘
 │   │       │          │    │      │       └─ Pattern name
 │   │       │          │    │      └─ Accuracy (C1+C2%)
 │   │       │          │    └─ Direction (CALL=up, PUT=down)
 │   │       │          └─ Time (HH:MM UTC)
 │   │       └─ Pair name (with -OTC suffix)
 │   └─ Expiry in minutes (M1=1min, M5=5min, M15=15min, M30=30min)
 └─ Tier badge (⭐⭐=90%+, ⭐=85%+, 🔥=80%+, ✓=70%+)
```

## 🏆 Tier Badges

- ⭐⭐ **Elite**: ≥90% C1+C2 accuracy (ultra-precise, rare)
- ⭐ **High-Elite**: 85-90% C1+C2 accuracy
- 🔥 **High**: 80-85% C1+C2 accuracy
- ✓ **Standard**: 70-80% C1+C2 accuracy

## 🎲 MTG1 Strategy

```
Entry 1: bet 1× → if WIN, take profit & stop
Entry 2: bet 2× → if WIN, recover loss & profit (after Entry 1 loss)
Stop:    after Entry 2 loss → max drawdown = 3×
```

## 🤖 Telegram Bot Integration

```python
import re
from datetime import datetime, timezone, timedelta

# Parse signal line
SIGNAL_PATTERN = r'M(\d+)\s+([A-Z]+-OTC)\s+(\d{2}):(\d{2})\s+(CALL|PUT)'

def parse_signal(line):
    match = re.search(SIGNAL_PATTERN, line)
    if not match:
        return None
    expiry, pair, hour, minute, direction = match.groups()
    return {
        'expiry': int(expiry),
        'pair': pair,
        'time': f"{hour}:{minute}",
        'direction': direction,
    }

# Schedule signal at HH:MM UTC
def schedule_signal(signal, send_callback):
    now = datetime.now(timezone.utc)
    target = now.replace(hour=int(signal['time'][:2]),
                         minute=int(signal['time'][3:5]),
                         second=0, microsecond=0)
    if target < now:
        target += timedelta(days=1)
    delay = (target - now).total_seconds()
    # ... schedule send_callback after `delay` seconds
```

## 🌍 Timezone Notes

All times are in **UTC**. Adjust for your local timezone:
- **UTC+1** (Algeria, France, Tunisia): add 1 hour
- **UTC+2** (Egypt, South Africa): add 2 hours
- **UTC+3** (Saudi Arabia, UAE): add 3 hours

## 📁 Repository Structure

```
CANDALXAU/
├── README.md                          ← This file
├── XAUUSD_5m_974d_bd7b33c9.json       ← Gold 5m candles (974 days)
├── XAUUSD_5m_2190d_1a320748.json      ← Gold 5m candles (2190 days)
├── XAUUSD_1m_120d_e6d1e4c3.json       ← Gold 1m candles (120 days)
├── futurequantvexa_v3.py              ← OTC pairs signal generator
├── futurequantvexa_v4_xauusd.py       ← XAUUSD movement analyzer
├── generate_signals.py                ← Tiered signal generator (this script)
├── generate_all_signals.py            ← Consolidated signal generator
├── signals/
│   ├── README.md                       ← Signal files index
│   ├── SIGNALS_90pct.txt              ← Elite tier (≥90%)
│   ├── SIGNALS_80pct.txt              ← High tier (≥80%)
│   ├── SIGNALS_70pct.txt              ← Standard tier (≥70%)
│   ├── SIGNALS_ALL.txt                ← All signals
│   ├── ALL_SIGNALS_v5.txt             ← Master file
│   ├── ALL_SIGNALS_v5.json            ← JSON version
│   └── xauusd_movements.csv           ← Movement statistics
└── 24h_signals_raw/                   ← Raw per-day signal files (unfiltered)
    ├── Sun_Sunday.txt
    ├── Mon_Monday.txt
    ├── Tue_Tuesday.txt
    ├── Wed_Wednesday.txt
    ├── Thu_Thursday.txt
    ├── Fri_Friday.txt
    └── Sat_Saturday.txt
```

## 📈 Generation Pipeline

```
1. SCAN:        Read candle JSON files (OTC pairs + XAUUSD)
                → Detect 18 candlestick patterns
                → Store raw signals per weekday

2. BACKTEST:    Train/test split (70/30) without lookahead bias
                → Calculate C1% (candle 1 win rate)
                → Calculate C1+C2% (candle 1+2 win rate with MTG1)
                → Build ELITE_PATTERNS database (≥85% C1+C2)

3. CLASSIFY:    Match each signal to:
                  - ELITE_PATTERNS DB (verified ≥85%)
                  - Pair baseline + hour-of-day bonus
                → Assign final accuracy estimate

4. OUTPUT:      Generate tiered files:
                  - 90%+ (Elite)
                  - 80%+ (High)
                  - 70%+ (Standard)
                  - All (combined)

5. PUSH:        Commit to GitHub for Telegram bot access
```

## ⚠️ Disclaimer

Trading binary options involves significant risk. These signals are based on historical pattern analysis and statistical backtesting. Past performance does not guarantee future results. Always:
- Start with demo account
- Use proper bankroll management
- Never bet more than you can afford to lose
- Stop after 2 consecutive losses (per MTG1 strategy)

## 📞 Contact

- Repository: https://github.com/mebroukbadi5-gif/CANDALXAU
- Telegram bot integration: see `signals/README.md`

---

Generated by **FutureQuantVexa v5.2**

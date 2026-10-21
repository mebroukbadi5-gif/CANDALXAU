#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CANDALXAU Signal Engine v9.0 — Minute-Level Pattern Scanner
==============================================================
Searches for RECURRING PRICE MOVEMENTS at specific HH:MM times.

For each (weekday, start_time):
  - Look at next 30 minutes of 5m candles (6 candles × 5min = 30min)
  - entry_price = close at start_time
  - max_high = max(high of next 6 candles)
  - min_low  = min(low of next 6 candles)
  - move_up   = max_high - entry_price  (in DOLLARS, not points!)
  - move_down = entry_price - min_low    (in DOLLARS)
  - dominant_dir = 'UP' if move_up >= move_down else 'DOWN'
  - movement_dollars = max(move_up, move_down)
  
For each (weekday, start_time), aggregate over 974 days:
  - up_count:    days where dominant direction was UP
  - down_count:  days where dominant direction was DOWN
  - recurring_rate: max(up_count, down_count) / total × 100
  - avg_movement_dollars: average size of dominant movement
  - median_movement_dollars
  - max_movement_dollars

Filter: only keep signals with recurring_rate ≥ 70% AND avg_movement ≥ $0.50
"""

import os, sys, json, csv
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import statistics

PROJECT_DIR = '/home/z/my-project'
REPO_DIR = '/tmp/CANDALXAU'
INPUT_FILE = f'{REPO_DIR}/XAUUSD_5m_974d_bd7b33c9.json'
OUTPUT_DIR = f'{PROJECT_DIR}/download/signal_tiers_xauusd_v9'

# User timezone: UTC+1 (Algeria)
TZ_OFFSET = 1
TZ_NAME = 'UTC+1 (Algeria)'

WEEKDAY_FULL = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
WEEKDAY_SHORT = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']
WEEKDAY_NEXT = {
    'Sunday':'Monday','Monday':'Tuesday','Tuesday':'Wednesday',
    'Wednesday':'Thursday','Thursday':'Friday','Friday':'Saturday','Saturday':'Sunday',
}

# Movement window: 30 minutes (6 × 5min candles)
WINDOW_CANDLES = 6  # 30 minutes


def load_candles(filepath):
    """Load 5m candles from JSON file."""
    print(f"  Loading candles from: {filepath}")
    with open(filepath, 'r') as f:
        data = json.load(f)
    if isinstance(data, dict) and 'candles' in data:
        candles = data['candles']
    elif isinstance(data, list):
        candles = data
    else:
        candles = data
    
    normalized = []
    for c in candles:
        normalized.append({
            'time': int(c['time']),
            'open': float(c['open']),
            'high': float(c['high']),
            'low': float(c['low']),
            'close': float(c['close']),
        })
    normalized.sort(key=lambda c: c['time'])
    print(f"  Loaded {len(normalized):,} candles")
    return normalized


def scan_minute_patterns(candles, tz_offset=1, window=WINDOW_CANDLES):
    """Scan for recurring price movements at every HH:MM.
    
    For each (weekday, hour, minute), aggregate over all historical occurrences:
      - direction (UP/DOWN) based on which side had larger move
      - movement_size in DOLLARS (not points)
    """
    print(f"  Scanning minute-level patterns over {len(candles):,} candles...")
    print(f"  Window: {window} candles = {window*5} minutes")
    
    # results[(weekday_short, hour, minute)] = stats
    results = defaultdict(lambda: {
        'total': 0,
        'up_count': 0,           # days where move_up > move_down
        'down_count': 0,
        'up_sizes': [],          # list of move_up dollar values
        'down_sizes': [],        # list of move_down dollar values
        'all_movements': [],    # max(move_up, move_down) for each day
        'all_max_high': [],
        'all_min_low': [],
    })
    
    for i in range(len(candles) - window):
        candle = candles[i]
        dt = datetime.fromtimestamp(candle['time'], tz=timezone.utc) + timedelta(hours=tz_offset)
        py_weekday = dt.weekday()  # Mon=0, Sun=6
        our_weekday = (py_weekday + 1) % 7  # Sun=0, Mon=1, ..., Sat=6
        hour = dt.hour
        minute = dt.minute
        
        # Skip Saturday
        if our_weekday == 6:
            continue
        # Skip Sunday before 23:00 Algeria
        if our_weekday == 0 and hour < 23:
            continue
        
        next_candles = candles[i+1:i+1+window]
        if len(next_candles) < window:
            continue
        
        entry_price = candle['close']
        max_high = max(c['high'] for c in next_candles)
        min_low = min(c['low'] for c in next_candles)
        
        move_up = max_high - entry_price      # in DOLLARS
        move_down = entry_price - min_low     # in DOLLARS
        movement = max(move_up, move_down)    # dominant movement size
        
        weekday_short = WEEKDAY_SHORT[our_weekday]
        key = (weekday_short, hour, minute)
        
        results[key]['total'] += 1
        results[key]['all_movements'].append(movement)
        results[key]['all_max_high'].append(max_high)
        results[key]['all_min_low'].append(min_low)
        
        if move_up >= move_down:
            results[key]['up_count'] += 1
            results[key]['up_sizes'].append(move_up)
        else:
            results[key]['down_count'] += 1
            results[key]['down_sizes'].append(move_down)
    
    return results


def compute_signal_stats(results):
    """Compute final stats per (weekday, hour, minute)."""
    signals = []
    
    for (weekday_short, hour_utc, minute), r in results.items():
        if r['total'] < 30:
            continue
        
        total = r['total']
        up_pct = r['up_count'] / total * 100
        down_pct = r['down_count'] / total * 100
        recurring_rate = max(up_pct, down_pct)
        
        # Direction = which side was more common
        if up_pct >= down_pct:
            direction = 'CALL'
            direction_pct = up_pct
            direction_sizes = r['up_sizes']
        else:
            direction = 'PUT'
            direction_pct = down_pct
            direction_sizes = r['down_sizes']
        
        # Movement stats (in DOLLARS)
        all_moves = r['all_movements']
        avg_movement = statistics.mean(all_moves)
        median_movement = statistics.median(all_moves)
        max_movement = max(all_moves)
        min_movement = min(all_moves)
        stdev_movement = statistics.stdev(all_moves) if len(all_moves) > 1 else 0
        
        # Direction-specific stats
        if direction_sizes:
            avg_dir_move = statistics.mean(direction_sizes)
            median_dir_move = statistics.median(direction_sizes)
            max_dir_move = max(direction_sizes)
        else:
            avg_dir_move = 0
            median_dir_move = 0
            max_dir_move = 0
        
        # Convert UTC time to Algeria (UTC+1)
        local_hour = (hour_utc + TZ_OFFSET) % 24
        weekday_full = WEEKDAY_FULL[WEEKDAY_SHORT.index(weekday_short)]
        local_weekday = weekday_full
        if hour_utc + TZ_OFFSET >= 24:
            local_weekday = WEEKDAY_NEXT.get(weekday_full, weekday_full)
        
        signals.append({
            'pair': 'XAUUSD',
            'time': f"{local_hour:02d}:{minute:02d}",
            'time_utc': f"{hour_utc:02d}:{minute:02d}",
            'hour': local_hour,
            'hour_utc': hour_utc,
            'minute': minute,
            'direction': direction,
            'expiry': 30,  # 30-minute window
            'recurring_rate': recurring_rate,  # % of days with this direction
            'direction_pct': direction_pct,
            'avg_movement_dollars': avg_dir_move,  # avg $ moved in predicted direction
            'median_movement_dollars': median_dir_move,
            'max_movement_dollars': max_dir_move,
            'avg_total_movement': avg_movement,  # avg of max(up,down)
            'up_pct': up_pct,
            'down_pct': down_pct,
            'day': local_weekday,
            'day_utc': weekday_full,
            'samples': total,
            'asset_type': 'GOLD',
            'window_minutes': 30,
        })
    
    return signals


def save_results_csv(signals, output_path):
    """Save all signal stats to CSV."""
    with open(output_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow([
            'weekday', 'time_utc', 'time_algeria', 'direction',
            'samples', 'up_pct', 'down_pct', 'recurring_rate',
            'avg_movement_dollars', 'median_movement_dollars', 'max_movement_dollars',
            'avg_total_movement', 'window_minutes'
        ])
        for s in sorted(signals, key=lambda x: -x['recurring_rate']):
            w.writerow([
                s['day_utc'][:3], s['time_utc'], s['time'], s['direction'],
                s['samples'], f"{s['up_pct']:.1f}%", f"{s['down_pct']:.1f}%",
                f"{s['recurring_rate']:.1f}%",
                f"${s['avg_movement_dollars']:.2f}",
                f"${s['median_movement_dollars']:.2f}",
                f"${s['max_movement_dollars']:.2f}",
                f"${s['avg_total_movement']:.2f}",
                s['window_minutes']
            ])
    print(f"  ✓ Saved to: {output_path}")


def filter_top_signals(signals, min_recurring=70, min_movement=0.5, min_avg_total=0.10):
    """Filter to top signals: high recurring rate + meaningful movement.
    
    Filters:
      - min_recurring: minimum recurring direction rate (%)
      - min_movement: minimum average $ moved in predicted direction
      - min_avg_total: minimum avg total movement (filters out closed-market
                       hours where price doesn't move at all)
    """
    filtered = [s for s in signals 
                if s['recurring_rate'] >= min_recurring 
                and s['avg_movement_dollars'] >= min_movement
                and s['avg_total_movement'] >= min_avg_total]
    # Sort by recurring_rate × avg_movement (combined score)
    filtered.sort(key=lambda s: -(s['recurring_rate'] * s['avg_movement_dollars']))
    return filtered


def filter_big_movement_signals(signals, min_recurring=55, min_movement=5.0):
    """Filter to big-movement signals: meaningful dollar movement ($5+) + ≥55% recurring.
    
    These are HIGH-VOLATILITY patterns where price moves $5-15+ in 30 minutes.
    Tradeable for larger profit targets.
    """
    filtered = [s for s in signals 
                if s['recurring_rate'] >= min_recurring 
                and s['avg_movement_dollars'] >= min_movement
                and s['avg_total_movement'] >= min_movement]
    # Sort by avg_movement (largest first)
    filtered.sort(key=lambda s: -s['avg_movement_dollars'])
    return filtered


def generate_signal_files(signals, output_dir):
    """Generate per-day folders with tier files."""
    by_day = defaultdict(list)
    for s in signals:
        by_day[s['day']].append(s)
    
    # Tier definitions: (min_recurring_rate, label)
    tiers = [
        (90, 'ULTRA-ELITE (≥90% recurring + ≥$0.50 movement)'),
        (80, 'ELITE (≥80% recurring + ≥$0.50 movement)'),
        (70, 'HIGH (≥70% recurring + ≥$0.50 movement)'),
    ]
    
    day_counts = {}
    
    for day in WEEKDAY_FULL:
        day_sigs = by_day.get(day, [])
        day_sigs.sort(key=lambda s: (s['hour'], s['minute']))
        
        day_folder = os.path.join(output_dir, day)
        os.makedirs(day_folder, exist_ok=True)
        
        day_counts[day] = {}
        
        for threshold, tier_label in tiers:
            tier_sigs = [s for s in day_sigs 
                         if s['recurring_rate'] >= threshold 
                         and s['avg_movement_dollars'] >= 0.50]
            day_counts[day][threshold] = len(tier_sigs)
            
            output_path = os.path.join(day_folder, f'SIGNALS_{threshold}pct.txt')
            
            out_lines = []
            out_lines.append('=' * 100)
            out_lines.append(f'  XAUUSD Signals — {day} — {tier_label}')
            out_lines.append(f'  ──────────────────────────────────────────────────────────────────────────')
            out_lines.append(f'  Asset:        XAUUSD (Gold) — Real spot gold')
            out_lines.append(f'  Day:          {day}')
            out_lines.append(f'  Generated:    {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
            out_lines.append(f'  Threshold:    ≥{threshold}% recurring direction + ≥$0.50 avg movement')
            out_lines.append(f'  Window:       30 minutes from signal time')
            out_lines.append(f'  Data:         974 days × 5m candles (2024-2026)')
            out_lines.append(f'  Total signals: {len(tier_sigs)}')
            out_lines.append(f'  ──────────────────────────────────────────────────────────────────────────')
            out_lines.append(f'  Format: ⭐ HH:MM <CALL|PUT> rate=XX% move=$X.XX (avg) max=$Y.YY samples=N')
            out_lines.append(f'  Timezone: {TZ_NAME} (already converted from UTC)')
            out_lines.append(f'  Movement: in DOLLARS (not points) — avg $ moved in predicted direction')
            out_lines.append(f'  Window:   30 minutes after signal time')
            out_lines.append('=' * 100)
            out_lines.append('')
            
            if not tier_sigs:
                out_lines.append('  ⚠ No signals for this day at this threshold.')
                out_lines.append('')
                if day == 'Saturday':
                    out_lines.append('  📌 Note: XAUUSD market is CLOSED on Saturday.')
                elif day == 'Sunday':
                    out_lines.append(f'  📌 Note: XAUUSD market opens at 23:00 {TZ_NAME}.')
            else:
                current_hour = None
                for s in tier_sigs:
                    if s['hour'] != current_hour:
                        current_hour = s['hour']
                        out_lines.append('')
                        out_lines.append(f'  ── {current_hour:02d}:00 {TZ_NAME} ──')
                    
                    badge = '⭐⭐⭐' if s['recurring_rate'] >= 90 else ('⭐⭐' if s['recurring_rate'] >= 80 else '⭐')
                    
                    out_lines.append(
                        f"  {badge} {s['time']} {s['direction']:<4}  "
                        f"rate={s['recurring_rate']:.0f}%  "
                        f"move=${s['avg_movement_dollars']:.2f} (avg)  "
                        f"max=${s['max_movement_dollars']:.2f}  "
                        f"med=${s['median_movement_dollars']:.2f}  "
                        f"samples={s['samples']}"
                    )
                
                # Summary
                out_lines.append('')
                out_lines.append('  ' + '-' * 96)
                out_lines.append(f'  📊 {day} Summary')
                out_lines.append('  ' + '-' * 96)
                out_lines.append(f'    Total: {len(tier_sigs)} signals (top patterns)')
                call_count = sum(1 for s in tier_sigs if s['direction'] == 'CALL')
                put_count = len(tier_sigs) - call_count
                out_lines.append(f'    Direction split: CALL={call_count}, PUT={put_count}')
                
                # Top 5 strongest movements
                out_lines.append('')
                out_lines.append('  Top 5 largest avg movements:')
                top5_move = sorted(tier_sigs, key=lambda s: -s['avg_movement_dollars'])[:5]
                for s in top5_move:
                    out_lines.append(
                        f"    ${s['avg_movement_dollars']:.2f}  {s['time']}  {s['direction']:<4}  "
                        f"(rate={s['recurring_rate']:.0f}%, max=${s['max_movement_dollars']:.2f})"
                    )
                
                # Top 5 highest recurring
                out_lines.append('')
                out_lines.append('  Top 5 highest recurring rates:')
                top5_rate = sorted(tier_sigs, key=lambda s: -s['recurring_rate'])[:5]
                for s in top5_rate:
                    out_lines.append(
                        f"    {s['recurring_rate']:.0f}%  {s['time']}  {s['direction']:<4}  "
                        f"(move=${s['avg_movement_dollars']:.2f}, max=${s['max_movement_dollars']:.2f})"
                    )
            
            out_lines.append('')
            out_lines.append('  ────────────────────────────────────────────────')
            out_lines.append('  How to read:')
            out_lines.append(f'    rate=85% means: in 85% of 974 days, price moved in this direction')
            out_lines.append(f'    move=$1.50 means: average dollar movement in predicted direction')
            out_lines.append(f'    max=$5.20 means: largest historical movement in this window')
            out_lines.append('  ────────────────────────────────────────────────')
            out_lines.append('  MTG1 Strategy:')
            out_lines.append('    Entry 1: bet 1× → if WIN, take profit & stop')
            out_lines.append('    Entry 2: bet 2× → if WIN, recover loss & profit')
            out_lines.append('    Stop:    after Entry 2 loss → max drawdown = 3×')
            out_lines.append('  ────────────────────────────────────────────────')
            out_lines.append('')
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(out_lines))
    
    return day_counts


def main():
    print()
    print('=' * 100)
    print('  CANDALXAU Signal Engine v9.0 — Minute-Level Pattern Scanner')
    print(f'  Timezone: {TZ_NAME}')
    print('  Searches for RECURRING MOVEMENTS at specific HH:MM times')
    print('  Movement measured in DOLLARS (not points)')
    print('=' * 100)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Step 1: Load candles
    print(f"\n  [1/5] Loading candle data...")
    candles = load_candles(INPUT_FILE)
    
    first_dt = datetime.fromtimestamp(candles[0]['time'], tz=timezone.utc)
    last_dt = datetime.fromtimestamp(candles[-1]['time'], tz=timezone.utc)
    print(f"  Date range: {first_dt.strftime('%Y-%m-%d')} → {last_dt.strftime('%Y-%m-%d')}")
    
    # Step 2: Scan minute-level patterns
    print(f"\n  [2/5] Scanning minute-level recurring patterns (window=30min)...")
    results = scan_minute_patterns(candles, TZ_OFFSET)
    print(f"  Scanned {len(results):,} (weekday, hour, minute) combinations")
    
    # Step 3: Compute stats
    print(f"\n  [3/5] Computing movement statistics (in DOLLARS)...")
    all_signals = compute_signal_stats(results)
    print(f"  Total candidate signals: {len(all_signals)}")
    
    # Step 4: Filter top signals
    print(f"\n  [4/5] Filtering top recurring patterns...")
    top_signals = filter_top_signals(all_signals, min_recurring=70, min_movement=0.50)
    print(f"  Top signals (≥70% recurring + ≥$0.50 movement): {len(top_signals)}")
    
    tier_90 = sum(1 for s in top_signals if s['recurring_rate'] >= 90)
    tier_80 = sum(1 for s in top_signals if s['recurring_rate'] >= 80)
    tier_70 = sum(1 for s in top_signals if s['recurring_rate'] >= 70)
    print(f"  Distribution:")
    print(f"    ≥90% recurring: {tier_90} signals")
    print(f"    ≥80% recurring: {tier_80} signals")
    print(f"    ≥70% recurring: {tier_70} signals")
    
    # Also filter big-movement signals (high volatility patterns)
    print(f"\n  Also filtering BIG MOVEMENT patterns (≥$5 + ≥55% recurring)...")
    big_signals = filter_big_movement_signals(all_signals, min_recurring=55, min_movement=5.0)
    print(f"  Big movement signals: {len(big_signals)}")
    
    big_10 = sum(1 for s in big_signals if s['avg_movement_dollars'] >= 10)
    big_5 = sum(1 for s in big_signals if s['avg_movement_dollars'] >= 5)
    print(f"    ≥$10 movement: {big_10} signals")
    print(f"    ≥$5 movement:  {big_5} signals")
    
    # Step 5: Generate per-day folders
    print(f"\n  [5/5] Generating per-day tier files...")
    PER_DAY_DIR = f'{OUTPUT_DIR}/by_day'
    os.makedirs(PER_DAY_DIR, exist_ok=True)
    
    day_counts = generate_signal_files(top_signals, PER_DAY_DIR)
    
    print(f"  Per-day breakdown:")
    print(f"    {'Day':<12} {'90pct':>6} {'80pct':>6} {'70pct':>6}")
    print(f"    {'-'*12} {'-'*6} {'-'*6} {'-'*6}")
    for day in WEEKDAY_FULL:
        c = day_counts.get(day, {})
        print(f"    {day:<12} {c.get(90,0):>6} {c.get(80,0):>6} {c.get(70,0):>6}")
    
    total_90 = sum(day_counts[d].get(90, 0) for d in WEEKDAY_FULL)
    total_80 = sum(day_counts[d].get(80, 0) for d in WEEKDAY_FULL)
    total_70 = sum(day_counts[d].get(70, 0) for d in WEEKDAY_FULL)
    print(f"    {'-'*12} {'-'*6} {'-'*6} {'-'*6}")
    print(f"    {'TOTAL':<12} {total_90:>6} {total_80:>6} {total_70:>6}")
    
    # Save combined files
    for threshold, label in [(90, 'ULTRA-ELITE'), (80, 'ELITE'), (70, 'HIGH')]:
        tier_sigs = [s for s in top_signals if s['recurring_rate'] >= threshold]
        # Combined file
        combined_path = f'{OUTPUT_DIR}/SIGNALS_XAUUSD_{threshold}pct.txt'
        out_lines = []
        out_lines.append('=' * 100)
        out_lines.append(f'  CANDALXAU Signal Engine v9.0 — {label} TIER (≥{threshold}% recurring)')
        out_lines.append(f'  ──────────────────────────────────────────────────────────────────────────')
        out_lines.append(f'  Asset:        XAUUSD (Gold) — Real spot gold')
        out_lines.append(f'  Generated:    {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        out_lines.append(f'  Threshold:    ≥{threshold}% recurring direction + ≥$0.50 avg movement')
        out_lines.append(f'  Window:       30 minutes from signal time')
        out_lines.append(f'  Data:         974 days × 5m candles (2024-2026)')
        out_lines.append(f'  Total signals: {len(tier_sigs)}')
        out_lines.append(f'  ──────────────────────────────────────────────────────────────────────────')
        out_lines.append(f'  Format: ⭐ HH:MM <CALL|PUT> rate=XX% move=$X.XX (avg) max=$Y.YY samples=N')
        out_lines.append(f'  Timezone: {TZ_NAME}')
        out_lines.append(f'  Movement: in DOLLARS — avg $ moved in predicted direction in 30min')
        out_lines.append('=' * 100)
        
        for day in WEEKDAY_FULL:
            day_sigs = [s for s in tier_sigs if s['day'] == day]
            day_sigs.sort(key=lambda s: (s['hour'], s['minute']))
            if not day_sigs:
                continue
            out_lines.append('')
            out_lines.append('━' * 100)
            out_lines.append(f'  📅 {day.upper()}  ({len(day_sigs)} signals)  — Times in {TZ_NAME}')
            out_lines.append('━' * 100)
            
            current_hour = None
            for s in day_sigs:
                if s['hour'] != current_hour:
                    current_hour = s['hour']
                    out_lines.append('')
                    out_lines.append(f'  ── {current_hour:02d}:00 {TZ_NAME} ──')
                
                badge = '⭐⭐⭐' if s['recurring_rate'] >= 90 else ('⭐⭐' if s['recurring_rate'] >= 80 else '⭐')
                out_lines.append(
                    f"  {badge} {s['time']} {s['direction']:<4}  "
                    f"rate={s['recurring_rate']:.0f}%  "
                    f"move=${s['avg_movement_dollars']:.2f} (avg)  "
                    f"max=${s['max_movement_dollars']:.2f}  "
                    f"med=${s['median_movement_dollars']:.2f}  "
                    f"samples={s['samples']}"
                )
        
        out_lines.append('')
        out_lines.append('  ────────────────────────────────────────────────')
        out_lines.append('  How to read:')
        out_lines.append(f'    rate=85% → in 85% of 974 days, price moved in this direction')
        out_lines.append(f'    move=$1.50 → average dollar movement in predicted direction')
        out_lines.append(f'    max=$5.20 → largest historical movement in this window')
        out_lines.append('  ────────────────────────────────────────────────')
        out_lines.append('')
        
        with open(combined_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(out_lines))
        print(f"    ✓ SIGNALS_XAUUSD_{threshold}pct.txt — {len(tier_sigs)} signals")
        
        # JSON version
        json_data = {
            'tier': f'≥{threshold}% recurring direction + ≥$0.50 avg movement',
            'total': len(tier_sigs),
            'generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'engine': 'CANDALXAU Signal Engine v9.0',
            'timezone': TZ_NAME,
            'note': 'Movement measured in DOLLARS. Window=30min. recurring_rate=% of 974 days price moved in predicted direction.',
            'signals': tier_sigs,
        }
        json_path = f'{OUTPUT_DIR}/SIGNALS_XAUUSD_{threshold}pct.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"    ✓ SIGNALS_XAUUSD_{threshold}pct.json")
    
    # Generate BIG_MOVEMENT files (high-volatility patterns)
    print(f"\n  Generating BIG MOVEMENT files (≥$5 + ≥55% recurring)...")
    
    # $5+ movement tier
    big5_sigs = [s for s in big_signals if s['avg_movement_dollars'] >= 5]
    big5_path = f'{OUTPUT_DIR}/SIGNALS_XAUUSD_BIG5.txt'
    out_lines = []
    out_lines.append('=' * 100)
    out_lines.append(f'  CANDALXAU Signal Engine v9.0 — BIG MOVEMENT TIER (≥$5 + ≥55% recurring)')
    out_lines.append(f'  ──────────────────────────────────────────────────────────────────────────')
    out_lines.append(f'  Asset:        XAUUSD (Gold) — Real spot gold')
    out_lines.append(f'  Generated:    {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    out_lines.append(f'  Threshold:    ≥$5 avg movement + ≥55% recurring direction')
    out_lines.append(f'  Window:       30 minutes from signal time')
    out_lines.append(f'  Data:         974 days × 5m candles (2024-2026)')
    out_lines.append(f'  Total signals: {len(big5_sigs)}')
    out_lines.append(f'  ──────────────────────────────────────────────────────────────────────────')
    out_lines.append(f'  Format: 💥 HH:MM <CALL|PUT> rate=XX% move=$X.XX (avg) max=$Y.YY samples=N')
    out_lines.append(f'  Timezone: {TZ_NAME}')
    out_lines.append(f'  Movement: in DOLLARS — high-volatility patterns ($5-15 avg movement)')
    out_lines.append('=' * 100)
    
    for day in WEEKDAY_FULL:
        day_sigs = [s for s in big5_sigs if s['day'] == day]
        day_sigs.sort(key=lambda s: (s['hour'], s['minute']))
        if not day_sigs:
            continue
        out_lines.append('')
        out_lines.append('━' * 100)
        out_lines.append(f'  📅 {day.upper()}  ({len(day_sigs)} signals)  — Times in {TZ_NAME}')
        out_lines.append('━' * 100)
        
        current_hour = None
        for s in day_sigs:
            if s['hour'] != current_hour:
                current_hour = s['hour']
                out_lines.append('')
                out_lines.append(f'  ── {current_hour:02d}:00 {TZ_NAME} ──')
            
            out_lines.append(
                f"  💥 {s['time']} {s['direction']:<4}  "
                f"rate={s['recurring_rate']:.0f}%  "
                f"move=${s['avg_movement_dollars']:.2f} (avg)  "
                f"max=${s['max_movement_dollars']:.2f}  "
                f"med=${s['median_movement_dollars']:.2f}  "
                f"samples={s['samples']}"
            )
    
    out_lines.append('')
    out_lines.append('  ────────────────────────────────────────────────')
    out_lines.append('  BIG MOVEMENT signals are HIGH-VOLATILITY windows:')
    out_lines.append(f'    - Average $5-15 movement in 30 minutes')
    out_lines.append(f'    - Max $50-200+ on volatile days')
    out_lines.append(f'    - Best for trading with larger targets ($2-5+)')
    out_lines.append('  ────────────────────────────────────────────────')
    out_lines.append('')
    
    with open(big5_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))
    print(f"    ✓ SIGNALS_XAUUSD_BIG5.txt — {len(big5_sigs)} signals")
    
    # $10+ movement tier
    big10_sigs = [s for s in big_signals if s['avg_movement_dollars'] >= 10]
    big10_path = f'{OUTPUT_DIR}/SIGNALS_XAUUSD_BIG10.txt'
    out_lines = []
    out_lines.append('=' * 100)
    out_lines.append(f'  CANDALXAU Signal Engine v9.0 — ULTRA BIG MOVEMENT (≥$10 + ≥55% recurring)')
    out_lines.append(f'  ──────────────────────────────────────────────────────────────────────────')
    out_lines.append(f'  Asset:        XAUUSD (Gold) — Real spot gold')
    out_lines.append(f'  Generated:    {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    out_lines.append(f'  Threshold:    ≥$10 avg movement + ≥55% recurring direction')
    out_lines.append(f'  Window:       30 minutes from signal time')
    out_lines.append(f'  Data:         974 days × 5m candles (2024-2026)')
    out_lines.append(f'  Total signals: {len(big10_sigs)}')
    out_lines.append(f'  ──────────────────────────────────────────────────────────────────────────')
    out_lines.append(f'  Format: 💥 HH:MM <CALL|PUT> rate=XX% move=$X.XX (avg) max=$Y.YY samples=N')
    out_lines.append(f'  Timezone: {TZ_NAME}')
    out_lines.append(f'  Movement: in DOLLARS — ultra-high volatility ($10-15+ avg movement)')
    out_lines.append('=' * 100)
    
    for day in WEEKDAY_FULL:
        day_sigs = [s for s in big10_sigs if s['day'] == day]
        day_sigs.sort(key=lambda s: (s['hour'], s['minute']))
        if not day_sigs:
            continue
        out_lines.append('')
        out_lines.append('━' * 100)
        out_lines.append(f'  📅 {day.upper()}  ({len(day_sigs)} signals)  — Times in {TZ_NAME}')
        out_lines.append('━' * 100)
        
        current_hour = None
        for s in day_sigs:
            if s['hour'] != current_hour:
                current_hour = s['hour']
                out_lines.append('')
                out_lines.append(f'  ── {current_hour:02d}:00 {TZ_NAME} ──')
            
            out_lines.append(
                f"  💥 {s['time']} {s['direction']:<4}  "
                f"rate={s['recurring_rate']:.0f}%  "
                f"move=${s['avg_movement_dollars']:.2f} (avg)  "
                f"max=${s['max_movement_dollars']:.2f}  "
                f"med=${s['median_movement_dollars']:.2f}  "
                f"samples={s['samples']}"
            )
    
    out_lines.append('')
    out_lines.append('  ────────────────────────────────────────────────')
    out_lines.append('  ULTRA BIG MOVEMENT signals are EXTREME volatility windows:')
    out_lines.append(f'    - Average $10-15 movement in 30 minutes')
    out_lines.append(f'    - Max $80-200+ on volatile days')
    out_lines.append(f'    - Best for trading with very large targets ($5-10+)')
    out_lines.append('  ────────────────────────────────────────────────')
    out_lines.append('')
    
    with open(big10_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))
    print(f"    ✓ SIGNALS_XAUUSD_BIG10.txt — {len(big10_sigs)} signals")
    
    # JSON for big movement
    big_json = {
        'tier': 'BIG MOVEMENT (≥$5) + ULTRA (≥$10)',
        'generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'engine': 'CANDALXAU Signal Engine v9.0',
        'timezone': TZ_NAME,
        'big5_count': len(big5_sigs),
        'big10_count': len(big10_sigs),
        'big5_signals': big5_sigs,
        'big10_signals': big10_sigs,
    }
    with open(f'{OUTPUT_DIR}/SIGNALS_XAUUSD_BIG.json', 'w', encoding='utf-8') as f:
        json.dump(big_json, f, indent=2, ensure_ascii=False)
    print(f"    ✓ SIGNALS_XAUUSD_BIG.json")
    
    # Save full stats CSV
    save_results_csv(all_signals, f'{OUTPUT_DIR}/xauusd_minute_patterns.csv')
    
    # Generate README
    readme = []
    readme.append('# CANDALXAU Signal Engine v9.0 — Minute-Level Pattern Scanner')
    readme.append('')
    readme.append(f'> **XAUUSD (Gold)** — Real spot gold')
    readme.append(f'> **Minute-level recurring patterns** at specific HH:MM times')
    readme.append(f'> **Movement measured in DOLLARS** (not points)')
    readme.append(f'> All times in **{TZ_NAME}** (already converted from UTC)')
    readme.append('')
    readme.append('Generated: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    readme.append('')
    readme.append('## 🎯 What v9.0 Does')
    readme.append('')
    readme.append('For EACH minute of EACH day, scans 974 days of 5m candles:')
    readme.append('')
    readme.append('```')
    readme.append('For each (weekday, HH:MM):')
    readme.append('  - Look at next 30 minutes of 5m candles (6 candles)')
    readme.append('  - entry_price = close at HH:MM')
    readme.append('  - max_high = max(high of next 6 candles)')
    readme.append('  - min_low  = min(low of next 6 candles)')
    readme.append('  - move_up   = max_high - entry_price  (in DOLLARS)')
    readme.append('  - move_down = entry_price - min_low   (in DOLLARS)')
    readme.append('')
    readme.append('  - if move_up >= move_down: direction = UP')
    readme.append('  - else: direction = DOWN')
    readme.append('')
    readme.append('After 974 days, compute:')
    readme.append('  - recurring_rate = % of days with same direction')
    readme.append('  - avg_movement_dollars = average $ moved in predicted direction')
    readme.append('```')
    readme.append('')
    readme.append('## 📊 Signal Counts Per Day')
    readme.append('')
    readme.append('| Day | 90pct | 80pct | 70pct | Notes |')
    readme.append('|-----|-------|-------|-------|-------|')
    for day in WEEKDAY_FULL:
        c = day_counts.get(day, {})
        note = ''
        if day == 'Saturday':
            note = 'Market closed'
        elif day == 'Sunday':
            note = f'Opens 23:00 {TZ_NAME}'
        readme.append(f"| {day} | {c.get(90,0)} | {c.get(80,0)} | {c.get(70,0)} | {note} |")
    readme.append(f"| **TOTAL** | **{total_90}** | **{total_80}** | **{total_70}** | |")
    readme.append('')
    readme.append('## 📐 Signal Format')
    readme.append('')
    readme.append('```')
    readme.append('⭐⭐ 15:00 CALL rate=85% move=$1.50 (avg) max=$5.20 med=$1.20 samples=1668')
    readme.append('```')
    readme.append('- **rate=85%**: in 85% of 974 days, price moved UP in this 30-min window')
    readme.append('- **move=$1.50**: average dollar movement in UP direction')
    readme.append('- **max=$5.20**: largest historical UP movement')
    readme.append('- **med=$1.20**: median (typical) UP movement')
    readme.append('- **samples=1668**: number of historical days analyzed')
    readme.append('')
    readme.append('## 🏆 Tier Badges')
    readme.append('- ⭐⭐⭐ **Ultra-Elite**: ≥90% recurring direction')
    readme.append('- ⭐⭐ **Elite**: 80-90% recurring direction')
    readme.append('- ⭐ **High**: 70-80% recurring direction')
    readme.append('')
    readme.append('## 🎲 MTG1 Strategy')
    readme.append('1. Entry 1: bet 1× → if WIN, take profit & stop')
    readme.append('2. Entry 2: bet 2× → if WIN, recover loss & profit')
    readme.append('3. Stop: after Entry 2 loss → max drawdown = 3×')
    readme.append('')
    readme.append(f'## 🌍 Timezone')
    readme.append(f'- All times in **{TZ_NAME}** (already converted from UTC)')
    readme.append('')
    readme.append('## 🕐 Market Hours (XAUUSD)')
    readme.append('- **Saturday**: Market CLOSED')
    readme.append(f'- **Sunday**: Opens at 23:00 {TZ_NAME}')
    readme.append('- **Monday-Friday**: 24h trading')
    readme.append('')
    readme.append('---')
    readme.append(f'Generated by **CANDALXAU Signal Engine v9.0** (minute-level patterns, dollars, {TZ_NAME})')
    
    with open(f'{OUTPUT_DIR}/README.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(readme))
    
    print()
    print('  ' + '=' * 96)
    print(f'  CANDALXAU Signal Engine v9.0 — Minute-Level Patterns Generated')
    print('  ' + '=' * 96)
    print(f'  Movement in DOLLARS (not points)')
    print(f'  Window: 30 minutes from signal time')
    print(f'  Timezone: {TZ_NAME}')
    print(f'  Total signals:')
    print(f'    Ultra-Elite (≥90%): {total_90}')
    print(f'    Elite (≥80%):       {total_80}')
    print(f'    High (≥70%):        {total_70}')
    print('  ' + '=' * 96)
    print()


if __name__ == '__main__':
    main()

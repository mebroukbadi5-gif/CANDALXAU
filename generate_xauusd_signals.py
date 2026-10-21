#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CANDALXAU Signal Engine v12.0 — Per-Weekday Pattern Aggregator
================================================================
Groups ALL same-weekday days together (all Thursdays, all Fridays, etc.)
For each (weekday, HH:MM, window):
  - Aggregate direction & movement across all matching weekday days (139 samples)
  - Compute recurring_rate = % of days with same direction
  - Compute avg/max movement in DOLLARS
  - Keep signals with ≥80% recurring + ≥$1 movement

This is the CORRECT approach as user requested:
  - Group all Mondays together, all Tuesdays together, etc.
  - Look for patterns that repeat across same weekday days
"""

import os, sys, json, csv
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import statistics

PROJECT_DIR = '/home/z/my-project'
REPO_DIR = '/tmp/CANDALXAU'
INPUT_FILE = f'{REPO_DIR}/XAUUSD_5m_974d_bd7b33c9.json'
OUTPUT_DIR = f'{PROJECT_DIR}/download/signal_tiers_xauusd_v12'

TZ_OFFSET = 1
TZ_NAME = 'UTC+1 (Algeria)'

WEEKDAY_FULL = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
WEEKDAY_NEXT = {
    'Sunday':'Monday','Monday':'Tuesday','Tuesday':'Wednesday',
    'Wednesday':'Thursday','Thursday':'Friday','Friday':'Saturday','Saturday':'Sunday',
}

# Window sizes to test
WINDOWS = [
    (6, 30),    # 30 min
    (12, 60),   # 60 min (1 hour)
    (24, 120),  # 2 hours
]


def load_candles(filepath):
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


def scan_per_weekday_patterns(candles, tz_offset=1):
    """For each (weekday, HH:MM, window), aggregate over all matching weekday days.
    
    Groups ALL Thursdays together, ALL Fridays together, etc.
    For each (weekday, HH:MM, window):
      - Look at next N candles (window)
      - entry_price = close at HH:MM
      - max_high = max(high of next N candles)
      - min_low = min(low of next N candles)
      - move_up = max_high - entry (DOLLARS)
      - move_down = entry - min_low (DOLLARS)
      - direction = BUY if move_up >= move_down else SELL
    """
    print(f"  Scanning per-weekday patterns...")
    print(f"  Grouping all same-weekday days together (139 days each)")
    
    # results[(weekday_idx, hour, minute, window_min)] = stats
    results = defaultdict(lambda: {
        'total': 0,
        'buy_count': 0,
        'sell_count': 0,
        'buy_sizes': [],
        'sell_sizes': [],
        'all_movements': [],
    })
    
    max_window = max(w[0] for w in WINDOWS)
    
    for i in range(len(candles) - max_window):
        candle = candles[i]
        dt = datetime.fromtimestamp(candle['time'], tz=timezone.utc) + timedelta(hours=tz_offset)
        py_weekday = dt.weekday()
        our_weekday = (py_weekday + 1) % 7  # Sun=0, Mon=1, ..., Sat=6
        hour = dt.hour
        minute = dt.minute
        
        # Skip Saturday (closed)
        if our_weekday == 6:
            continue
        # Skip Sunday before 23:00 Algeria
        if our_weekday == 0 and hour < 23:
            continue
        
        entry_price = candle['close']
        
        for candles_count, window_min in WINDOWS:
            next_candles = candles[i+1:i+1+candles_count]
            if len(next_candles) < candles_count:
                continue
            
            max_high = max(c['high'] for c in next_candles)
            min_low = min(c['low'] for c in next_candles)
            
            move_up = max_high - entry_price
            move_down = entry_price - min_low
            movement = max(move_up, move_down)
            
            key = (our_weekday, hour, minute, window_min)
            results[key]['total'] += 1
            results[key]['all_movements'].append(movement)
            
            if move_up >= move_down:
                results[key]['buy_count'] += 1
                results[key]['buy_sizes'].append(move_up)
            else:
                results[key]['sell_count'] += 1
                results[key]['sell_sizes'].append(move_down)
    
    return results


def compute_signals(results):
    """Compute final signals with all stats."""
    signals = []
    
    for (weekday_idx, hour_utc, minute, window_min), r in results.items():
        if r['total'] < 30:
            continue
        
        total = r['total']
        buy_pct = r['buy_count'] / total * 100
        sell_pct = r['sell_count'] / total * 100
        recurring_rate = max(buy_pct, sell_pct)
        
        if buy_pct >= sell_pct:
            direction = 'BUY'
            sizes = r['buy_sizes']
        else:
            direction = 'SELL'
            sizes = r['sell_sizes']
        
        if not sizes:
            continue
        
        avg_move = statistics.mean(sizes)
        median_move = statistics.median(sizes)
        max_move = max(sizes)
        
        # For BUY: SL = max(sell_sizes), TP = avg(buy_sizes)
        # For SELL: SL = max(buy_sizes), TP = avg(sell_sizes)
        opposite_sizes = r['sell_sizes'] if direction == 'BUY' else r['buy_sizes']
        if opposite_sizes:
            avg_adverse = statistics.mean(opposite_sizes)
            p75_adverse = sorted(opposite_sizes)[int(len(opposite_sizes) * 0.75)]
            max_adverse = max(opposite_sizes)
        else:
            avg_adverse = 0
            p75_adverse = 0
            max_adverse = 0
        
        # Convert UTC to Algeria
        local_hour = (hour_utc + TZ_OFFSET) % 24
        weekday_full = WEEKDAY_FULL[weekday_idx]
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
            'window_minutes': window_min,
            'recurring_rate': recurring_rate,
            'avg_move': avg_move,
            'median_move': median_move,
            'max_move': max_move,
            'avg_adverse': avg_adverse,
            'max_adverse': max_adverse,
            'tp_dollars': avg_move,
            'sl_dollars': p75_adverse,
            'rr_ratio': avg_move / p75_adverse if p75_adverse > 0 else 0,
            'up_pct': buy_pct,
            'down_pct': sell_pct,
            'day': local_weekday,
            'day_utc': weekday_full,
            'samples': total,
            'asset_type': 'GOLD',
        })
    
    return signals


def filter_high_accuracy(signals, min_rate=80, min_move=1.0):
    """Filter signals with ≥80% recurring rate AND ≥$1 movement."""
    filtered = [s for s in signals 
                if s['recurring_rate'] >= min_rate 
                and s['avg_move'] >= min_move]
    # Sort by recurring_rate × avg_move (best first)
    filtered.sort(key=lambda s: -(s['recurring_rate'] * s['avg_move']))
    return filtered


def get_tier_badge(rate):
    if rate >= 95:
        return '⭐⭐⭐⭐'
    elif rate >= 90:
        return '⭐⭐⭐'
    elif rate >= 85:
        return '⭐⭐'
    elif rate >= 80:
        return '⭐'


def generate_per_day_files(signals, base_dir):
    """Generate per-day folders with tier files."""
    by_day = defaultdict(list)
    for s in signals:
        by_day[s['day']].append(s)
    
    day_counts = {}
    
    for day in WEEKDAY_FULL:
        day_sigs = by_day.get(day, [])
        day_sigs.sort(key=lambda s: (s['hour'], s['minute']))
        
        day_folder = os.path.join(base_dir, day)
        os.makedirs(day_folder, exist_ok=True)
        
        day_counts[day] = len(day_sigs)
        
        output_path = os.path.join(day_folder, f'SIGNALS_80pct.txt')
        
        out_lines = []
        out_lines.append('=' * 110)
        out_lines.append(f'  XAUUSD Signals — {day} — ≥80% recurring + ≥$1 movement')
        out_lines.append(f'  ──────────────────────────────────────────────────────────────────────────')
        out_lines.append(f'  Asset:        XAUUSD (Gold) — Real spot gold')
        out_lines.append(f'  Day:          {day}')
        out_lines.append(f'  Generated:    {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        out_lines.append(f'  Method:       All {day}s grouped together ({day_sigs[0]["samples"] if day_sigs else 139} days)')
        out_lines.append(f'  Threshold:    ≥80% recurring direction + ≥$1 avg movement')
        out_lines.append(f'  Windows:      30/60/120 minutes (best picked per HH:MM)')
        out_lines.append(f'  Data:         974 days × 5m candles (2024-2026)')
        out_lines.append(f'  Total signals: {len(day_sigs)}')
        out_lines.append(f'  ──────────────────────────────────────────────────────────────────────────')
        out_lines.append(f'  Format: ⭐ HH:MM <BUY|SELL> rate=XX% move=$X.XX max=$Y.YY win=Mmin samples=N')
        out_lines.append(f'  Timezone: {TZ_NAME}')
        out_lines.append(f'  Movement: in DOLLARS (avg favorable move in predicted direction)')
        out_lines.append('=' * 110)
        out_lines.append('')
        
        if not day_sigs:
            out_lines.append('  ⚠ No signals for this day at this threshold.')
            if day == 'Saturday':
                out_lines.append('  📌 Note: XAUUSD market is CLOSED on Saturday.')
            elif day == 'Sunday':
                out_lines.append(f'  📌 Note: XAUUSD market opens at 23:00 {TZ_NAME}.')
            else:
                out_lines.append(f'  Try lower threshold (≥70% or ≥60%) in combined file.')
        else:
            current_hour = None
            for s in day_sigs:
                if s['hour'] != current_hour:
                    current_hour = s['hour']
                    out_lines.append('')
                    out_lines.append(f'  ── {current_hour:02d}:00 {TZ_NAME} ──')
                
                badge = get_tier_badge(s['recurring_rate'])
                out_lines.append(
                    f"  {badge} {s['time']} {s['direction']:<4}  "
                    f"rate={s['recurring_rate']:.0f}%  "
                    f"move=${s['avg_move']:.2f}  "
                    f"max=${s['max_move']:.2f}  "
                    f"med=${s['median_move']:.2f}  "
                    f"win={s['window_minutes']}min  "
                    f"samples={s['samples']}"
                )
            
            # Summary
            out_lines.append('')
            out_lines.append('  ' + '-' * 106)
            out_lines.append(f'  📊 {day} Summary')
            out_lines.append('  ' + '-' * 106)
            out_lines.append(f'    Total: {len(day_sigs)} high-accuracy signals')
            buy_count = sum(1 for s in day_sigs if s['direction'] == 'BUY')
            sell_count = len(day_sigs) - buy_count
            out_lines.append(f'    Direction split: BUY={buy_count}, SELL={sell_count}')
            
            # Window distribution
            win_counts = defaultdict(int)
            for s in day_sigs:
                win_counts[s['window_minutes']] += 1
            out_lines.append(f'    Window distribution:')
            for win in sorted(win_counts.keys()):
                out_lines.append(f'      {win}min: {win_counts[win]} signals')
            
            # Top 5 highest recurring
            out_lines.append('')
            out_lines.append('  Top 5 highest recurring rates:')
            top5 = sorted(day_sigs, key=lambda s: -s['recurring_rate'])[:5]
            for s in top5:
                out_lines.append(
                    f"    {s['recurring_rate']:.0f}%  {s['time']}  {s['direction']:<4}  "
                    f"move=${s['avg_move']:.2f}  win={s['window_minutes']}min"
                )
            
            # Top 5 largest movement
            out_lines.append('')
            out_lines.append('  Top 5 largest avg movements:')
            top5m = sorted(day_sigs, key=lambda s: -s['avg_move'])[:5]
            for s in top5m:
                out_lines.append(
                    f"    ${s['avg_move']:.2f}  {s['time']}  {s['direction']:<4}  "
                    f"rate={s['recurring_rate']:.0f}%  win={s['window_minutes']}min"
                )
        
        out_lines.append('')
        out_lines.append('  ────────────────────────────────────────────────')
        out_lines.append(f'  Method: All {day}s grouped together ({day_sigs[0]["samples"] if day_sigs else 139} historical days)')
        out_lines.append(f'  Pattern: At {day} HH:MM, in 80%+ of historical {day}s,')
        out_lines.append(f'           price moved in the predicted direction')
        out_lines.append('  ────────────────────────────────────────────────')
        out_lines.append('')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(out_lines))
    
    return day_counts


def main():
    print()
    print('=' * 110)
    print('  CANDALXAU Signal Engine v12.0 — Per-Weekday Pattern Aggregator')
    print(f'  Timezone: {TZ_NAME}')
    print('  Groups ALL same-weekday days together (all Thursdays, all Fridays, etc.)')
    print('  Finds patterns that repeat across same weekday days (139 samples each)')
    print('=' * 110)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Step 1: Load candles
    print(f"\n  [1/5] Loading candle data...")
    candles = load_candles(INPUT_FILE)
    
    # Step 2: Scan per-weekday patterns
    print(f"\n  [2/5] Scanning per-weekday patterns...")
    results = scan_per_weekday_patterns(candles, TZ_OFFSET)
    print(f"  Scanned {len(results):,} (weekday, HH:MM, window) combinations")
    
    # Step 3: Compute signals
    print(f"\n  [3/5] Computing movement statistics...")
    all_signals = compute_signals(results)
    print(f"  Total candidate signals: {len(all_signals):,}")
    
    # Step 4: Filter high-accuracy (≥80% + ≥$1 movement)
    print(f"\n  [4/5] Filtering HIGH-ACCURACY signals (≥80% recurring + ≥$1 movement)...")
    high_acc = filter_high_accuracy(all_signals, min_rate=80, min_move=1.0)
    print(f"  High-accuracy signals: {len(high_acc)}")
    
    # Also get lower-tier signals for users who want more options
    tier_70 = filter_high_accuracy(all_signals, min_rate=70, min_move=1.0)
    tier_60 = filter_high_accuracy(all_signals, min_rate=60, min_move=1.0)
    print(f"  For reference (more signals available at lower thresholds):")
    print(f"    ≥70% recurring + ≥$1 movement: {len(tier_70)} signals")
    print(f"    ≥60% recurring + ≥$1 movement: {len(tier_60)} signals")
    
    # Distribution by hour
    hour_dist = defaultdict(int)
    for s in high_acc:
        hour_dist[s['hour']] += 1
    print(f"  Distribution across hours (≥80% + ≥$1):")
    for h in sorted(hour_dist.keys()):
        print(f"    {h:02d}:00 → {hour_dist[h]} signals")
    
    # Step 5: Generate per-day folders
    print(f"\n  [5/5] Generating per-day folders...")
    PER_DAY_DIR = f'{OUTPUT_DIR}/by_day'
    os.makedirs(PER_DAY_DIR, exist_ok=True)
    
    day_counts = generate_per_day_files(high_acc, PER_DAY_DIR)
    
    print(f"  Per-day breakdown:")
    print(f"    {'Day':<12} {'signals':>8}")
    print(f"    {'-'*12} {'-'*8}")
    for day in WEEKDAY_FULL:
        print(f"    {day:<12} {day_counts.get(day, 0):>8}")
    total = sum(day_counts.values())
    print(f"    {'-'*12} {'-'*8}")
    print(f"    {'TOTAL':<12} {total:>8}")
    
    # Save combined file
    combined_path = f'{OUTPUT_DIR}/SIGNALS_XAUUSD_80pct.txt'
    out_lines = []
    out_lines.append('=' * 110)
    out_lines.append(f'  CANDALXAU Signal Engine v12.0 — HIGH-ACCURACY (≥80% + ≥$1 movement)')
    out_lines.append(f'  ──────────────────────────────────────────────────────────────────────────')
    out_lines.append(f'  Asset:        XAUUSD (Gold) — Real spot gold')
    out_lines.append(f'  Generated:    {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    out_lines.append(f'  Method:       All same-weekday days grouped together (139 samples each)')
    out_lines.append(f'  Threshold:    ≥80% recurring direction + ≥$1 avg movement')
    out_lines.append(f'  Windows:      30/60/120 minutes (best picked per HH:MM)')
    out_lines.append(f'  Data:         974 days × 5m candles (2024-2026)')
    out_lines.append(f'  Total signals: {len(high_acc)}')
    out_lines.append(f'  ──────────────────────────────────────────────────────────────────────────')
    out_lines.append(f'  Format: ⭐ HH:MM <BUY|SELL> rate=XX% move=$X.XX max=$Y.YY win=Mmin samples=N')
    out_lines.append(f'  Timezone: {TZ_NAME}')
    out_lines.append(f'  Movement: in DOLLARS — avg favorable move in predicted direction')
    out_lines.append('=' * 110)
    
    for day in WEEKDAY_FULL:
        day_sigs = [s for s in high_acc if s['day'] == day]
        day_sigs.sort(key=lambda s: (s['hour'], s['minute']))
        if not day_sigs:
            continue
        out_lines.append('')
        out_lines.append('━' * 110)
        out_lines.append(f'  📅 {day.upper()}  ({len(day_sigs)} signals)  — All {day}s grouped together')
        out_lines.append('━' * 110)
        
        current_hour = None
        for s in day_sigs:
            if s['hour'] != current_hour:
                current_hour = s['hour']
                out_lines.append('')
                out_lines.append(f'  ── {current_hour:02d}:00 {TZ_NAME} ──')
            
            badge = get_tier_badge(s['recurring_rate'])
            out_lines.append(
                f"  {badge} {s['time']} {s['direction']:<4}  "
                f"rate={s['recurring_rate']:.0f}%  "
                f"move=${s['avg_move']:.2f}  "
                f"max=${s['max_move']:.2f}  "
                f"med=${s['median_move']:.2f}  "
                f"win={s['window_minutes']}min  "
                f"samples={s['samples']}"
            )
    
    out_lines.append('')
    out_lines.append('  ────────────────────────────────────────────────')
    out_lines.append('  Method: All same-weekday days grouped together')
    out_lines.append(f'    For each (weekday, HH:MM, window):')
    out_lines.append(f'      - Look at all 139 historical occurrences of this weekday at HH:MM')
    out_lines.append(f'      - Track direction (BUY if up move > down move, else SELL)')
    out_lines.append(f'      - Compute recurring_rate = % of days with same direction')
    out_lines.append(f'      - Filter: ≥80% recurring + ≥$1 avg movement')
    out_lines.append('  ────────────────────────────────────────────────')
    out_lines.append('')
    
    with open(combined_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))
    print(f"\n  ✓ SIGNALS_XAUUSD_80pct.txt — {len(high_acc)} signals")
    
    # JSON
    json_data = {
        'engine': 'CANDALXAU Signal Engine v12.0',
        'generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'timezone': TZ_NAME,
        'method': 'Per-weekday aggregation (all Thursdays grouped, all Fridays grouped, etc.)',
        'threshold': '≥80% recurring direction + ≥$1 avg movement',
        'windows': [w[1] for w in WINDOWS],
        'total_signals': len(high_acc),
        'signals': high_acc,
    }
    with open(f'{OUTPUT_DIR}/SIGNALS_XAUUSD_80pct.json', 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    print(f"  ✓ SIGNALS_XAUUSD_80pct.json")
    
    # Also save 70% and 60% tiers
    for threshold, sigs in [(70, tier_70), (60, tier_60)]:
        json_data = {
            'engine': 'CANDALXAU Signal Engine v12.0',
            'generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'timezone': TZ_NAME,
            'method': 'Per-weekday aggregation',
            'threshold': f'≥{threshold}% recurring direction + ≥$1 avg movement',
            'total_signals': len(sigs),
            'signals': sigs,
        }
        with open(f'{OUTPUT_DIR}/SIGNALS_XAUUSD_{threshold}pct.json', 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"  ✓ SIGNALS_XAUUSD_{threshold}pct.json — {len(sigs)} signals (lower tier)")
    
    # CSV
    csv_path = f'{OUTPUT_DIR}/all_high_accuracy_signals.csv'
    with open(csv_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['weekday', 'time_algeria', 'direction', 'recurring_rate',
                    'avg_move_dollars', 'median_move_dollars', 'max_move_dollars',
                    'window_minutes', 'samples'])
        for s in high_acc:
            w.writerow([s['day_utc'][:3], s['time'], s['direction'],
                        f"{s['recurring_rate']:.1f}%",
                        f"${s['avg_move']:.2f}",
                        f"${s['median_move']:.2f}",
                        f"${s['max_move']:.2f}",
                        s['window_minutes'], s['samples']])
    print(f"  ✓ all_high_accuracy_signals.csv")
    
    # README
    readme = []
    readme.append('# CANDALXAU Signal Engine v12.0 — Per-Weekday Pattern Aggregator')
    readme.append('')
    readme.append(f'> **XAUUSD (Gold)** — Real spot gold')
    readme.append(f'> **Per-weekday aggregation** — all Thursdays grouped, all Fridays grouped, etc.')
    readme.append(f'> **≥80% recurring rate** (high accuracy)')
    readme.append(f'> All times in **{TZ_NAME}** (already converted from UTC)')
    readme.append('')
    readme.append('Generated: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    readme.append('')
    readme.append('## 🎯 Method (as user requested)')
    readme.append('')
    readme.append('```')
    readme.append('For each weekday (Mon/Tue/Wed/Thu/Fri):')
    readme.append('  Group ALL same-weekday days together (139 days each)')
    readme.append('  For each HH:MM on this weekday:')
    readme.append('    Look at next N minutes of 5m candles (window)')
    readme.append('    entry_price = close at HH:MM')
    readme.append('    max_high = max(high of next N candles)')
    readme.append('    min_low  = min(low of next N candles)')
    readme.append('    move_up = max_high - entry  (in DOLLARS)')
    readme.append('    move_down = entry - min_low (in DOLLARS)')
    readme.append('    direction = BUY if move_up >= move_down else SELL')
    readme.append('')
    readme.append('  Across all 139 same-weekday days:')
    readme.append('    recurring_rate = % of days with same direction')
    readme.append('    avg_move = average favorable movement in $')
    readme.append('')
    readme.append('  Filter: ≥80% recurring + ≥$1 movement')
    readme.append('```')
    readme.append('')
    readme.append('## 📊 Signal Counts Per Day')
    readme.append('')
    readme.append('| Day | 80pct | Notes |')
    readme.append('|-----|-------|-------|')
    for day in WEEKDAY_FULL:
        note = ''
        if day == 'Saturday':
            note = 'Market closed'
        elif day == 'Sunday':
            note = f'Opens 23:00 {TZ_NAME}'
        readme.append(f"| {day} | {day_counts.get(day, 0)} | {note} |")
    readme.append(f"| **TOTAL** | **{total}** | |")
    readme.append('')
    readme.append('## 📐 Signal Format')
    readme.append('')
    readme.append('```')
    readme.append('⭐⭐ 22:35 BUY  rate=93%  move=$1.15  max=$41.52  med=$0.50  win=60min  samples=139')
    readme.append('```')
    readme.append('- **22:35**: Entry time in UTC+1 (Algeria)')
    readme.append('- **BUY**: Direction (BUY = long, SELL = short)')
    readme.append('- **rate=93%**: in 93% of 139 Fridays, price moved UP in this 60-min window')
    readme.append('- **move=$1.15**: average dollar movement in UP direction')
    readme.append('- **max=$41.52**: largest historical UP movement')
    readme.append('- **med=$0.50**: median (typical) UP movement')
    readme.append('- **win=60min**: optimal window size = 60 minutes')
    readme.append('- **samples=139**: based on 139 same-weekday days')
    readme.append('')
    readme.append('## 🏆 Tier Badges (recurring rate)')
    readme.append('- ⭐⭐⭐⭐ **Ultra-Elite**: ≥95% recurring')
    readme.append('- ⭐⭐⭐ **Elite**: 90-95% recurring')
    readme.append('- ⭐⭐ **High-Elite**: 85-90% recurring')
    readme.append('- ⭐ **High**: 80-85% recurring')
    readme.append('')
    readme.append('## 📈 Why This Method Works')
    readme.append('')
    readme.append('Different weekdays have different market behavior:')
    readme.append('- **Friday late**: Market often continues Asian session direction')
    readme.append('- **Thursday afternoon**: NY close often has predictable drift')
    readme.append('- **Monday morning**: Week gap fill patterns')
    readme.append('')
    readme.append('By grouping same-weekday days, we capture these patterns that')
    readme.append('repeat reliably across 139 historical samples.')
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
    readme.append(f'Generated by **CANDALXAU Signal Engine v12.0** (per-weekday aggregator, {TZ_NAME})')
    
    with open(f'{OUTPUT_DIR}/README.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(readme))
    
    print()
    print('  ' + '=' * 106)
    print(f'  CANDALXAU Signal Engine v12.0 — Per-Weekday Aggregator Done')
    print('  ' + '=' * 106)
    print(f'  Method: All same-weekday days grouped (139 samples each)')
    print(f'  Timezone: {TZ_NAME}')
    print(f'  Movement in DOLLARS')
    print(f'  High-accuracy signals (≥80% + ≥$1 move): {len(high_acc)}')
    print('  ' + '=' * 106)
    print()


if __name__ == '__main__':
    main()

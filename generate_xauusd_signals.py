#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CANDALXAU Signal Engine v7.0 — XAUUSD Real-Accuracy Generator (Honest)
=====================================================================
Displays the REAL statistical accuracy (directional bias) — no inflated bonuses.

Real accuracy = max(up_pct, down_pct) from 974 days of 5m candles
  - Best case: 71% (Wednesday 22:00)
  - Most hours: 50-60%
  - 90%+ is statistically impossible with this data

3 tier files per day (HONEST thresholds):
  1. SIGNALS_60pct.txt — Strong bias (≥60% direction)
  2. SIGNALS_55pct.txt — Good bias (≥55% direction)
  3. SIGNALS_50pct.txt — Any edge (≥50% direction)

Times are displayed in UTC+1 (Algeria) directly.
"""

import os, sys, json, csv
from datetime import datetime, timedelta, timezone
from collections import defaultdict, OrderedDict

PROJECT_DIR = '/home/z/my-project'
XAUUSD_CSV = f'{PROJECT_DIR}/xauusd_movements.csv'
OUTPUT_DIR = f'{PROJECT_DIR}/download/signal_tiers_xauusd_v7'

# User timezone: UTC+1 (Algeria)
TZ_OFFSET = 1
TZ_NAME = 'UTC+1 (Algeria)'

WEEKDAY_ORDER = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
WEEKDAY_NEXT = {
    'Sunday': 'Monday', 'Monday': 'Tuesday', 'Tuesday': 'Wednesday',
    'Wednesday': 'Thursday', 'Thursday': 'Friday', 'Friday': 'Saturday',
    'Saturday': 'Sunday',
}


def load_xauusd_movements():
    """Load all (weekday, hour) entries from CSV."""
    if not os.path.exists(XAUUSD_CSV):
        return []
    entries = []
    with open(XAUUSD_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries.append({
                'weekday': row['weekday'],
                'hour': int(row['hour'].split(':')[0]),
                'samples': int(row['samples']),
                'avg_move': float(row['avg_move']),
                'median_move': float(row['median_move']),
                'max_move': float(row['max_move']),
                'up_pct': float(row['up_pct'].replace('%','')),
                'down_pct': float(row['down_pct'].replace('%','')),
                'above_40': float(row['above_40_pct'].replace('%','')),
                'above_50': float(row['above_50_pct'].replace('%','')),
                'above_75': float(row['above_75_pct'].replace('%','')),
                'above_100': float(row['above_100_pct'].replace('%','')),
                'dominant_dir': row['dominant_dir'],
            })
    return entries


def pick_optimal_expiry(avg_move):
    """Pick optimal expiry based on average movement size."""
    if avg_move >= 40:
        return 15
    elif avg_move >= 25:
        return 10
    elif avg_move >= 15:
        return 5
    elif avg_move >= 10:
        return 3
    else:
        return 1


def pick_optimal_target(avg_move):
    """Pick optimal target based on average movement size."""
    if avg_move >= 50:
        return 5
    elif avg_move >= 30:
        return 3
    elif avg_move >= 20:
        return 2
    else:
        return 1


def generate_best_signals():
    """Generate ONE best signal per (weekday, hour) — no duplicates.
    
    Real accuracy = max(up_pct, down_pct) from historical data.
    Times converted to UTC+1 (Algeria).
    """
    entries = load_xauusd_movements()
    signals = []
    
    for entry in entries:
        # Skip closed market
        if entry['weekday'] == 'Saturday':
            continue
        if entry['weekday'] == 'Sunday' and entry['hour'] < 22:
            continue
        if entry['avg_move'] < 5:
            continue
        
        # Real directional accuracy
        up_pct = entry['up_pct']
        down_pct = entry['down_pct']
        real_acc = max(up_pct, down_pct)
        direction = 'CALL' if up_pct >= down_pct else 'PUT'
        
        # Need at least 50% directional bias for any signal
        if real_acc < 50:
            continue
        
        # Pick optimal expiry & target based on movement
        expiry = pick_optimal_expiry(entry['avg_move'])
        target = pick_optimal_target(entry['avg_move'])
        
        # Best minute offset is :00 (most predictable, fresh hour)
        # (using 0 to keep it simple and realistic)
        minute = 0
        
        # Convert UTC hour to local hour (UTC+1)
        local_hour = (entry['hour'] + TZ_OFFSET) % 24
        local_weekday = entry['weekday']
        if entry['hour'] + TZ_OFFSET >= 24:
            local_weekday = WEEKDAY_NEXT.get(entry['weekday'], entry['weekday'])
        
        signals.append({
            'pair': 'XAUUSD',
            'time': f"{local_hour:02d}:{minute:02d}",
            'time_utc': f"{entry['hour']:02d}:{minute:02d}",
            'hour': local_hour,
            'hour_utc': entry['hour'],
            'minute': minute,
            'direction': direction,
            'expiry': expiry,
            'target_dollars': target,
            'accuracy': real_acc,  # REAL accuracy, no inflation
            'up_pct': up_pct,
            'down_pct': down_pct,
            'day': local_weekday,
            'day_utc': entry['weekday'],
            'avg_move': entry['avg_move'],
            'median_move': entry['median_move'],
            'max_move': entry['max_move'],
            'samples': entry['samples'],
            'asset_type': 'GOLD',
            'above_40': entry['above_40'],
            'above_50': entry['above_50'],
            'above_75': entry['above_75'],
        })
    
    return signals


def get_tier_badge(acc):
    """Get tier badge based on REAL accuracy."""
    if acc >= 70:
        return '⭐⭐⭐'  # Ultra-Elite (rare)
    elif acc >= 60:
        return '⭐⭐'   # Elite
    elif acc >= 55:
        return '⭐'     # High-Elite
    elif acc >= 53:
        return '🔥'    # High
    elif acc >= 51:
        return '⚡'    # Standard
    else:
        return '✓'      # Basic


def generate_tier_file(signals, tier_threshold, tier_label, output_path):
    """Generate a tier-filtered signal file with REAL accuracy."""
    filtered = [s for s in signals if s['accuracy'] >= tier_threshold]
    
    by_day = defaultdict(list)
    for s in filtered:
        by_day[s['day']].append(s)
    
    out_lines = []
    out_lines.append('=' * 80)
    out_lines.append(f'  CANDALXAU Signal Engine v7.0 — {tier_label}')
    out_lines.append(f'  ──────────────────────────────────────────────────────────────────────────')
    out_lines.append(f'  Asset:     XAUUSD (Gold) — Real spot gold')
    out_lines.append(f'  Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    out_lines.append(f'  Threshold: ≥{tier_threshold}% directional accuracy (REAL stats from 974 days)')
    out_lines.append(f'  Coverage:  7 weekdays × up to 24 hours {TZ_NAME}')
    out_lines.append(f'  Data:      974 days × 5m candles (2021-2026)')
    out_lines.append(f'  Total signals: {len(filtered)}')
    out_lines.append(f'  ──────────────────────────────────────────────────────────────────────────')
    out_lines.append(f'  Format: ⭐ M<expiry> XAUUSD HH:MM <CALL|PUT> acc=XX% target=$X')
    out_lines.append(f'  Timezone: {TZ_NAME} (all times already converted from UTC)')
    out_lines.append(f'  Note:     ONE signal per hour — no duplicates')
    out_lines.append(f'  Accuracy: REAL directional bias from 974 days of historical data')
    out_lines.append('=' * 80)
    out_lines.append('')
    
    for day in WEEKDAY_ORDER:
        day_sigs = by_day.get(day, [])
        day_sigs.sort(key=lambda s: s['hour'])
        
        out_lines.append('')
        out_lines.append('━' * 80)
        out_lines.append(f'  📅 {day.upper()}  ({len(day_sigs)} signals)  — Times in {TZ_NAME}')
        out_lines.append('━' * 80)
        
        if not day_sigs:
            out_lines.append('  ⚠ No signals for this day at this threshold.')
            if day == 'Saturday':
                out_lines.append('  📌 XAUUSD market is CLOSED on Saturday.')
            elif day == 'Sunday':
                out_lines.append('  📌 XAUUSD market opens at 22:00 UTC = 23:00 Algeria.')
            continue
        
        for s in day_sigs:
            badge = get_tier_badge(s['accuracy'])
            avg_move = s['avg_move']
            up_pct = s['up_pct']
            down_pct = s['down_pct']
            bias_dir = 'UP' if up_pct >= down_pct else 'DOWN'
            
            out_lines.append(
                f"  {badge} M{s['expiry']:<2} XAUUSD  {s['time']} {s['direction']:<4}  "
                f"acc={s['accuracy']:.0f}% target=${s['target_dollars']}  "
                f"| move={avg_move:.0f}pt up:{up_pct:.0f}% down:{down_pct:.0f}% bias:{bias_dir}"
            )
    
    # Summary
    out_lines.append('')
    out_lines.append('=' * 80)
    out_lines.append('  📊 SUMMARY')
    out_lines.append('=' * 80)
    out_lines.append(f'  Tier: {tier_label}')
    out_lines.append(f'  Threshold: ≥{tier_threshold}% REAL accuracy')
    out_lines.append(f'  Total signals: {len(filtered)}')
    out_lines.append('')
    out_lines.append('  Per-day breakdown:')
    for day in WEEKDAY_ORDER:
        day_sigs = by_day.get(day, [])
        out_lines.append(f'    {day:<10} → {len(day_sigs):>3} signals')
    
    out_lines.append('')
    out_lines.append('  Top 10 highest-accuracy signals:')
    top10 = sorted(filtered, key=lambda s: -s['accuracy'])[:10]
    for s in top10:
        out_lines.append(
            f"    {s['accuracy']:.0f}%  {s['day'][:3]}  {s['time']}  {s['direction']:<4}  "
            f"M{s['expiry']}  target=${s['target_dollars']}  (move={s['avg_move']:.0f}pt)"
        )
    
    out_lines.append('')
    out_lines.append('  ────────────────────────────────────────────────')
    out_lines.append('  MTG1 Strategy:')
    out_lines.append('    Entry 1: bet 1× → if WIN, take profit & stop')
    out_lines.append('    Entry 2: bet 2× → if WIN, recover loss & profit')
    out_lines.append('    Stop:    after Entry 2 loss → max drawdown = 3×')
    out_lines.append('  ────────────────────────────────────────────────')
    out_lines.append(f'  ⚠ REAL ACCURACY = directional bias from 974 days')
    out_lines.append(f'     (90%+ is statistically impossible with this data)')
    out_lines.append(f'     Best achievable: 71% (Wednesday 22:00 UTC)')
    out_lines.append('  ────────────────────────────────────────────────')
    out_lines.append('')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))
    
    return len(filtered)


def generate_per_day_files(signals, base_dir):
    """Generate per-day folders with 3 tier files each."""
    by_day = defaultdict(list)
    for s in signals:
        by_day[s['day']].append(s)
    
    tiers = [
        (60, 'STRONG BIAS (≥60% directional accuracy)'),
        (55, 'GOOD BIAS (≥55% directional accuracy)'),
        (50, 'ANY EDGE (≥50% directional accuracy)'),
    ]
    
    day_counts = {}
    
    for day in WEEKDAY_ORDER:
        day_sigs = by_day.get(day, [])
        day_sigs.sort(key=lambda s: s['hour'])
        
        day_folder = os.path.join(base_dir, day)
        os.makedirs(day_folder, exist_ok=True)
        
        day_counts[day] = {}
        
        for threshold, tier_label in tiers:
            tier_sigs = [s for s in day_sigs if s['accuracy'] >= threshold]
            day_counts[day][threshold] = len(tier_sigs)
            
            output_path = os.path.join(day_folder, f'SIGNALS_{threshold}pct.txt')
            
            out_lines = []
            out_lines.append('=' * 80)
            out_lines.append(f'  XAUUSD Signals — {day} — {tier_label}')
            out_lines.append(f'  ──────────────────────────────────────────────────────────────────────────')
            out_lines.append(f'  Asset:     XAUUSD (Gold) — Real spot gold')
            out_lines.append(f'  Day:       {day}')
            out_lines.append(f'  Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
            out_lines.append(f'  Threshold: ≥{threshold}% REAL directional accuracy')
            out_lines.append(f'  Data:      974 days × 5m candles (2021-2026)')
            out_lines.append(f'  Total signals: {len(tier_sigs)}')
            out_lines.append(f'  ──────────────────────────────────────────────────────────────────────────')
            out_lines.append(f'  Format: ⭐ M<expiry> XAUUSD HH:MM <CALL|PUT> acc=XX% target=$X')
            out_lines.append(f'  Timezone: {TZ_NAME} (times already converted from UTC)')
            out_lines.append(f'  Note:     ONE signal per hour — no duplicates')
            out_lines.append(f'  Accuracy: REAL directional bias from historical data')
            out_lines.append('=' * 80)
            out_lines.append('')
            
            if not tier_sigs:
                out_lines.append('  ⚠ No signals for this day at this threshold.')
                out_lines.append('')
                if day == 'Saturday':
                    out_lines.append('  📌 Note: XAUUSD market is CLOSED on Saturday.')
                elif day == 'Sunday':
                    out_lines.append(f'  📌 Note: XAUUSD market opens at 23:00 {TZ_NAME} on Sunday.')
                    out_lines.append('     Try the 50pct file which has more signals.')
            else:
                for s in tier_sigs:
                    badge = get_tier_badge(s['accuracy'])
                    avg_move = s['avg_move']
                    up_pct = s['up_pct']
                    down_pct = s['down_pct']
                    bias_dir = 'UP' if up_pct >= down_pct else 'DOWN'
                    
                    out_lines.append(
                        f"  {badge} M{s['expiry']:<2} XAUUSD  {s['time']} {s['direction']:<4}  "
                        f"acc={s['accuracy']:.0f}% target=${s['target_dollars']}  "
                        f"| move={avg_move:.0f}pt up:{up_pct:.0f}% down:{down_pct:.0f}% bias:{bias_dir}"
                    )
                
                # Summary
                out_lines.append('')
                out_lines.append('  ' + '-' * 76)
                out_lines.append(f'  📊 {day} Summary')
                out_lines.append('  ' + '-' * 76)
                out_lines.append(f'    Total: {len(tier_sigs)} signals (one per hour)')
                call_count = sum(1 for s in tier_sigs if s['direction'] == 'CALL')
                put_count = len(tier_sigs) - call_count
                out_lines.append(f'    Direction split: CALL={call_count}, PUT={put_count}')
                avg_acc = sum(s['accuracy'] for s in tier_sigs) / len(tier_sigs)
                out_lines.append(f'    Average accuracy: {avg_acc:.1f}%')
                
                # Top 5
                out_lines.append('')
                out_lines.append('  Top 5 highest-accuracy signals:')
                top5 = sorted(tier_sigs, key=lambda s: -s['accuracy'])[:5]
                for s in top5:
                    out_lines.append(
                        f"    {s['accuracy']:.0f}%  {s['time']}  {s['direction']:<4}  "
                        f"M{s['expiry']}  target=${s['target_dollars']}  (move={s['avg_move']:.0f}pt)"
                    )
            
            out_lines.append('')
            out_lines.append('  ────────────────────────────────────────────────')
            out_lines.append('  MTG1 Strategy:')
            out_lines.append('    Entry 1: bet 1× → if WIN, take profit & stop')
            out_lines.append('    Entry 2: bet 2× → if WIN, recover loss & profit')
            out_lines.append('    Stop:    after Entry 2 loss → max drawdown = 3×')
            out_lines.append('  ────────────────────────────────────────────────')
            out_lines.append(f'  ⚠ REAL accuracy = directional bias from 974 days')
            out_lines.append('')
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(out_lines))
    
    return day_counts


def main():
    print()
    print('=' * 80)
    print('  CANDALXAU Signal Engine v7.0 — HONEST Real-Accuracy Generator')
    print(f'  Timezone: {TZ_NAME}')
    print('  NO INFLATED BONUSES — only real directional bias from 974 days')
    print('=' * 80)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Generate signals
    print(f"\n  [1/4] Generating signals with REAL accuracy (1 per hour)...")
    all_signals = generate_best_signals()
    print(f"  Total unique signals: {len(all_signals)}")
    
    # Tier distributions (REALISTIC thresholds)
    tier_60_count = sum(1 for s in all_signals if s['accuracy'] >= 60)
    tier_55_count = sum(1 for s in all_signals if s['accuracy'] >= 55)
    tier_50_count = sum(1 for s in all_signals if s['accuracy'] >= 50)
    print(f"  Distribution (REAL accuracy):")
    print(f"    ≥60% (Strong bias):  {tier_60_count} signals")
    print(f"    ≥55% (Good bias):    {tier_55_count} signals")
    print(f"    ≥50% (Any edge):     {tier_50_count} signals")
    print(f"  Max achievable accuracy: 71% (Wednesday 22:00 UTC)")
    
    # Generate per-day folder structure
    print(f"\n  [2/4] Generating per-day folders (7 days × 3 tiers)...")
    PER_DAY_DIR = f'{OUTPUT_DIR}/by_day'
    os.makedirs(PER_DAY_DIR, exist_ok=True)
    
    day_counts = generate_per_day_files(all_signals, PER_DAY_DIR)
    
    print(f"  Per-day breakdown:")
    print(f"    {'Day':<12} {'60pct':>6} {'55pct':>6} {'50pct':>6}")
    print(f"    {'-'*12} {'-'*6} {'-'*6} {'-'*6}")
    for day in WEEKDAY_ORDER:
        c = day_counts.get(day, {})
        print(f"    {day:<12} {c.get(60,0):>6} {c.get(55,0):>6} {c.get(50,0):>6}")
    
    total_60 = sum(day_counts[d].get(60, 0) for d in WEEKDAY_ORDER)
    total_55 = sum(day_counts[d].get(55, 0) for d in WEEKDAY_ORDER)
    total_50 = sum(day_counts[d].get(50, 0) for d in WEEKDAY_ORDER)
    print(f"    {'-'*12} {'-'*6} {'-'*6} {'-'*6}")
    print(f"    {'TOTAL':<12} {total_60:>6} {total_55:>6} {total_50:>6}")
    
    # Generate combined tier files
    print(f"\n  [3/4] Generating combined tier files...")
    tier_60 = generate_tier_file(all_signals, 60, 'STRONG BIAS TIER (≥60% real accuracy)',
                                  f'{OUTPUT_DIR}/SIGNALS_XAUUSD_60pct.txt')
    print(f"    ✓ SIGNALS_XAUUSD_60pct.txt — {tier_60} signals")
    
    tier_55 = generate_tier_file(all_signals, 55, 'GOOD BIAS TIER (≥55% real accuracy)',
                                 f'{OUTPUT_DIR}/SIGNALS_XAUUSD_55pct.txt')
    print(f"    ✓ SIGNALS_XAUUSD_55pct.txt — {tier_55} signals")
    
    tier_50 = generate_tier_file(all_signals, 50, 'ANY EDGE TIER (≥50% real accuracy)',
                                  f'{OUTPUT_DIR}/SIGNALS_XAUUSD_50pct.txt')
    print(f"    ✓ SIGNALS_XAUUSD_50pct.txt — {tier_50} signals")
    
    # Generate JSON
    for tier, threshold in [(60, 60), (55, 55), (50, 50)]:
        filtered = [s for s in all_signals if s['accuracy'] >= threshold]
        json_data = {
            'tier': f'≥{threshold}% real directional accuracy',
            'total': len(filtered),
            'generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'engine': 'CANDALXAU Signal Engine v7.0',
            'timezone': TZ_NAME,
            'note': 'ONE best signal per hour — no duplicates. Accuracy is REAL directional bias from 974 days.',
            'max_possible_accuracy': 71,
            'signals': filtered,
        }
        json_path = f'{OUTPUT_DIR}/SIGNALS_XAUUSD_{tier}pct.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"    ✓ SIGNALS_XAUUSD_{tier}pct.json")
    
    # Generate README
    print(f"\n  [4/4] Generating README.md...")
    readme = []
    readme.append(f'# CANDALXAU Signal Engine v7.0 — XAUUSD Real-Accuracy Signals')
    readme.append('')
    readme.append(f'> **XAUUSD (Gold) ONLY** — REAL directional accuracy from 974 days of 5m candles')
    readme.append(f'> All times in **{TZ_NAME}** (already converted from UTC)')
    readme.append(f'> NO INFLATED BONUSES — what you see is the real historical win rate')
    readme.append('')
    readme.append('Generated: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    readme.append('')
    readme.append('## 📊 Signal Counts Per Day')
    readme.append('')
    readme.append('| Day | 60pct | 55pct | 50pct | Notes |')
    readme.append('|-----|-------|-------|-------|-------|')
    for day in WEEKDAY_ORDER:
        c = day_counts.get(day, {})
        note = ''
        if day == 'Saturday':
            note = 'Market closed'
        elif day == 'Sunday':
            note = f'Opens 23:00 {TZ_NAME}'
        elif day in ['Tuesday', 'Thursday']:
            note = 'Best days (peak movement)'
        readme.append(f"| {day} | {c.get(60,0)} | {c.get(55,0)} | {c.get(50,0)} | {note} |")
    readme.append(f"| **TOTAL** | **{total_60}** | **{total_55}** | **{total_50}** | |")
    readme.append('')
    readme.append('## ⚠️ IMPORTANT: Real Accuracy')
    readme.append('')
    readme.append('The displayed accuracy is the **REAL directional bias** from 974 days of historical data:')
    readme.append('')
    readme.append('```')
    readme.append('accuracy = max(up_pct, down_pct)')
    readme.append('```')
    readme.append('')
    readme.append('| Tier | Threshold | Description |')
    readme.append('|------|-----------|-------------|')
    readme.append('| Strong Bias | ≥60% | High directional edge |')
    readme.append('| Good Bias | ≥55% | Moderate directional edge |')
    readme.append('| Any Edge | ≥50% | Slight directional edge |')
    readme.append('')
    readme.append('**Max possible accuracy: 71%** (Wednesday 22:00 UTC = 23:00 Algeria)')
    readme.append('')
    readme.append('⚠️ **90%+ accuracy is statistically impossible** with this data.')
    readme.append('Previous versions showed inflated numbers (90%+) which were artificially')
    readme.append('boosted by bonuses. v7.0 shows the REAL historical win rate only.')
    readme.append('')
    readme.append('## 🎯 Asset')
    readme.append('- **XAUUSD (Gold)** — Real spot gold')
    readme.append('- Source data: 974 days of 5-minute candles (2021-2026)')
    readme.append(f'- All times in **{TZ_NAME}** (converted from UTC)')
    readme.append('- ONE best signal per hour — no duplicates')
    readme.append('')
    readme.append('## 📐 Signal Format')
    readme.append('```')
    readme.append(f'⭐⭐ M3  XAUUSD  23:00 CALL  acc=58% target=$1  | move=10pt up:58% down:42% bias:UP')
    readme.append('```')
    readme.append('- **acc=58%** = REAL directional accuracy from 974 days (58% of days went UP)')
    readme.append('- **move=10pt** = average price movement during this hour')
    readme.append('- **bias:UP** = direction is up (because up_pct ≥ down_pct)')
    readme.append('')
    readme.append('## 🏆 Tier Badges (REAL accuracy)')
    readme.append('- ⭐⭐⭐ **Ultra-Elite**: ≥70% (very rare, only 1 hour exists)')
    readme.append('- ⭐⭐ **Elite**: 60-70% (strong bias)')
    readme.append('- ⭐ **High-Elite**: 55-60% (good bias)')
    readme.append('- 🔥 **High**: 53-55% (slight edge)')
    readme.append('- ⚡ **Standard**: 51-53% (marginal edge)')
    readme.append('- ✓ **Basic**: 50-51% (coin flip + tiny edge)')
    readme.append('')
    readme.append('## 🎲 MTG1 Strategy')
    readme.append('1. Entry 1: bet 1× → if WIN, take profit & stop')
    readme.append('2. Entry 2: bet 2× → if WIN, recover loss & profit')
    readme.append('3. Stop: after Entry 2 loss → max drawdown = 3×')
    readme.append('')
    readme.append(f'## 🌍 Timezone')
    readme.append(f'- All times in **{TZ_NAME}** (already converted from UTC)')
    readme.append('- UTC+1 = Algeria, France, Tunisia')
    readme.append('')
    readme.append('## 🕐 Market Hours (XAUUSD)')
    readme.append('- **Saturday**: Market CLOSED')
    readme.append(f'- **Sunday**: Opens at 23:00 {TZ_NAME}')
    readme.append('- **Monday-Friday**: 24h trading')
    readme.append(f'- **Peak hours**: 13:00-17:00 {TZ_NAME} (London/NY overlap)')
    readme.append('')
    readme.append('---')
    readme.append(f'Generated by **CANDALXAU Signal Engine v7.0** (honest accuracy, {TZ_NAME})')
    
    with open(f'{OUTPUT_DIR}/README.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(readme))
    
    print()
    print('  ' + '=' * 76)
    print(f'  CANDALXAU Signal Engine v7.0 — HONEST Signals Generated ({TZ_NAME})')
    print('  ' + '=' * 76)
    print(f'  Output directory: {OUTPUT_DIR}')
    print(f'  NO DUPLICATES — ONE signal per hour')
    print(f'  REAL accuracy (no inflated bonuses):')
    print(f'    Strong bias (≥60%):  {total_60} signals')
    print(f'    Good bias (≥55%):    {total_55} signals')
    print(f'    Any edge (≥50%):     {total_50} signals')
    print(f'  Max achievable accuracy: 71% (Wed 23:00 Algeria)')
    print('  ' + '=' * 76)
    print()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FutureQuantVexa v4.0 — Movement Prediction Engine (XAUUSD 5m)
=============================================================

Instead of predicting candle direction (CALL/PUT), this version predicts
MOVEMENT SIZE (in points/pips) during specific time windows.

Strategy:
  - Analyze 521,037 XAUUSD 5m candles (1809 days, 2021-2026)
  - For each weekday × hour, calculate the average price movement
  - Movement = max(high) - min(low) during that hour
  - Identify "high-movement windows" where price moves ≥40-100 points
  - Output: "Friday 14:00-15:00 → avg 85 points movement → Target: 50 points"

Usage:
  python fqv4.py /path/to/XAUUSD_5m.json --tz=1
  python fqv4.py /path/to/XAUUSD_5m.json --tz=1 --day=Friday --min-move=50
  python fqv4.py /path/to/XAUUSD_5m.json --tz=1 --day=all --min-move=40
"""

import os, sys, json, argparse, csv
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import statistics

WEEKDAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
WEEKDAY_FULL = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']


def load_candles(filepath):
    """Load candles from JSON file."""
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
            'datetime': c.get('datetime', ''),
            'open': float(c['open']),
            'high': float(c['high']),
            'low': float(c['low']),
            'close': float(c['close']),
        })
    normalized.sort(key=lambda c: c['time'])
    return normalized


def calculate_hourly_movements(candles, tz_offset=0):
    """For each candle, calculate the price movement during the NEXT hour.
    
    Since candles are 5m, we look at the next 12 candles (60 min / 5 min = 12).
    Movement = max(high[1..12]) - min(low[1..12])
    
    Returns list of movement records with weekday, hour, movement, etc.
    """
    movements = []
    
    for i in range(len(candles) - 12):
        candle = candles[i]
        dt = datetime.fromtimestamp(candle['time'], tz=timezone.utc) + timedelta(hours=tz_offset)
        
        # Python weekday: Mon=0, Sun=6 → our: Sun=0, Sat=6
        weekday = dt.weekday()
        our_weekday = (weekday + 1) % 7
        hour = dt.hour
        
        # Get next 12 candles (1 hour of 5m candles)
        next_candles = candles[i+1:i+13]
        if len(next_candles) < 12:
            continue
        
        # Calculate movement: highest high - lowest low
        max_high = max(c['high'] for c in next_candles)
        min_low = min(c['low'] for c in next_candles)
        movement = max_high - min_low
        
        # Also calculate directional movement
        entry_price = candle['close']
        max_up = max_high - entry_price    # how much it went up
        max_down = entry_price - min_low   # how much it went down
        
        movements.append({
            'timestamp': candle['time'],
            'datetime': candle.get('datetime', dt.strftime('%Y-%m-%d %H:%M:%S')),
            'weekday': our_weekday,
            'weekday_name': WEEKDAY_NAMES[our_weekday],
            'weekday_full': WEEKDAY_FULL[our_weekday],
            'hour': hour,
            'entry_price': entry_price,
            'max_high': max_high,
            'min_low': min_low,
            'movement': movement,
            'max_up': max_up,
            'max_down': max_down,
            'dominant_dir': 'UP' if max_up >= max_down else 'DOWN',
        })
    
    return movements


def analyze_movements(movements, min_move=40, tz_offset=1):
    """Analyze movements by weekday × hour.
    
    Returns list of analysis records sorted by average movement (descending).
    """
    # Group by weekday × hour
    groups = defaultdict(list)
    for m in movements:
        key = (m['weekday'], m['hour'])
        groups[key].append(m)
    
    results = []
    for (weekday, hour), group in groups.items():
        if len(group) < 10:
            continue  # need at least 10 samples for statistical significance
        
        move_values = [g['movement'] for g in group]
        up_values = [g['max_up'] for g in group]
        down_values = [g['max_down'] for g in group]
        
        avg_move = statistics.mean(move_values)
        median_move = statistics.median(move_values)
        max_move = max(move_values)
        min_move_val = min(move_values)
        stdev_move = statistics.stdev(move_values) if len(move_values) > 1 else 0
        
        # Calculate how often movement exceeds threshold
        above_40 = sum(1 for v in move_values if v >= 40) / len(move_values) * 100
        above_50 = sum(1 for v in move_values if v >= 50) / len(move_values) * 100
        above_75 = sum(1 for v in move_values if v >= 75) / len(move_values) * 100
        above_100 = sum(1 for v in move_values if v >= 100) / len(move_values) * 100
        
        # Direction bias
        up_count = sum(1 for g in group if g['dominant_dir'] == 'UP')
        down_count = len(group) - up_count
        up_pct = up_count / len(group) * 100
        
        results.append({
            'weekday': weekday,
            'weekday_name': WEEKDAY_NAMES[weekday],
            'weekday_full': WEEKDAY_FULL[weekday],
            'hour': hour,
            'samples': len(group),
            'avg_move': avg_move,
            'median_move': median_move,
            'max_move': max_move,
            'min_move': min_move_val,
            'stdev': stdev_move,
            'above_40_pct': above_40,
            'above_50_pct': above_50,
            'above_75_pct': above_75,
            'above_100_pct': above_100,
            'up_pct': up_pct,
            'down_pct': 100 - up_pct,
            'dominant_dir': 'UP' if up_pct >= 50 else 'DOWN',
        })
    
    # Sort by average movement descending
    results.sort(key=lambda r: r['avg_move'], reverse=True)
    return results


def print_results(results, min_move, day_filter, tz_offset, detailed=False):
    """Print movement analysis results."""
    tz_label = f"UTC+{tz_offset}" if tz_offset >= 0 else f"UTC{tz_offset}"
    
    # Filter by day if specified
    if day_filter and day_filter.lower() != 'all':
        day_map = {WEEKDAY_NAMES[i].lower(): i for i in range(7)}
        day_map.update({WEEKDAY_FULL[i].lower(): i for i in range(7)})
        if day_filter.lower() in day_map:
            target_day = day_map[day_filter.lower()]
            results = [r for r in results if r['weekday'] == target_day]
    
    # Filter by minimum movement
    filtered = [r for r in results if r['avg_move'] >= min_move]
    
    if not filtered:
        print(f"\n  ⚠ No time windows found with avg movement ≥ {min_move} points.")
        print(f"  Try a lower threshold (e.g. --min-move=20)")
        return
    
    print()
    print("━" * 7 + " • " + "━" * 7)
    print(f"  XAUUSD 5m — Movement Prediction ({tz_label})")
    print(f"  Min movement: {min_move} points | Target: close on reaching movement")
    print("━" * 7 + " • " + "━" * 7)
    print()
    
    # Group by weekday for display
    by_day = defaultdict(list)
    for r in filtered:
        by_day[r['weekday']].append(r)
    
    for day_idx in range(7):
        day_results = by_day.get(day_idx, [])
        if not day_results:
            continue
        
        day_results.sort(key=lambda r: r['hour'])
        
        print(f"\n  📅 {WEEKDAY_FULL[day_idx]}")
        print(f"  {'Hour':<8} {'Samples':<10} {'Avg Move':<12} {'Median':<10} {'≥40pt':<8} {'≥50pt':<8} {'≥75pt':<8} {'≥100pt':<8} {'Dir':<6}")
        print(f"  {'-'*90}")
        
        for r in day_results:
            dir_emoji = "🟢 UP" if r['dominant_dir'] == 'UP' else "🔴 DOWN"
            print(f"  {r['hour']:02d}:00   {r['samples']:<10} {r['avg_move']:<12.1f} {r['median_move']:<10.1f} "
                  f"{r['above_40_pct']:<7.0f}% {r['above_50_pct']:<7.0f}% {r['above_75_pct']:<7.0f}% {r['above_100_pct']:<7.0f}% {dir_emoji}")
    
    # Top 20 highest-movement windows
    print(f"\n{'='*100}")
    print(f"  TOP 20 HIGHEST-MOVEMENT TIME WINDOWS (≥{min_move} avg points)")
    print(f"{'='*100}")
    print(f"\n  {'#':<4} {'Day':<10} {'Hour':<8} {'Samples':<10} {'Avg Move':<12} {'Max Move':<12} {'≥50pt%':<8} {'≥75pt%':<8} {'≥100pt%':<9} {'Direction':<10}")
    print(f"  {'-'*100}")
    
    for i, r in enumerate(filtered[:20], 1):
        dir_emoji = "🟢 UP" if r['dominant_dir'] == 'UP' else "🔴 DOWN"
        print(f"  {i:<4} {r['weekday_full']:<10} {r['hour']:02d}:00   {r['samples']:<10} "
              f"{r['avg_move']:<12.1f} {r['max_move']:<12.1f} "
              f"{r['above_50_pct']:<7.0f}% {r['above_75_pct']:<7.0f}% {r['above_100_pct']:<8.0f}% {dir_emoji}")
    
    # Trading recommendations
    print(f"\n{'='*100}")
    print(f"  TRADING RECOMMENDATIONS")
    print(f"{'='*100}")
    
    # Best windows: high avg move + high probability of reaching target
    best = [r for r in filtered if r['above_50_pct'] >= 60]
    best.sort(key=lambda r: r['above_50_pct'], reverse=True)
    
    if best:
        print(f"\n  Best windows (≥60% chance of 50+ point move):")
        for r in best[:10]:
            dir_emoji = "🟢 UP" if r['dominant_dir'] == 'UP' else "🔴 DOWN"
            # Recommend target = 60% of average movement (conservative)
            target = r['avg_move'] * 0.6
            print(f"    {r['weekday_full']:<10} {r['hour']:02d}:00-{(r['hour']+1)%24:02d}:00 ({tz_label}) | "
                  f"Avg: {r['avg_move']:.0f}pt | Target: {target:.0f}pt | "
                  f"Hit rate: {r['above_50_pct']:.0f}% | Direction: {dir_emoji}")
    else:
        print(f"\n  No windows with ≥60% chance of 50pt move. Try lower --min-move.")
    
    # Summary
    print(f"\n  {'='*60}")
    print(f"  SUMMARY")
    print(f"  {'='*60}")
    print(f"  Total time windows analyzed: {len(results)}")
    print(f"  Windows with ≥{min_move}pt avg movement: {len(filtered)}")
    
    if filtered:
        all_moves = [r['avg_move'] for r in filtered]
        print(f"  Average movement across all windows: {statistics.mean(all_moves):.1f} points")
        print(f"  Highest avg movement: {max(all_moves):.1f} points ({filtered[0]['weekday_full']} {filtered[0]['hour']:02d}:00)")
        print(f"  Lowest avg movement: {min(all_moves):.1f} points")
    
    print(f"  Timezone: {tz_label}")
    print(f"  Strategy: Enter at hour start → Set TP target → Close on hit")
    print(f"  {'='*60}")


def save_csv(results, filepath='xauusd_movements.csv'):
    """Save movement analysis to CSV."""
    with open(filepath, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['weekday', 'hour', 'samples', 'avg_move', 'median_move', 'max_move',
                     'min_move', 'stdev', 'above_40_pct', 'above_50_pct', 'above_75_pct',
                     'above_100_pct', 'up_pct', 'down_pct', 'dominant_dir'])
        for r in sorted(results, key=lambda x: -x['avg_move']):
            w.writerow([r['weekday_full'], f"{r['hour']:02d}:00", r['samples'],
                        f"{r['avg_move']:.1f}", f"{r['median_move']:.1f}", f"{r['max_move']:.1f}",
                        f"{r['min_move']:.1f}", f"{r['stdev']:.1f}",
                        f"{r['above_40_pct']:.0f}%", f"{r['above_50_pct']:.0f}%",
                        f"{r['above_75_pct']:.0f}%", f"{r['above_100_pct']:.0f}%",
                        f"{r['up_pct']:.0f}%", f"{r['down_pct']:.0f}%", r['dominant_dir']])
    print(f"\n  ✓ Saved to: {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description='FutureQuantVexa v4.0 — XAUUSD Movement Prediction',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fqv4.py XAUUSD_5m.json --tz=1
  python fqv4.py XAUUSD_5m.json --tz=1 --day=Friday --min-move=50
  python fqv4.py XAUUSD_5m.json --tz=1 --day=all --min-move=40 --detailed
""")
    
    parser.add_argument('file', help='XAUUSD 5m JSON candle file')
    parser.add_argument('--tz', type=int, default=1, help='Timezone offset (default: 1 = UTC+1)')
    parser.add_argument('--day', default='all', help='Day filter: Sun-Sat or all (default: all)')
    parser.add_argument('--min-move', type=float, default=40, help='Min avg movement in points (default: 40)')
    parser.add_argument('--detailed', action='store_true', help='Show all hours (not just filtered)')
    
    args = parser.parse_args()
    
    print()
    print('=' * 70)
    print('  FutureQuantVexa v4.0 — XAUUSD Movement Prediction Engine')
    print('  Predicts PRICE MOVEMENT (not direction) per weekday × hour')
    print('  Data: 521,037 candles × 5m × 1809 days (2021-2026)')
    print('=' * 70)
    
    tz_label = f"UTC+{args.tz}" if args.tz >= 0 else f"UTC{args.tz}"
    print(f"\n  Loading: {args.file}")
    print(f"  Timezone: {tz_label}")
    print(f"  Min movement: {args.min_move} points")
    print(f"  Day filter: {args.day}")
    
    # Load candles
    candles = load_candles(args.file)
    print(f"  Candles loaded: {len(candles):,}")
    
    first_dt = datetime.fromtimestamp(candles[0]['time'], tz=timezone.utc)
    last_dt = datetime.fromtimestamp(candles[-1]['time'], tz=timezone.utc)
    print(f"  Date range: {first_dt.strftime('%Y-%m-%d')} → {last_dt.strftime('%Y-%m-%d')}")
    print(f"  Price range: {min(c['low'] for c in candles):.2f} - {max(c['high'] for c in candles):.2f}")
    
    # Calculate movements
    print(f"\n  Analyzing hourly movements (next 12 candles = 1 hour)...")
    movements = calculate_hourly_movements(candles, args.tz)
    print(f"  Movement records: {len(movements):,}")
    
    # Analyze by weekday × hour
    print(f"\n  Grouping by weekday × hour...")
    results = analyze_movements(movements, args.min_move, args.tz)
    print(f"  Time windows analyzed: {len(results)}")
    
    # Print results
    print_results(results, args.min_move, args.day, args.tz, args.detailed)
    
    # Save CSV
    save_csv(results)
    
    print()
    print(f"  {'='*60}")
    print(f"  FutureQuantVexa v4.0 — Complete")
    print(f"  {'='*60}")
    print()


if __name__ == '__main__':
    main()

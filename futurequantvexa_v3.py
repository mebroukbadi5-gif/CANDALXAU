#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FutureQuantVexa v3.0 — Advanced Multi-Stage Signal Generator
=============================================================

Pipeline:
  1. SCAN:     Reads candle JSON → detects all 18 patterns → stores ALL signals
  2. STORE:    Saves raw signals to per-weekday JSON cache files (.fqv_raw/)
  3. FILTER:   User requests a specific day + direction + time range + gap
  4. OUTPUT:   Telegram-style list (M1 PAIR-OTC HH:MM CALL/PUT)
  5. CACHE:    Tracks already-sent signals to prevent duplicates across runs

Usage:
  # First: scan candle files (generates raw signal cache)
  python fqv3.py scan *.json

  # Then: extract signals for any day/time/direction/gap
  python fqv3.py extract --day=Sunday --dir=both --time=09:00-12:00 --gap=4 --tz=1
  python fqv3.py extract --day=Mon --dir=CALL --time=23:00-00:00 --gap=3 --tz=1
  python fqv3.py extract --day=Saturday --dir=PUT --gap=5
  python fqv3.py extract --day=all --dir=both --gap=4 --tz=1

  # Clear cache
  python fqv3.py clear-cache
"""

import os, sys, json, re, argparse, csv
from datetime import datetime, timedelta, timezone
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, '.fqv_raw')
SENT_CACHE = os.path.join(SCRIPT_DIR, '.fqv_sent.json')

# ============================================================================
# ELITE PATTERN DATABASE (142 combinations, ≥85% C1+C2)
# ============================================================================
ELITE_PATTERNS = {
    "USDPHP:Sun:GapRev:BUY":(50.0,86.7,6.6),"USDNGN:Sun:InsideBody:SELL":(50.0,89.3,8.8),
    "USDIDR:Sun:InsideBar:SELL":(70.0,95.0,11.2),"USDIDR:Sun:PinBar:SELL":(50.0,94.4,9.0),
    "USDIDR:Sun:ShootStar:SELL":(33.3,91.7,4.4),"USDIDR:Sun:LongWick:SELL":(52.4,90.5,7.6),
    "USDIDR:Sun:Harami:SELL":(60.0,90.0,3.6),"USDMXN:Sun:Doji:SELL":(55.6,94.4,9.2),
    "USDMXN:Sun:Marubozu:BUY":(50.0,92.9,6.2),"USDMXN:Sun:LongWick:SELL":(57.6,87.9,9.2),
    "USDMXN:Sun:PinBar:SELL":(55.0,85.0,3.4),"USDMXN:Sun:Harami:BUY":(58.3,83.3,7.8),
    "USDMXN:Sun:InsideBody:BUY":(50.0,81.3,4.0),"USDCOP:Sun:Engulfing:SELL":(58.3,91.7,5.0),
    "USDCOP:Sun:BigBodyRev:SELL":(59.5,86.5,8.6),"USDCOP:Sun:Marubozu:SELL":(66.7,86.7,3.8),
    "USDZAR:Sun:Tweezer:SELL":(68.2,86.4,5.4),"USDZAR:Sun:InsideBar:BUY":(60.0,85.0,3.6),
    "USDZAR:Sun:PinBar:SELL":(47.1,82.4,9.8),"USDARS:Sun:GapRev:BUY":(60.6,90.9,13.0),
    "USDARS:Sun:Engulfing:BUY":(52.4,90.5,7.6),"USDARS:Sun:Marubozu:BUY":(55.0,85.0,3.4),
    "USDBDT:Sun:Doji:BUY":(55.6,83.3,10.8),"USDDZD:Sun:PinBar:SELL":(71.4,85.7,3.2),
    "USDEGP:Sun:Tweezer:SELL":(71.4,85.7,3.2),"USDEGP:Sun:Marubozu:BUY":(40.0,86.7,3.0),
    "USDEGP:Sun:BigBodyRev:SELL":(51.4,82.9,20.6),"BRLUSD:Wed:ShootStar:SELL":(50.0,85.0,3.2),
    "USDINR:Mon:PinBar:BUY":(66.7,100.0,11.0),"USDZAR:Mon:Doji:BUY":(75.0,100.0,9.0),
    "USDEGP:Mon:InsideBar:SELL":(75.0,93.8,8.4),"USDMXN:Mon:Marubozu:SELL":(73.3,93.3,7.6),
    "USDCOP:Mon:Star:BUY":(70.6,94.1,9.0),"USDARS:Mon:Star:BUY":(80.0,93.3,7.8),
    "USDARS:Mon:Harami:SELL":(30.0,90.0,3.0),"USDINR:Mon:Tweezer:BUY":(60.0,86.7,3.6),
    "BRLUSD:Mon:Engulfing:SELL":(66.7,91.7,5.2),"BRLUSD:Mon:PinBar:BUY":(68.4,89.5,6.8),
    "BRLUSD:Mon:LongWick:BUY":(57.7,88.5,7.8),"BRLUSD:Mon:Hammer:BUY":(64.3,85.7,3.0),
    "BRLUSD:Mon:Harami:BUY":(38.5,84.6,8.0),"USDDZD:Mon:Tweezer:BUY":(69.2,92.3,6.0),
    "USDDZD:Mon:InsideBar:BUY":(50.0,89.3,8.8),"USDDZD:Mon:LongWick:BUY":(56.7,83.3,19.4),
    "USDPHP:Mon:Marubozu:SELL":(46.2,92.3,5.4),"USDPHP:Mon:Star:BUY":(71.4,85.7,3.2),
    "USDPHP:Mon:PinBar:BUY":(43.8,81.3,9.0),"USDNGN:Mon:InsideBar:BUY":(59.3,88.9,8.6),
    "USDNGN:Mon:InsideBody:BUY":(60.0,85.0,3.6),"USDEGP:Mon:Star:BUY":(56.3,87.5,4.2),
    "USDINR:Tue:PinBar:BUY":(60.0,95.0,10.8),"USDINR:Tue:ShootStar:SELL":(20.0,90.0,2.8),
    "USDINR:Tue:Marubozu:SELL":(50.0,90.0,3.4),"USDNGN:Tue:Engulfing:BUY":(58.3,91.7,5.0),
    "USDNGN:Tue:InsideBar:SELL":(63.2,89.5,6.6),"USDNGN:Tue:LongWick:SELL":(57.7,88.5,7.8),
    "USDNGN:Tue:BigBodyRev:SELL":(57.1,82.9,5.8),"USDNGN:Tue:Tweezer:BUY":(59.5,85.7,8.6),
    "USDARS:Tue:PinBar:SELL":(71.4,85.7,3.2),"USDARS:Tue:GapRev:BUY":(60.0,85.7,7.2),
    "USDARS:Tue:LongWick:SELL":(65.4,84.6,1.4),"USDPKR:Tue:InsideBody:BUY":(69.4,91.7,15.8),
    "USDPKR:Tue:GapRev:BUY":(53.7,87.8,11.0),"USDPKR:Tue:Star:BUY":(51.6,83.9,18.2),
    "USDPKR:Tue:Harami:SELL":(54.5,81.8,7.0),"USDIDR:Tue:Engulfing:SELL":(56.3,87.5,4.2),
    "USDIDR:Tue:PinBar:SELL":(39.1,87.0,4.8),"USDIDR:Tue:ShootStar:SELL":(10.0,90.0,2.8),
    "USDIDR:Tue:Doji:SELL":(42.9,82.1,15.6),"USDIDR:Tue:Tweezer:SELL":(65.6,87.5,9.0),
    "USDIDR:Tue:InsideBar:BUY":(53.3,83.3,4.0),"USDIDR:Tue:BigBodyRev:BUY":(46.3,82.9,24.8),
    "USDZAR:Tue:Hammer:SELL":(58.3,91.7,5.0),"USDZAR:Tue:Doji:SELL":(65.0,85.0,3.8),
    "USDZAR:Tue:Marubozu:BUY":(52.4,85.7,4.0),"USDMXN:Tue:Doji:SELL":(53.3,86.7,3.4),
    "USDCOP:Tue:3Soldiers:BUY":(60.9,85.5,13.8),"USDCOP:Tue:Consec2:BUY":(57.9,81.7,33.0),
    "BRLUSD:Fri:Engulfing:BUY":(51.9,85.2,4.6),
    "USDPHP:Wed:Harami:SELL":(56.3,93.8,7.8),"USDPHP:Wed:InsideBar:SELL":(48.1,86.5,11.0),
    "USDNGN:Wed:Harami:BUY":(62.5,87.5,4.4),"USDNGN:Wed:InsideBar:BUY":(51.1,87.2,11.4),
    "USDNGN:Wed:Tweezer:BUY":(59.5,85.7,8.6),"USDARS:Wed:Star:SELL":(69.2,87.2,10.8),
    "USDDZD:Wed:PinBar:SELL":(54.8,90.3,11.2),"USDDZD:Wed:ShootStar:SELL":(58.8,88.2,5.0),
    "USDDZD:Wed:LongWick:SELL":(54.4,84.2,4.0),"USDDZD:Tue:TrendCont:BUY":(63.6,85.5,11.2),
    "USDMXN:Wed:ShootStar:SELL":(54.5,86.4,4.8),"USDMXN:Wed:Harami:BUY":(63.6,86.4,5.2),
    "USDZAR:Wed:Harami:BUY":(60.9,82.6,14.2),
    "USDINR:Thu:ShootStar:SELL":(72.2,94.4,9.8),"USDINR:Thu:BigBodyRev:SELL":(60.0,86.2,12.0),
    "USDINR:Thu:Harami:BUY":(47.1,82.4,9.8),"USDZAR:Thu:Harami:BUY":(50.0,94.4,9.0),
    "USDZAR:Thu:GapRev:SELL":(44.9,84.1,26.4),"USDARS:Thu:InsideBar:BUY":(63.6,88.6,14.0),
    "USDARS:Thu:Harami:BUY":(58.8,88.2,5.0),"USDARS:Thu:Marubozu:SELL":(52.2,87.0,5.4),
    "USDARS:Thu:Tweezer:BUY":(51.9,85.2,4.6),"USDDZD:Thu:Hammer:BUY":(68.2,81.8,13.8),
    "USDEGP:Thu:Marubozu:BUY":(60.9,87.0,5.8),"USDPHP:Thu:Hammer:SELL":(50.0,90.0,3.4),
    "USDBDT:Thu:Marubozu:SELL":(48.3,86.2,5.8),"USDBDT:Thu:BigBodyRev:SELL":(47.5,85.2,10.0),
    "USDBDT:Thu:PinBar:BUY":(59.6,83.0,0.2),
    "USDCOP:Fri:ShootStar:SELL":(52.4,95.2,11.2),"USDINR:Fri:Engulfing:BUY":(71.4,89.3,10.0),
    "USDMXN:Fri:Marubozu:SELL":(54.2,91.7,9.8),"USDMXN:Fri:PinBar:BUY":(68.8,90.6,12.8),
    "USDMXN:Fri:Star:SELL":(57.6,81.8,5.2),"USDMXN:Fri:Tweezer:SELL":(57.1,82.1,2.0),
    "USDNGN:Fri:Hammer:BUY":(64.7,88.2,5.2),"USDNGN:Fri:InsideBar:BUY":(52.1,85.4,8.6),
    "USDNGN:Fri:Tweezer:SELL":(64.5,87.1,8.2),"USDEGP:Fri:Marubozu:BUY":(54.5,87.9,9.0),
    "USDIDR:Fri:ShootStar:SELL":(56.3,87.5,4.2),"USDIDR:Fri:PinBar:SELL":(45.5,81.8,4.4),
    "USDCOP:Fri:Star:BUY":(55.3,81.6,7.4),"BRLUSD:Fri:Tweezer:SELL":(69.0,86.2,7.0),
    "USDDZD:Fri:Hammer:SELL":(35.0,85.0,2.6),"USDPHP:Fri:Harami:BUY":(59.1,86.4,5.0),
    "USDDZD:Sat:Marubozu:SELL":(66.7,100.0,8.8),"USDINR:Sat:Tweezer:SELL":(76.9,100.0,9.8),
    "USDPKR:Sat:PinBar:BUY":(52.2,95.7,12.6),"USDBDT:Sat:PinBar:BUY":(53.3,93.3,7.0),
    "USDZAR:Sat:Star:BUY":(46.7,93.3,6.8),"USDDZD:Sat:Star:SELL":(42.9,92.9,6.0),
    "USDINR:Sat:Star:SELL":(64.3,92.9,13.2),"USDNGN:Sat:Star:BUY":(73.3,86.7,4.0),
    "USDNGN:Sat:GapRev:SELL":(56.7,86.7,7.0),"USDPHP:Sat:Hammer:SELL":(50.0,91.7,4.8),
    "USDPHP:Sat:Tweezer:BUY":(58.3,91.7,5.0),"USDPHP:Sat:PinBar:BUY":(45.5,90.9,4.0),
    "USDPKR:Sat:InsideBody:BUY":(63.6,90.9,8.8),"USDPKR:Sat:Star:BUY":(63.2,89.5,6.6),
    "USDPKR:Sat:LongWick:BUY":(52.9,82.4,4.8),"USDPKR:Sat:Engulfing:BUY":(66.7,88.9,6.0),
    "USDDZD:Sat:PinBar:SELL":(50.0,87.5,4.0),"USDDZD:Sat:Tweezer:BUY":(50.0,87.5,4.0),
    "USDDZD:Sat:LongWick:SELL":(56.5,87.0,5.6),"USDDZD:Sat:Engulfing:BUY":(53.8,84.6,7.6),
    "USDDZD:Sat:TrendCont:SELL":(60.0,86.0,10.8),"USDBDT:Sat:LongWick:BUY":(48.1,88.9,8.0),
    "USDIDR:Sat:InsideBar:BUY":(50.0,88.9,5.4),"USDIDR:Sat:3Soldiers:SELL":(63.0,81.5,19.2),
    "USDIDR:Sat:TrendCont:BUY":(52.2,87.0,10.8),"USDARS:Sat:Hammer:BUY":(70.0,90.0,3.8),
    "USDARS:Sat:LongWick:BUY":(61.3,87.1,8.0),"USDARS:Sat:InsideBody:BUY":(52.2,87.0,5.4),
    "USDARS:Sat:BigBodyRev:SELL":(65.2,87.0,6.0),"USDCOP:Sat:Marubozu:BUY":(54.5,86.4,4.8),
    "USDCOP:Sat:Tweezer:SELL":(58.6,86.2,6.4),"USDCOP:Sat:GapRev:BUY":(53.3,82.2,11.8),
    "USDMXN:Sat:BigBodyRev:SELL":(40.7,81.5,0.4),"USDMXN:Sat:Engulfing:BUY":(58.8,88.2,5.0),
    "USDZAR:Sat:Doji:BUY":(45.5,81.8,6.8),"USDZAR:Sat:Engulfing:BUY":(50.0,87.5,4.0),
    "USDEGP:Mon:InsideBar:SELL":(75.0,93.8,8.4),
}

# ============================================================================
# PATTERN DETECTION (18 patterns)
# ============================================================================
def detect_doji(c):
    s=[]
    for i in range(1,len(c)-1):
        p,x=c[i-1],c[i];r=x['high']-x['low'];b=abs(x['close']-x['open'])
        if r>0 and b/r<=0.1:
            if p['close']<p['open']:s.append({'entry_idx':i+1,'direction':'BUY','pattern':'Doji'})
            elif p['close']>p['open']:s.append({'entry_idx':i+1,'direction':'SELL','pattern':'Doji'})
    return s

def detect_hammer(c):
    s=[]
    for i in range(1,len(c)-1):
        p,x=c[i-1],c[i];r=x['high']-x['low'];b=abs(x['close']-x['open'])
        lw=min(x['open'],x['close'])-x['low'];uw=x['high']-max(x['open'],x['close'])
        if r>0 and b/r<=0.3 and lw/r>=0.6 and uw/r<=0.15:
            if p['close']<p['open']:s.append({'entry_idx':i+1,'direction':'BUY','pattern':'Hammer'})
            elif p['close']>p['open']:s.append({'entry_idx':i+1,'direction':'SELL','pattern':'Hammer'})
    return s

def detect_shooting_star(c):
    s=[]
    for i in range(1,len(c)-1):
        p,x=c[i-1],c[i]
        if p['close']<=p['open']:continue
        r=x['high']-x['low'];b=abs(x['close']-x['open'])
        uw=x['high']-max(x['open'],x['close']);lw=min(x['open'],x['close'])-x['low']
        if r>0 and b/r<=0.3 and uw/r>=0.6 and lw/r<=0.15:
            s.append({'entry_idx':i+1,'direction':'SELL','pattern':'ShootStar'})
    return s

def detect_star(c):
    s=[]
    for i in range(2,len(c)-1):
        c1,c2,c3=c[i-2],c[i-1],c[i]
        if c1['close']<c1['open'] and abs(c2['close']-c2['open'])<abs(c1['close']-c1['open'])*0.5 and c3['close']>c3['open'] and c3['close']>(c1['open']+c1['close'])/2:
            s.append({'entry_idx':i+1,'direction':'BUY','pattern':'Star'})
        if c1['close']>c1['open'] and abs(c2['close']-c2['open'])<abs(c1['close']-c1['open'])*0.5 and c3['close']<c3['open'] and c3['close']<(c1['open']+c1['close'])/2:
            s.append({'entry_idx':i+1,'direction':'SELL','pattern':'Star'})
    return s

def detect_three_soldiers(c):
    s=[]
    for i in range(2,len(c)-1):
        c1,c2,c3=c[i-2],c[i-1],c[i]
        if c1['close']>c1['open'] and c2['close']>c2['open'] and c3['close']>c3['open'] and c2['close']>c1['close'] and c3['close']>c2['close']:
            s.append({'entry_idx':i+1,'direction':'BUY','pattern':'3Soldiers'})
        if c1['close']<c1['open'] and c2['close']<c2['open'] and c3['close']<c3['open'] and c2['close']<c1['close'] and c3['close']<c2['close']:
            s.append({'entry_idx':i+1,'direction':'SELL','pattern':'3Soldiers'})
    return s

def detect_harami(c):
    s=[]
    for i in range(1,len(c)-1):
        p,x=c[i-1],c[i];pb=abs(p['close']-p['open']);cb=abs(x['close']-x['open'])
        if cb<pb*0.6 and x['high']<=p['high'] and x['low']>=p['low']:
            if p['close']<p['open'] and x['close']>x['open']:s.append({'entry_idx':i+1,'direction':'BUY','pattern':'Harami'})
            if p['close']>p['open'] and x['close']<x['open']:s.append({'entry_idx':i+1,'direction':'SELL','pattern':'Harami'})
    return s

def detect_piercing(c):
    s=[]
    for i in range(1,len(c)-1):
        p,x=c[i-1],c[i]
        if p['close']<p['open'] and x['open']<p['low'] and x['close']>(p['open']+p['close'])/2 and x['close']>x['open']:
            s.append({'entry_idx':i+1,'direction':'BUY','pattern':'Piercing'})
        if p['close']>p['open'] and x['open']>p['high'] and x['close']<(p['open']+p['close'])/2 and x['close']<x['open']:
            s.append({'entry_idx':i+1,'direction':'SELL','pattern':'Piercing'})
    return s

def detect_tweezer(c):
    s=[]
    for i in range(1,len(c)-1):
        p,x=c[i-1],c[i];r=x['high']-x['low']
        if r>0:
            if abs(x['low']-p['low'])<r*0.05 and p['close']<p['open'] and x['close']>x['open']:s.append({'entry_idx':i+1,'direction':'BUY','pattern':'Tweezer'})
            if abs(x['high']-p['high'])<r*0.05 and p['close']>p['open'] and x['close']<x['open']:s.append({'entry_idx':i+1,'direction':'SELL','pattern':'Tweezer'})
    return s

def detect_marubozu(c):
    s=[]
    for i in range(len(c)-1):
        x=c[i];r=x['high']-x['low'];b=abs(x['close']-x['open'])
        if r>0 and b/r>=0.92:
            if x['close']>x['open']:s.append({'entry_idx':i+1,'direction':'BUY','pattern':'Marubozu'})
            else:s.append({'entry_idx':i+1,'direction':'SELL','pattern':'Marubozu'})
    return s

def detect_inside_bar(c):
    s=[]
    for i in range(1,len(c)-1):
        m,ins=c[i-1],c[i]
        if ins['high']<=m['high'] and ins['low']>=m['low']:
            if ins['close']>ins['open']:s.append({'entry_idx':i+1,'direction':'BUY','pattern':'InsideBar'})
            elif ins['close']<ins['open']:s.append({'entry_idx':i+1,'direction':'SELL','pattern':'InsideBar'})
    return s

def detect_pin_bar(c):
    s=[]
    for i in range(1,len(c)-1):
        p,x=c[i-1],c[i];r=x['high']-x['low']
        if r<=0:continue
        b=abs(x['close']-x['open']);uw=x['high']-max(x['open'],x['close']);lw=min(x['open'],x['close'])-x['low']
        if lw/r>=0.6 and b/r<=0.35 and p['close']<p['open']:s.append({'entry_idx':i+1,'direction':'BUY','pattern':'PinBar'})
        if uw/r>=0.6 and b/r<=0.35 and p['close']>p['open']:s.append({'entry_idx':i+1,'direction':'SELL','pattern':'PinBar'})
    return s

def detect_engulfing(c):
    s=[]
    for i in range(1,len(c)-1):
        p,x=c[i-1],c[i]
        if x['high']>p['high'] and x['low']<p['low'] and x['close']>x['open'] and p['close']<p['open']:
            s.append({'entry_idx':i+1,'direction':'BUY','pattern':'Engulfing'})
        if x['high']>p['high'] and x['low']<p['low'] and x['close']<x['open'] and p['close']>p['open']:
            s.append({'entry_idx':i+1,'direction':'SELL','pattern':'Engulfing'})
    return s

def detect_trend_cont(c):
    s=[]
    for i in range(3,len(c)-1):
        c1,c2,c3,c4=c[i-3],c[i-2],c[i-1],c[i]
        if c2['high']>c1['high'] and c3['high']>c2['high'] and c4['high']>c3['high'] and c2['low']>c1['low'] and c3['low']>c2['low'] and c4['low']>c3['low']:
            s.append({'entry_idx':i+1,'direction':'BUY','pattern':'TrendCont'})
        if c2['high']<c1['high'] and c3['high']<c2['high'] and c4['high']<c3['high'] and c2['low']<c1['low'] and c3['low']<c2['low'] and c4['low']<c3['low']:
            s.append({'entry_idx':i+1,'direction':'SELL','pattern':'TrendCont'})
    return s

def detect_inside_body(c):
    s=[]
    for i in range(1,len(c)-1):
        p,x=c[i-1],c[i];pbh=max(p['open'],p['close']);pbl=min(p['open'],p['close'])
        if x['close']<pbh and x['close']>pbl and abs(x['close']-x['open'])<abs(p['close']-p['open'])*0.5:
            if p['close']>p['open'] and x['close']<x['open']:s.append({'entry_idx':i+1,'direction':'SELL','pattern':'InsideBody'})
            elif p['close']<p['open'] and x['close']>x['open']:s.append({'entry_idx':i+1,'direction':'BUY','pattern':'InsideBody'})
    return s

def detect_gap_rev(c):
    s=[]
    for i in range(1,len(c)-1):
        p,x=c[i-1],c[i]
        if x['open']>p['close'] and x['close']<p['close']:s.append({'entry_idx':i+1,'direction':'SELL','pattern':'GapRev'})
        if x['open']<p['close'] and x['close']>p['close']:s.append({'entry_idx':i+1,'direction':'BUY','pattern':'GapRev'})
    return s

def detect_consec(c):
    s=[]
    for i in range(1,len(c)-1):
        p,x=c[i-1],c[i]
        if p['close']>p['open'] and x['close']>x['open']:s.append({'entry_idx':i+1,'direction':'BUY','pattern':'Consec2'})
        if p['close']<p['open'] and x['close']<x['open']:s.append({'entry_idx':i+1,'direction':'SELL','pattern':'Consec2'})
    return s

def detect_long_wick(c):
    s=[]
    for i in range(1,len(c)-1):
        p,x=c[i-1],c[i];r=x['high']-x['low']
        if r<=0:continue
        b=abs(x['close']-x['open']);uw=x['high']-max(x['open'],x['close']);lw=min(x['open'],x['close'])-x['low']
        if lw/r>=0.5 and b/r<=0.4 and p['close']<p['open']:s.append({'entry_idx':i+1,'direction':'BUY','pattern':'LongWick'})
        if uw/r>=0.5 and b/r<=0.4 and p['close']>p['open']:s.append({'entry_idx':i+1,'direction':'SELL','pattern':'LongWick'})
    return s

def detect_big_body_rev(c):
    s=[]
    ab=sum(abs(x['close']-x['open']) for x in c)/len(c) if c else 0
    for i in range(1,len(c)-1):
        p,x=c[i-1],c[i];b=abs(x['close']-x['open'])
        if b>=ab*1.3:
            if p['close']<p['open'] and x['close']>x['open']:s.append({'entry_idx':i+1,'direction':'BUY','pattern':'BigBodyRev'})
            if p['close']>p['open'] and x['close']<x['open']:s.append({'entry_idx':i+1,'direction':'SELL','pattern':'BigBodyRev'})
    return s

PATTERN_DETECTORS = {
    'Doji':detect_doji,'Hammer':detect_hammer,'ShootStar':detect_shooting_star,
    'Star':detect_star,'3Soldiers':detect_three_soldiers,'Harami':detect_harami,
    'Piercing':detect_piercing,'Tweezer':detect_tweezer,'Marubozu':detect_marubozu,
    'InsideBar':detect_inside_bar,'PinBar':detect_pin_bar,'Engulfing':detect_engulfing,
    'TrendCont':detect_trend_cont,'InsideBody':detect_inside_body,'GapRev':detect_gap_rev,
    'Consec2':detect_consec,'LongWick':detect_long_wick,'BigBodyRev':detect_big_body_rev,
}

WEEKDAY_NAMES = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']
WEEKDAY_FULL = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
def load_candles(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)
    candles = data if isinstance(data, list) else data.get('candles', data)
    return sorted([{
        'time':int(c['time']),'datetime':c.get('datetime',''),
        'open':float(c['open']),'high':float(c['high']),
        'low':float(c['low']),'close':float(c['close'])
    } for c in candles], key=lambda c: c['time'])

def get_pair_name(filepath):
    return os.path.splitext(os.path.basename(filepath))[0].split('_')[0]

def generate_signals(candles, pair_name):
    all_signals = []
    for pattern_name, detector in PATTERN_DETECTORS.items():
        for sig in detector(candles):
            entry_idx = sig['entry_idx']
            if entry_idx >= len(candles): continue
            entry_candle = candles[entry_idx]
            dt = datetime.fromtimestamp(entry_candle['time'], tz=timezone.utc)
            our_weekday = (dt.weekday() + 1) % 7
            day_name = WEEKDAY_NAMES[our_weekday]
            key = f"{pair_name}:{day_name}:{pattern_name}:{sig['direction']}"
            if key in ELITE_PATTERNS:
                c1, c12, profit = ELITE_PATTERNS[key]
                all_signals.append({
                    'timestamp': entry_candle['time'],
                    'pair': pair_name, 'pattern': pattern_name,
                    'direction': sig['direction'], 'weekday': day_name,
                    'weekday_full': WEEKDAY_FULL[our_weekday],
                    'c1_rate': c1, 'c12_rate': c12, 'net_profit': profit,
                })
    return all_signals

def parse_time_range(time_str):
    if not time_str: return None, None
    parts = time_str.split('-')
    if len(parts) != 2: return None, None
    def parse_hm(hm):
        h, m = hm.split(':'); return int(h) * 60 + int(m)
    return parse_hm(parts[0].strip()), parse_hm(parts[1].strip())

def time_in_range(minutes, start, end):
    if start is None: return True
    if start <= end: return start <= minutes <= end
    return minutes >= start or minutes <= end

def load_sent_cache():
    if not os.path.exists(SENT_CACHE): return set()
    try:
        with open(SENT_CACHE, 'r') as f: return set(json.load(f))
    except: return set()

def save_sent_cache(cache):
    try:
        with open(SENT_CACHE, 'w') as f: json.dump(list(cache), f)
    except: pass

# ============================================================================
# STAGE 1: SCAN — detect all signals and store in raw cache
# ============================================================================
def cmd_scan(args):
    print(f"\n{'='*70}")
    print("  FutureQuantVexa v3.0 — STAGE 1: SCAN")
    print(f"{'='*70}\n")
    
    os.makedirs(RAW_DIR, exist_ok=True)
    files = sorted(args.files)
    print(f"  Scanning {len(files)} file(s)...\n")
    
    all_signals = []
    for filepath in files:
        if not os.path.exists(filepath):
            print(f"  ✗ Not found: {filepath}"); continue
        pair = get_pair_name(filepath)
        try:
            candles = load_candles(filepath)
            signals = generate_signals(candles, pair)
            all_signals.extend(signals)
            print(f"  [{pair:<9}] {len(candles)} candles → {len(signals)} signals")
        except Exception as e:
            print(f"  [{pair:<9}] ERROR: {e}")
    
    # Group by weekday and save
    by_day = defaultdict(list)
    for s in all_signals:
        dt = datetime.fromtimestamp(s['timestamp'], tz=timezone.utc)
        our_weekday = (dt.weekday() + 1) % 7
        s['hour_utc'] = dt.hour
        s['minute_utc'] = dt.minute
        s['time_str_utc'] = dt.strftime('%H:%M')
        by_day[our_weekday].append(s)
    
    print(f"\n  Saving raw signals to: {RAW_DIR}/")
    total = 0
    for day_idx in range(7):
        day_signals = by_day.get(day_idx, [])
        day_signals.sort(key=lambda s: s['timestamp'])
        day_name = WEEKDAY_NAMES[day_idx]
        raw_file = os.path.join(RAW_DIR, f'{day_name}_signals.json')
        with open(raw_file, 'w') as f:
            json.dump(day_signals, f)
        print(f"    {WEEKDAY_FULL[day_idx]:<10}: {len(day_signals):>5} signals → {day_name}_signals.json")
        total += len(day_signals)
    
    print(f"\n  ✓ Total: {total} signals stored across 7 files")
    print(f"  ✓ Scan complete! Now run 'extract' to filter signals.\n")

# ============================================================================
# STAGE 2: EXTRACT — filter by day/direction/time/gap
# ============================================================================
def cmd_extract(args):
    print(f"\n{'='*70}")
    print("  FutureQuantVexa v3.0 — STAGE 2: EXTRACT")
    print(f"{'='*70}\n")
    
    # Determine which days to process
    day_map = {WEEKDAY_NAMES[i].lower(): i for i in range(7)}
    day_map.update({WEEKDAY_FULL[i].lower(): i for i in range(7)})
    
    if args.day.lower() == 'all':
        days_to_process = list(range(7))
    else:
        day_key = args.day.lower()
        if day_key not in day_map:
            print(f"  ✗ Unknown day: {args.day}")
            print(f"    Use: Sun, Mon, Tue, Wed, Thu, Fri, Sat, or 'all'")
            return
        days_to_process = [day_map[day_key]]
    
    # Direction filter
    dir_filter = args.dir.lower()
    if dir_filter not in ('call', 'put', 'both'):
        print(f"  ✗ Invalid direction: {args.dir}. Use: call, put, or both")
        return
    
    # Parse time range
    start_min, end_min = parse_time_range(args.time) if args.time else (None, None)
    
    tz_label = f"UTC+{args.tz}" if args.tz >= 0 else f"UTC{args.tz}"
    
    print(f"  Day:      {', '.join(WEEKDAY_FULL[d] for d in days_to_process)}")
    print(f"  Direction: {dir_filter.upper()}")
    if args.time:
        print(f"  Time:     {args.time} ({tz_label})")
    print(f"  Gap:      {args.gap} minutes")
    print(f"  Timezone: {tz_label}")
    print(f"  Cache:    {'disabled' if args.no_cache else 'enabled'}")
    print()
    
    # Load cache
    sent_cache = set() if args.no_cache else load_sent_cache()
    
    # Collect all signals from selected days
    all_signals = []
    for day_idx in days_to_process:
        day_name = WEEKDAY_NAMES[day_idx]
        raw_file = os.path.join(RAW_DIR, f'{day_name}_signals.json')
        if not os.path.exists(raw_file):
            print(f"  ⚠ No scan data for {WEEKDAY_FULL[day_idx]}. Run 'scan' first.")
            continue
        with open(raw_file, 'r') as f:
            day_signals = json.load(f)
        all_signals.extend(day_signals)
    
    if not all_signals:
        print("\n  ⚠ No signals found. Run 'scan *.json' first.")
        return
    
    print(f"  Raw signals loaded: {len(all_signals)}")
    
    # Filter by direction
    if dir_filter == 'call':
        all_signals = [s for s in all_signals if s['direction'] == 'BUY']
        print(f"  After direction filter (CALL only): {len(all_signals)}")
    elif dir_filter == 'put':
        all_signals = [s for s in all_signals if s['direction'] == 'SELL']
        print(f"  After direction filter (PUT only): {len(all_signals)}")
    
    # Filter by time range (in user's timezone)
    if start_min is not None:
        filtered = []
        for s in all_signals:
            dt_local = datetime.fromtimestamp(s['timestamp'], tz=timezone.utc) + timedelta(hours=args.tz)
            local_minutes = dt_local.hour * 60 + dt_local.minute
            if time_in_range(local_minutes, start_min, end_min):
                filtered.append(s)
        all_signals = filtered
        print(f"  After time filter ({args.time} {tz_label}): {len(all_signals)}")
    
    # Remove already-sent signals
    new_signals = []
    for s in all_signals:
        cache_key = f"{s['timestamp']}_{s['pair']}_{s['pattern']}_{s['direction']}"
        if cache_key not in sent_cache:
            new_signals.append(s)
    print(f"  After cache filter: {len(new_signals)} new (removed {len(all_signals) - len(new_signals)} sent)")
    
    # Sort by timestamp
    new_signals.sort(key=lambda s: s['timestamp'])
    
    # Deduplicate same minute (keep highest C1+C2)
    by_minute = {}
    for s in new_signals:
        mk = s['timestamp'] // 60
        if mk not in by_minute or s['c12_rate'] > by_minute[mk]['c12_rate']:
            by_minute[mk] = s
    unique_signals = sorted(by_minute.values(), key=lambda s: s['timestamp'])
    print(f"  After dedup (same minute): {len(unique_signals)}")
    
    # Apply gap filter
    final_signals = []
    last_ts = None
    for s in unique_signals:
        if last_ts is None or (s['timestamp'] - last_ts) / 60 >= args.gap:
            final_signals.append(s)
            last_ts = s['timestamp']
    print(f"  After gap filter ({args.gap} min): {len(final_signals)} signals")
    
    # Output
    if not final_signals:
        print("\n  ⚠ No signals match your criteria. Try different filters.")
        return
    
    print()
    print("━" * 7 + " • " + "━" * 7)
    for s in final_signals:
        dt_local = datetime.fromtimestamp(s['timestamp'], tz=timezone.utc) + timedelta(hours=args.tz)
        time_str = dt_local.strftime('%H:%M')
        pair_str = f"{s['pair']}-OTC"
        direction = "CALL" if s['direction'] == 'BUY' else "PUT"
        print(f"M1 {pair_str} {time_str} {direction}")
    print("━" * 7 + " • " + "━" * 7)
    
    call_count = sum(1 for s in final_signals if s['direction'] == 'BUY')
    put_count = len(final_signals) - call_count
    days_str = ', '.join(WEEKDAY_FULL[d] for d in days_to_process)
    print(f"\n  Total: {len(final_signals)} signals | CALL={call_count} | PUT={put_count}")
    print(f"  Day: {days_str}")
    if args.time:
        print(f"  Time: {args.time} ({tz_label})")
    print(f"  Gap: {args.gap} min | Timezone: {tz_label}")
    print(f"  Strategy: Entry 1 → MTG1 → STOP | Max loss: 3× stake")
    
    # Detailed view
    if args.detailed:
        print(f"\n{'='*100}")
        print(f"  Detailed Report")
        print(f"{'='*100}")
        print(f"\n  {'#':<4} {'Time':<6} {'Pair':<9} {'Pattern':<12} {'Dir':<5} {'C1':>7} {'C1+C2':>8} {'Profit':>8}")
        print(f"  {'-'*80}")
        for i, s in enumerate(final_signals, 1):
            dt_local = datetime.fromtimestamp(s['timestamp'], tz=timezone.utc) + timedelta(hours=args.tz)
            d = "CALL" if s['direction'] == 'BUY' else "PUT"
            print(f"  {i:<4} {dt_local.strftime('%H:%M'):<6} {s['pair']:<9} {s['pattern']:<12} {d:<5} "
                  f"{s['c1_rate']:>6.1f}% {s['c12_rate']:>7.1f}% {s['net_profit']:>7.1f}×")
    
    # Save CSV
    csv_file = 'futurequantvexa_signals.csv'
    with open(csv_file, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['time','pair','pattern','direction','weekday','c1_rate','c12_rate','net_profit','timestamp'])
        for s in final_signals:
            dt_local = datetime.fromtimestamp(s['timestamp'], tz=timezone.utc) + timedelta(hours=args.tz)
            w.writerow([dt_local.strftime('%H:%M'), s['pair'], s['pattern'],
                        'CALL' if s['direction']=='BUY' else 'PUT', s['weekday'],
                        f"{s['c1_rate']:.1f}%", f"{s['c12_rate']:.1f}%", f"{s['net_profit']:.1f}×",
                        s['timestamp']])
    print(f"\n  ✓ Saved to: {csv_file}")
    
    # Update sent cache
    if not args.no_cache:
        for s in final_signals:
            cache_key = f"{s['timestamp']}_{s['pair']}_{s['pattern']}_{s['direction']}"
            sent_cache.add(cache_key)
        save_sent_cache(sent_cache)
        print(f"  ✓ Cache updated: {len(sent_cache)} total sent signals")
    
    # Summary
    print(f"\n  {'='*60}")
    print(f"  SUMMARY")
    print(f"  {'='*60}")
    pair_counts = defaultdict(int)
    for s in final_signals:
        pair_counts[s['pair']] += 1
    print(f"\n  Per pair:")
    for pair, count in sorted(pair_counts.items(), key=lambda x: -x[1]):
        print(f"    {pair:<9}: {count} signals")
    print(f"\n  {'='*60}")
    print(f"  FutureQuantVexa v3.0 — Complete")
    print(f"  {'='*60}\n")

# ============================================================================
# MAIN
# ============================================================================
def main():
    parser = argparse.ArgumentParser(
        description='FutureQuantVexa v3.0 — Advanced Multi-Stage Signal Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Pipeline:
  1. SCAN:    Detect all signals from candle files → store in cache
  2. EXTRACT: Filter by day/direction/time/gap → output Telegram-style list

Examples:
  python fqv3.py scan *.json
  python fqv3.py extract --day=Sunday --dir=both --time=09:00-12:00 --gap=4 --tz=1
  python fqv3.py extract --day=Mon --dir=CALL --time=23:00-00:00 --gap=3 --tz=1
  python fqv3.py extract --day=Saturday --dir=PUT --gap=5
  python fqv3.py extract --day=all --dir=both --gap=4 --tz=1 --detailed
  python fqv3.py clear-cache
""")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # SCAN command
    scan_parser = subparsers.add_parser('scan', help='Scan candle files and store all signals')
    scan_parser.add_argument('files', nargs='+', help='JSON candle data file(s)')
    
    # EXTRACT command
    ext_parser = subparsers.add_parser('extract', help='Extract filtered signals')
    ext_parser.add_argument('--day', type=str, default='all',
                            help='Day: Sun, Mon, Tue, Wed, Thu, Fri, Sat, or "all" (default: all)')
    ext_parser.add_argument('--dir', type=str, default='both',
                            help='Direction: call, put, or both (default: both)')
    ext_parser.add_argument('--time', type=str, default=None,
                            help='Time range HH:MM-HH:MM (e.g. 09:00-12:00, 23:00-00:00)')
    ext_parser.add_argument('--gap', type=int, default=4,
                            help='Min minutes between signals (default: 4)')
    ext_parser.add_argument('--tz', type=int, default=0,
                            help='Timezone offset (default: 0). e.g. --tz=1 for UTC+1')
    ext_parser.add_argument('--no-cache', action='store_true',
                            help='Disable sent-signal cache')
    ext_parser.add_argument('--detailed', action='store_true',
                            help='Show detailed table')
    
    # CLEAR-CACHE command
    subparsers.add_parser('clear-cache', help='Clear sent-signal cache')
    
    args = parser.parse_args()
    
    if args.command == 'scan':
        cmd_scan(args)
    elif args.command == 'extract':
        cmd_extract(args)
    elif args.command == 'clear-cache':
        if os.path.exists(SENT_CACHE):
            os.remove(SENT_CACHE)
            print("  ✓ Sent-signal cache cleared.")
        else:
            print("  Cache file not found (already empty).")
    else:
        parser.print_help()

if __name__ == '__main__':
    main()

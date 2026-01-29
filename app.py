import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime

# UI Config
st.set_page_config(page_title="Multi-Exchange Scanner", layout="wide")

def get_exchange(exchange_id):
    if exchange_id == 'gateio':
        return ccxt.gateio({
            'timeout': 20000,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'} # Mandatory for Gate.io Futures
        })
    else:
        return ccxt.mexc({
            'timeout': 20000,
            'enableRateLimit': True
        })

def get_data(exchange_id, symbol, tf):
    try:
        ex = get_exchange(exchange_id)
        # Gate.io sometimes uses '_' instead of '/' in API, CCXT handles this
        bars = ex.fetch_ohlcv(symbol, tf, limit=110)
        if not bars or len(bars) < 100: return None
        
        df = pd.DataFrame(bars, columns=['ts','o','h','l','c','v'])
        df['SMA20'] = ta.sma(df['c'], 20)
        df['SMA100'] = ta.sma(df['c'], 100)
        df['RSI'] = ta.rsi(df['c'], 14)
        return df
    except Exception as e:
        return None

def analyze(exchange_id, symbol):
    # Fetching the standard 15m/1h/4h bias + 3m/5m triggers
    tfs = {}
    for tf in ['3m', '5m', '15m', '1h', '4h']:
        df = get_data(exchange_id, symbol, tf)
        if df is None: return []
        tfs[tf] = df

    # Bias Logic
    b15 = "BULL" if tfs['15m'].iloc[-1]['c'] > tfs['15m'].iloc[-1]['SMA100'] else "BEAR"
    
    results = []
    for tf_name in ['3m', '5m']:
        df = tfs[tf_name]
        curr, prev = df.iloc[-1], df.iloc[-2]
        
        # Triple-Lock Logic
        body = abs(curr['c'] - curr['o'])
        avg_body = abs(df['c'] - df['o']).tail(20).mean()
        is_expanding = abs(curr['SMA20'] - curr['SMA100']) > abs(prev['SMA20'] - prev['SMA100'])
        
        status, tier = "WAIT", "Wait"
        if (body > avg_body * 2.5) and is_expanding:
            p_dir = "LONG" if curr['c'] > curr['SMA20'] else "SHORT"
            if (p_dir == "LONG" and b15 == "BULL") or (p_dir == "SHORT" and b15 == "BEAR"):
                status, tier = p_dir, "A"
            else:
                status, tier = p_dir, "Caution"

        results.append({
            "Ex": exchange_id.upper(),
            "Symbol": symbol,
            "Price": f"{curr['c']:.8f}".rstrip('0').rstrip('.'),
            "Vol": f"{curr['v']:,.0f}",
            "TF": tf_name,
            "Action": status,
            "Tier": tier
        })
    return results

# Combined Watchlist
gate_watchlist = ["PEPE/USDT", "WIF/USDT", "BONK/USDT"] 
mexc_watchlist = ["BTC/USDT", "SOL/USDT", "PNUT/USDT"]

if st.button("🚀 SCAN BOTH EXCHANGES"):
    all_res = []
    # Scan Gate.io
    for coin in gate_watchlist:
        res = analyze('gateio', coin)
        if res: all_res.extend(res)
    # Scan MEXC
    for coin in mexc_watchlist:
        res = analyze('mexc', coin)
        if res: all_res.extend(res)
    
    if all_res:
        st.table(pd.DataFrame(all_res))

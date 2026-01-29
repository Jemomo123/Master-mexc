import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime

# Clean Mobile UI
st.set_page_config(page_title="Expansion Monitor", layout="wide")

def get_data(ex_id, symbol, tf):
    try:
        # Use CCXT 2026 unified API domains
        if ex_id == 'gateio':
            ex = ccxt.gateio({'timeout': 10000, 'options': {'defaultType': 'swap'}})
        else:
            ex = ccxt.mexc({'timeout': 10000})
            
        bars = ex.fetch_ohlcv(symbol, tf, limit=110)
        if not bars or len(bars) < 100: return None
        
        df = pd.DataFrame(bars, columns=['ts','o','h','l','c','v'])
        df['SMA20'] = ta.sma(df['c'], 20)
        df['SMA100'] = ta.sma(df['c'], 100)
        df['RSI'] = ta.rsi(df['c'], 14)
        return df
    except:
        return None

def analyze(ex_id, symbol):
    # Fetch 3m, 5m, 15m, 1h, 4h
    tfs = {tf: get_data(ex_id, symbol, tf) for tf in ['3m', '5m', '15m', '1h', '4h']}
    
    # If API fails, return a simple skip row
    if any(v is None for v in tfs.values()):
        return [{
            "Time": datetime.now().strftime("%H:%M:%S"),
            "Symbol": symbol.split(':')[0],
            "Price": "-", "Vol": "-", "TF": "-", "Action": "SKIP", "Tier": "-", "Reason": "API Timeout"
        }]

    # Bias Logic
    b15 = "BULL" if tfs['15m'].iloc[-1]['c'] > tfs['15m'].iloc[-1]['SMA100'] else "BEAR"
    
    results = []
    timestamp = datetime.now().strftime("%H:%M:%S")

    for tf_name in ['3m', '5m']:
        df = tfs[tf_name]
        curr, prev = df.iloc[-1], df.iloc[-2]
        
        # Trigger Logic
        body = abs(curr['c'] - curr['o'])
        avg_body = abs(df['c'] - df['o']).tail(20).mean()
        is_expanding = abs(curr['SMA20'] - curr['SMA100']) > abs(prev['SMA20'] - prev['SMA100'])
        
        status, tier, reason = "WAIT", "Wait", "Narrowing"

        if (body > avg_body * 2.5) and is_expanding:
            p_dir = "LONG" if curr['c'] > curr['SMA20'] else "SHORT"
            if (p_dir == "LONG" and b15 == "BULL") or (p_dir == "SHORT" and b15 == "BEAR"):
                status, tier, reason = p_dir, "A", "Expansion + Bias"
            else:
                status, tier, reason = p_dir, "Caution", "Bias Conflict"

        # BUILD TABLE (Removed 'Ex' column for cleaner mobile view)
        results.append({
            "Time": timestamp,
            "Symbol": symbol.split(':')[0],
            "Price": f"{curr['c']:.8f}".rstrip('0').rstrip('.'),
            "Vol": f"{curr['v']:,.0f}",
            "TF": tf_name,
            "Action": status,
            "Tier": tier,
            "Reason": reason
        })
    return results

# Combined lists
mexc_list = ["BTC/USDT", "SOL/USDT", "PNUT/USDT"]
gate_list = ["PEPE/USDT", "WIF/USDT", "BONK/USDT", "POPCAT/USDT"]

if st.button("🚀 SCAN MARKETS"):
    all_rows = []
    # Loop both exchanges
    for s in mexc_list: all_rows.extend(analyze('mexc', s))
    for s in gate_list: all_rows.extend(analyze('gateio', s))
        
    if all_rows:
        final_df = pd.DataFrame(all_rows)
        # Force column order (No Exchange Column)
        cols = ["Time", "Symbol", "Price", "Vol", "TF", "Action", "Tier", "Reason"]
        st.table(final_df[cols])

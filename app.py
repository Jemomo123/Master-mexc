import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime

# UI Config for Mobile
st.set_page_config(page_title="Expansion Monitor", layout="wide")
st.title("🛡️ Conviction Edge Scanner")

def get_data(symbol, tf):
    try:
        # Initializing MEXC with a timeout to prevent hanging
        ex = ccxt.mexc({'timeout': 10000, 'enableRateLimit': True})
        bars = ex.fetch_ohlcv(symbol, tf, limit=110)
        if not bars: return None
        df = pd.DataFrame(bars, columns=['ts','o','h','l','c','v'])
        df['SMA20'] = ta.sma(df['c'], 20)
        df['SMA100'] = ta.sma(df['c'], 100)
        df['RSI'] = ta.rsi(df['c'], 14)
        return df
    except: return None

def analyze(symbol):
    # Timeframes for bias and monitoring
    tfs_to_fetch = ['3m', '5m', '15m', '1h', '4h']
    tfs = {}
    
    for tf in tfs_to_fetch:
        data = get_data(symbol, tf)
        if data is None or len(data) < 101: # Check for enough data for SMA100
            return [] 
        tfs[tf] = data

    # BIAS CHECK
    b15 = "BULL" if tfs['15m'].iloc[-1]['c'] > tfs['15m'].iloc[-1]['SMA100'] else "BEAR"
    b1h = "BULL" if tfs['1h'].iloc[-1]['c'] > tfs['1h'].iloc[-1]['SMA100'] else "BEAR"
    b4h = "BULL" if tfs['4h'].iloc[-1]['c'] > tfs['4h'].iloc[-1]['SMA100'] else "BEAR"
    macro_aligned = (b1h == b4h == b15)

    results = []
    for tf_name in ['3m', '5m']:
        df = tfs[tf_name]
        curr, prev = df.iloc[-1], df.iloc[-2]
        
        signal_time = datetime.now().strftime("%H:%M:%S")
        entry_price = curr['c']
        vol = curr['v'] # Current volume of the candle

        # Mandatory Bar Confirmation
        body = abs(curr['c'] - curr['o'])
        avg_body = abs(df['c'] - df['o']).tail(20).mean()
        confirmed = (body > avg_body * 2.5) or \
                    (curr['h'] - max(curr['c'],curr['o']) > body * 2) or \
                    (min(curr['c'],curr['o']) - curr['l'] > body * 2)

        is_expanding = abs(curr['SMA20'] - curr['SMA100']) > abs(prev['SMA20'] - prev['SMA100'])
        
        status, tier, reason = "WAIT", "Wait", "Searching Setup..."

        if confirmed and is_expanding:
            p_dir = "LONG" if curr['c'] > curr['SMA20'] else "SHORT"
            is_void = (p_dir == "LONG" and curr['RSI'] > 65) or (p_dir == "SHORT" and curr['RSI'] < 35)
            
            if (p_dir == "LONG" and b15 == "BULL") or (p_dir == "SHORT" and b15 == "BEAR"):
                if macro_aligned and is_void:
                    status, tier, reason = p_dir, "A+", "Expansion + Bias + Macro + Void"
                else:
                    status, tier, reason = p_dir, "A", "Expansion + Bias + Bar"
            else:
                status, tier, reason = p_dir, "Caution", "Bias Conflict (15m)"

        results.append({
            "Time": signal_time,
            "Symbol": symbol,
            "Price": f"{entry_price:.8f}".rstrip('0').rstrip('.'),
            "Vol": f"{vol:,.0f}", # Formatted Volume
            "TF": tf_name,
            "Action": status,
            "Tier": tier,
            "Reason": reason
        })
    return results

# Expanded Watchlist
watchlist = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT", "SPX/USDT", "WIF/USDT", "BONK/USDT", "FLOKI/USDT", "POPCAT/USDT"]

if st.button("🚀 SCAN CONVICTION"):
    data = []
    for coin in watchlist:
        res = analyze(coin)
        for r in res: data.append(r)
    
    if data:
        df_final = pd.DataFrame(data)
        tier_order = {"A+": 0, "A": 1, "Caution": 2, "Wait": 3}
        df_final['Rank'] = df_final['Tier'].map(tier_order)
        df_final = df_final.sort_values('Rank').drop('Rank', axis=1)
        st.table(df_final)
    else:
        st.warning("No data found. Check your internet or MEXC API status.")

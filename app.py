import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime

# Streamlit UI Config for Mobile
st.set_page_config(page_title="Expansion Monitor", layout="wide")
st.title("🛡️ Conviction Edge Scanner")

def get_data(symbol, tf):
    try:
        ex = ccxt.mexc() # Optimized for MEXC
        bars = ex.fetch_ohlcv(symbol, tf, limit=110)
        df = pd.DataFrame(bars, columns=['ts','o','h','l','c','v'])
        df['SMA20'] = ta.sma(df['c'], 20)
        df['SMA100'] = ta.sma(df['c'], 100)
        df['RSI'] = ta.rsi(df['c'], 14)
        return df
    except Exception: return None

def analyze(symbol):
    # Fetch all relevant timeframes (as per preferences)
    tfs = {tf: get_data(symbol, tf) for tf in ['3m', '5m', '15m', '1h', '4h']}
    
    # 1. BIAS CHECK (HTF Permission)
    b15 = "BULL" if tfs['15m'].iloc[-1]['c'] > tfs['15m'].iloc[-1]['SMA100'] else "BEAR"
    b1h = "BULL" if tfs['1h'].iloc[-1]['c'] > tfs['1h'].iloc[-1]['SMA100'] else "BEAR"
    b4h = "BULL" if tfs['4h'].iloc[-1]['c'] > tfs['4h'].iloc[-1]['SMA100'] else "BEAR"
    macro_aligned = (b1h == b4h == b15)

    results = []
    # Loop execution timeframes
    for tf_name in ['3m', '5m']:
        df = tfs[tf_name]
        if df is None: continue
        curr, prev = df.iloc[-1], df.iloc[-2]
        
        # 2. THE TRIGGER: Elephant or Tail Bar
        body = abs(curr['c'] - curr['o'])
        avg_body = abs(df['c'] - df['o']).tail(20).mean()
        is_confirmed = (body > avg_body * 2.5) or \
                       (curr['h'] - max(curr['c'],curr['o']) > body * 2) or \
                       (min(curr['c'],curr['o']) - curr['l'] > body * 2)

        # 3. EXPANSION CHECK
        is_expanding = abs(curr['SMA20'] - curr['SMA100']) > abs(prev['SMA20'] - prev['SMA100'])
        
        # Initialize Output
        status, tier, reason = "WAIT", "Wait", "No Expansion/Bar"
        signal_time = datetime.now().strftime("%H:%M:%S")
        entry_price = curr['c']

        if is_confirmed and is_expanding:
            p_dir = "LONG" if curr['c'] > curr['SMA20'] else "SHORT"
            is_void = (p_dir == "LONG" and curr['RSI'] > 65) or (p_dir == "SHORT" and curr['RSI'] < 35)
            
            # Match current action to 15m trend
            if (p_dir == "LONG" and b15 == "BULL") or (p_dir == "SHORT" and b15 == "BEAR"):
                if macro_aligned and is_void:
                    status, tier, reason = p_dir, "A+", "Expansion + Bias + Macro + Void"
                else:
                    status, tier, reason = p_dir, "A", "Confirmed Expansion + 15m Bias"
            else:
                status, tier, reason = p_dir, "Caution", "Counter-Trend (15m Conflict)"

        results.append({
            "Time": signal_time,
            "Symbol": symbol,
            "Price": entry_price,
            "TF": tf_name,
            "Action": status,
            "Tier": tier,
            "Reason": reason
        })
    return results

# Scalper's Watchlist
watchlist = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "PEPE/USDT", "WIF/USDT"]

if st.button("🚀 RUN SCAN"):
    data = []
    for coin in watchlist:
        res = analyze(coin)
        for r in res: data.append(r)
    
    # Sort by Tier Priority (A+ first)
    df_final = pd.DataFrame(data)
    tier_order = {"A+": 0, "A": 1, "Caution": 2, "Wait": 3}
    df_final['Rank'] = df_final['Tier'].map(tier_order)
    df_final = df_final.sort_values('Rank').drop('Rank', axis=1)
    
    st.table(df_final)

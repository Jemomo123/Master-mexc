import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime
import time

# Mobile UI Optimization
st.set_page_config(page_title="Conviction Edge", layout="wide")

# CSS to make the table look better on mobile
st.markdown("""
    <style>
    .stTable { font-size: 12px !important; }
    div[data-testid="stMetricValue"] { font-size: 18px !important; }
    </style>
    """, unsafe_allow_html=True)

def get_data(symbol, tf):
    try:
        # Using the unified MEXC API domain for 2026 stability
        ex = ccxt.mexc({'timeout': 10000, 'enableRateLimit': True})
        bars = ex.fetch_ohlcv(symbol, tf, limit=110)
        if not bars or len(bars) < 100: return None
        
        df = pd.DataFrame(bars, columns=['ts','o','h','l','c','v'])
        df['SMA20'] = ta.sma(df['c'], 20)
        df['SMA100'] = ta.sma(df['c'], 100)
        df['RSI'] = ta.rsi(df['c'], 14)
        return df
    except:
        return None

def analyze(symbol):
    tfs_needed = ['3m', '5m', '15m', '1h', '4h']
    data_map = {}
    
    for tf in tfs_needed:
        df = get_data(symbol, tf)
        if df is None: return [] # Skip if any timeframe fails
        data_map[tf] = df

    # Bias Rules
    last_15m = data_map['15m'].iloc[-1]
    last_1h = data_map['1h'].iloc[-1]
    last_4h = data_map['4h'].iloc[-1]
    
    b15 = "BULL" if last_15m['c'] > last_15m['SMA100'] else "BEAR"
    b1h = "BULL" if last_1h['c'] > last_1h['SMA100'] else "BEAR"
    b4h = "BULL" if last_4h['c'] > last_4h['SMA100'] else "BEAR"
    macro_aligned = (b1h == b4h == b15)

    results = []
    for tf_name in ['3m', '5m']:
        df = data_map[tf_name]
        curr, prev = df.iloc[-1], df.iloc[-2]
        
        # Expansion Logic
        body = abs(curr['c'] - curr['o'])
        avg_body = abs(df['c'] - df['o']).tail(20).mean()
        is_expanding = abs(curr['SMA20'] - curr['SMA100']) > abs(prev['SMA20'] - prev['SMA100'])
        
        # Bar Confirmation (Elephant/Tail)
        is_elephant = body > (avg_body * 2.5)
        is_tail = (curr['h'] - max(curr['c'],curr['o']) > body * 2) or (min(curr['c'],curr['o']) - curr['l'] > body * 2)
        
        status, tier, reason = "WAIT", "Wait", "Searching..."

        if (is_elephant or is_tail) and is_expanding:
            p_dir = "LONG" if curr['c'] > curr['SMA20'] else "SHORT"
            is_void = (p_dir == "LONG" and curr['RSI'] > 65) or (p_dir == "SHORT" and curr['RSI'] < 35)
            
            if (p_dir == "LONG" and b15 == "BULL") or (p_dir == "SHORT" and b15 == "BEAR"):
                if macro_aligned and is_void:
                    status, tier, reason = p_dir, "A+", "Expansion + Bias + Macro + Void"
                else:
                    status, tier, reason = p_dir, "A", "Expansion + Bias + Bar"
            else:
                status, tier, reason = p_dir, "Caution", "Bias Conflict"

        results.append({
            "Time": datetime.now().strftime("%H:%M:%S"),
            "Symbol": symbol.replace("/USDT", ""),
            "Price": f"{curr['c']:.8f}".rstrip('0').rstrip('.'),
            "Vol": f"{curr['v']:,.0f}",
            "TF": tf_name,
            "Action": status,
            "Tier": tier,
            "Reason": reason
        })
    return results

# CLEANSED LIST (Removed SPX and PUMP due to API instability)
watchlist = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT", "WIF/USDT", "BONK/USDT", "POPCAT/USDT", "PEPE/USDT", "PNUT/USDT"]

# App UI
col1, col2 = st.columns([3, 1])
with col1:
    st.subheader("Live Expansion Feed")
with col2:
    if st.button("🔄 REFRESH"):
        st.rerun()

all_data = []
progress_bar = st.progress(0)

for i, coin in enumerate(watchlist):
    res = analyze(coin)
    if res:
        all_data.extend(res)
    progress_bar.progress((i + 1) / len(watchlist))

if all_data:
    final_df = pd.DataFrame(all_data)
    # Sort: A+ first, then A, then Caution
    order = {"A+": 0, "A": 1, "Caution": 2, "Wait": 3}
    final_df['Sort'] = final_df['Tier'].map(order)
    final_df = final_df.sort_values('Sort').drop('Sort', axis=1)
    
    st.table(final_df)
else:
    st.error("API Fetch Failed. Please check internet or MEXC status.")

st.caption(f"Last Heartbeat: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Expansion Monitor", layout="wide")

# Auto-refresh every 60 seconds for live mobile monitoring
st_autorefresh(interval=60000, key="live_refresh")

def check_expansion_edge(df_3m, df_15m):
    # 1. 15m Higher Timeframe Bias (The Permission)
    h_now, h_prev = df_15m.iloc[-1], df_15m.iloc[-2]
    bias = "WAIT"
    if h_now['c'] > h_now['SMA100'] and h_now['SMA20'] >= h_prev['SMA20'] and h_now['RSI'] >= 50:
        bias = "LONG"
    elif h_now['c'] < h_now['SMA100'] and h_now['SMA20'] <= h_prev['SMA20'] and h_now['RSI'] <= 50:
        bias = "SHORT"
    
    if bias == "WAIT": return "WAIT", "Wait", "15m Bias Neutral."

    # 2. Expansion Event (3m/5m Structure)
    curr, prev = df_3m.iloc[-1], df_3m.iloc[-2]
    if abs(curr['SMA20'] - curr['SMA100']) <= abs(prev['SMA20'] - prev['SMA100']):
        return "WAIT", "Wait", "No Expansion (Squeeze Phase)."

    # 3. Candle Confirmation (The Trigger)
    body = abs(curr['c'] - curr['o'])
    avg_body = abs(df_3m['c'] - df_3m['o']).tail(20).mean()
    is_elephant = body > (avg_body * 2.5)
    is_tail = (curr['h'] - max(curr['c'], curr['o']) > body * 2) or (min(curr['c'], curr['o']) - curr['l'] > body * 2)

    if not (is_elephant or is_tail):
        return "WAIT", "Wait", "Expanding but no Elephant/Tail bar."

    conv = "High" if (bias == "LONG" and curr['RSI'] > 55) or (bias == "SHORT" and curr['RSI'] < 45) else "Medium"
    return bias, conv, f"Confirmed {bias} Expansion."

@st.cache_data(ttl=30)
def get_data(symbol, tf):
    try:
        ex = ccxt.gateio()
        bars = ex.fetch_ohlcv(symbol, tf, limit=120)
        df = pd.DataFrame(bars, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df['SMA20'], df['SMA100'], df['RSI'] = ta.sma(df['c'], 20), ta.sma(df['c'], 100), ta.rsi(df['c'], 14)
        return df
    except: return None

st.title("🛡️ Expansion Monitor")
watchlist = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT"]
results = []

for symbol in watchlist:
    df_15 = get_data(symbol, '15m')
    if df_15 is None: continue
    for tf in ['3m', '5m']:
        df_ex = get_data(symbol, tf)
        if df_ex is None: continue
        direction, conviction, reason = check_expansion_edge(df_ex, df_15)
        results.append({"Symbol": symbol, "Timeframe": tf, "Direction": direction, "Conviction": conviction, "Reason": reason})

st.table(pd.DataFrame(results))

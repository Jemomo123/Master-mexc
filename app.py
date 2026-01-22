import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Expansion Edge Monitor", layout="wide")
st.title("🛡️ Expansion Edge: Live Monitor")
st.write("Strict Logic: SMA 20/100 | RSI | 15m Bias")

def get_data(symbol, tf):
    try:
        ex = ccxt.gateio()
        bars = ex.fetch_ohlcv(symbol, tf, limit=110)
        df = pd.DataFrame(bars, columns=['ts','o','h','l','c','v'])
        df['SMA20'] = ta.sma(df['c'], 20)
        df['SMA100'] = ta.sma(df['c'], 100)
        df['RSI'] = ta.rsi(df['c'], 14)
        return df
    except: return None

def analyze(symbol):
    df_15 = get_data(symbol, '15m')
    if df_15 is None: return []
    
    # 15m Bias
    h15 = df_15.iloc[-1]
    bias = "BULL" if h15['c'] > h15['SMA100'] and h15['RSI'] > 50 else "BEAR" if h15['c'] < h15['SMA100'] and h15['RSI'] < 50 else "NEUTRAL"

    results = []
    for tf in ['3m', '5m']:
        df = get_data(symbol, tf)
        if df is None: continue
        curr, prev = df.iloc[-1], df.iloc[-2]
        
        # Expansion Logic: Gap between 20 & 100 is widening
        is_expanding = abs(curr['SMA20'] - curr['SMA100']) > abs(prev['SMA20'] - prev['SMA100'])
        
        # Confirmation Logic: Elephant/Tail Bar
        body = abs(curr['c'] - curr['o'])
        avg_body = abs(df['c'] - df['o']).tail(20).mean()
        is_elephant = body > (avg_body * 2.5)
        is_tail = (curr['h'] - max(curr['c'], curr['o']) > body * 2) or (min(curr['c'], curr['o']) - curr['l'] > body * 2)

        # Logic Assignment
        action, conviction, reason = "WAIT", "Wait", "No Expansion"
        
        if is_expanding and (is_elephant or is_tail):
            if bias == "BULL" and curr['c'] > curr['SMA20']:
                action, conviction, reason = "LONG", "High A", "Confirmed Expansion + 15m Alignment"
            elif bias == "BEAR" and curr['c'] < curr['SMA20']:
                action, conviction, reason = "SHORT", "High A", "Confirmed Expansion + 15m Alignment"
            else:
                action, conviction, reason = "WAIT", "Caution", "Expansion exists but 15m Bias conflicts"

        results.append({"TF": tf, "Action": action, "Tier": conviction, "Reason": reason})
    return results

watchlist = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "PEPE/USDT", "WIF/USDT"]
if st.button("🚀 SCAN FOR EXPANSION", use_container_width=True):
    final_table = []
    for coin in watchlist:
        for res in analyze(coin):
            final_table.append({"Symbol": coin, **res})
    st.table(pd.DataFrame(final_table))

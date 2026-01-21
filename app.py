import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta

# 1. FORCE UI LOAD FIRST (Ensures Handshake Success)
st.set_page_config(page_title="Expansion Monitor", layout="wide")
st.title("🛡️ Expansion Edge Monitor")
st.write("3m, 5m, 15m, 1h, 4h")

# 2. THE CAST LOGIC (SMA 20/100/200 + RSI)
def check_edge(symbol):
    try:
        ex = ccxt.gateio()
        results = []
        # Get Macro Bias first (1h/4h)
        df_1h = pd.DataFrame(ex.fetch_ohlcv(symbol, '1h', limit=100), columns=['ts','o','h','l','c','v'])
        df_1h['SMA100'] = ta.sma(df_1h['c'], 100)
        
        bias = "LONG" if df_1h.iloc[-1]['c'] > df_1h.iloc[-1]['SMA100'] else "SHORT"
        
        # Check Expansion Timeframes
        for tf in ['3m', '5m', '15m']:
            bars = ex.fetch_ohlcv(symbol, tf, limit=110)
            df = pd.DataFrame(bars, columns=['ts','o','h','l','c','v'])
            df['SMA20'] = ta.sma(df['c'], 20)
            df['SMA100'] = ta.sma(df['c'], 100)
            
            curr, prev = df.iloc[-1], df.iloc[-2]
            # Expansion = Gap Widening
            is_expanding = abs(curr['SMA20'] - curr['SMA100']) > abs(prev['SMA20'] - prev['SMA100'])
            
            action = "WAIT"
            if is_expanding:
                if bias == "LONG" and curr['c'] > curr['SMA20']: action = "LONG"
                if bias == "SHORT" and curr['c'] < curr['SMA20']: action = "SHORT"
            
            results.append({"TF": tf, "Action": action, "Reason": "Expanding" if action != "WAIT" else "Squeeze"})
        return results
    except:
        return []

# 3. INTERFACE
watchlist = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]

if st.button("🚀 SCAN NOW", use_container_width=True):
    all_data = []
    for coin in watchlist:
        st.write(f"Checking {coin}...")
        res = check_edge(coin)
        for r in res:
            all_data.append({"Coin": coin, **r})
    st.table(pd.DataFrame(all_data))

import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time

# --- MOBILE UI SETUP ---
st.set_page_config(page_title="Expansion Scanner", layout="wide")

def get_data(ex, symbol, tf):
    try:
        bars = ex.fetch_ohlcv(symbol, tf, limit=120)
        df = pd.DataFrame(bars, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df['SMA20'] = ta.sma(df['c'], 20)
        df['SMA100'] = ta.sma(df['c'], 100)
        df['RSI'] = ta.rsi(df['c'], 14)
        return df
    except:
        return None

def check_expansion(df_ex, df_bias):
    # 1. Higher Timeframe (15m) Permission
    h = df_bias.iloc[-1]
    h_prev = df_bias.iloc[-2]
    
    bias = "WAIT"
    if h['c'] > h['SMA100'] and h['SMA20'] >= h_prev['SMA20'] and h['RSI'] >= 50:
        bias = "LONG"
    elif h['c'] < h['SMA100'] and h['SMA20'] <= h_prev['SMA20'] and h['RSI'] <= 50:
        bias = "SHORT"
    
    if bias == "WAIT":
        return "WAIT", "Wait", "15m Bias is Neutral or RSI in Chop Zone (45-55)."

    # 2. Expansion Logic (Gap widening between 20 and 100)
    curr, prev = df_ex.iloc[-1], df_ex.iloc[-2]
    curr_gap = abs(curr['SMA20'] - curr['SMA100'])
    prev_gap = abs(prev['SMA20'] - prev['SMA100'])
    
    if curr_gap <= prev_gap:
        return "WAIT", "Wait", "No Expansion. Price is in a Squeeze or Crossover phase."

    # 3. Candle Confirmation (Elephant or Tail)
    body = abs(curr['c'] - curr['o'])
    avg_body = abs(df_ex['c'] - df_ex['o']).tail(20).mean()
    is_elephant = body > (avg_body * 2.5)
    is_tail = (curr['h'] - max(curr['c'], curr['o']) > body * 2) or (min(curr['c'], curr['o']) - curr['l'] > body * 2)

    if not (is_elephant or is_tail):
        return "WAIT", "Wait", "Expansion present but no Elephant Bar or Tail rejection."

    # 4. Final Conviction
    conviction = "High" if (bias == "LONG" and curr['RSI'] > 55) or (bias == "SHORT" and curr['RSI'] < 45) else "Medium"
    return bias, conviction, f"Confirmed {bias} Expansion with strong price action."

def main():
    st.title("🛡️ Expansion Matrix")
    
    # Connect to both Exchanges
    gate = ccxt.gateio({'apiKey': st.secrets["GATE_KEY"], 'secret': st.secrets["GATE_SEC"]})
    mexc = ccxt.mexc({'apiKey': st.secrets["MEXC_KEY"], 'secret': st.secrets["MEXC_SEC"]})
    
    watchlist = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]
    results = []

    if st.button("RUN SCANNER", use_container_width=True):
        for symbol in watchlist:
            # Check 15m Bias
            df_15 = get_data(gate, symbol, '15m')
            if df_15 is None: continue
            
            for tf in ['3m', '5m']:
                df_ex = get_data(gate, symbol, tf)
                if df_ex is None: continue
                
                dir, conv, reason = check_expansion(df_ex, df_15)
                results.append({"Symbol": symbol, "Timeframe": tf, "Direction": dir, "Conviction": conv, "Reason": reason})
            time.sleep(0.2)
        
        st.table(pd.DataFrame(results))

if __name__ == "__main__":
    main()

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide", page_title="Backtest Results")
st.title("📊 Investment Strategy Backtester")

# Sidebar Configuration
st.sidebar.header("Strategy Settings")
ticker = st.sidebar.text_input("Ticker", "^GSPC")
col_a, col_b = st.sidebar.columns(2)
with col_a:
    dip_threshold = st.sidebar.slider("Initial Dip (%)", 1, 20, 5) / 100
    sub_dip = st.sidebar.slider("Subsequent Dip (%)", 1, 10, 2) / 100
with col_b:
    inv_amt = st.sidebar.number_input("Initial Buy ($)", value=1000)
    sub_inv = st.sidebar.number_input("Subsequent Buy ($)", value=2000)
sip_amt = st.sidebar.number_input("Monthly SIP ($)", value=500)

if st.sidebar.button("Run Analysis"):
    @st.cache_data
    def fetch_data(t):
        d = yf.download(t, start='2020-05-01', end='2026-05-01', auto_adjust=True, progress=False)
        return d['Close'].iloc[:, 0].to_frame('Close') if isinstance(d.columns, pd.MultiIndex) else d[['Close']]

    df = fetch_data(ticker)
    rolling_high = df['Close'].cummax()
    dd = (df['Close'] - rolling_high) / rolling_high

    # Logic
    inv_t, sh_p = [], []
    last_p, triggered = None, False
    for p, d in zip(df['Close'], dd):
        i, s = 0, 0
        if d == 0: triggered, last_p = False, None
        if not triggered and d <= -dip_threshold:
            triggered, last_p = True, p
            i, s = inv_amt, inv_amt / p
        elif triggered and last_p and p <= last_p * (1 - sub_dip):
            last_p, i, s = p, sub_inv, sub_inv / p
        inv_t.append(i); sh_p.append(s)

    df['Btd_Amt'], df['Btd_Shares'] = inv_t, sh_p
    df['Btd_Total_Inv'], df['Btd_Total_Sh'] = df['Btd_Amt'].cumsum(), df['Btd_Shares'].cumsum()
    df['Btd_Val'] = df['Btd_Total_Sh'] * df['Close']
    
    # SIP
    df['Sip_Amt'] = np.where(df.index.to_period('M') != df.index.to_period('M').shift(1), sip_amt, 0.0)
    df['Sip_Total_Inv'], df['Sip_Total_Sh'] = df['Sip_Amt'].cumsum(), (df['Sip_Amt'] / df['Close']).cumsum()
    df['Sip_Val'] = df['Sip_Total_Sh'] * df['Close']

    # Metrics
    def get_stats(cash, shares, val, start, end):
        p, c = val - cash, (pd.to_datetime(end) - pd.to_datetime(start)).days / 365.25
        return cash, val, p, (p/cash)*100 if cash>0 else 0, ((val/cash)**(1/c)-1)*100 if c>0 and cash>0 else 0

    btd_s = get_stats(df['Btd_Total_Inv'].iloc[-1], df['Btd_Total_Sh'].iloc[-1], df['Btd_Val'].iloc[-1], df.index[0], df.index[-1])
    sip_s = get_stats(df['Sip_Total_Inv'].iloc[-1], df['Sip_Total_Sh'].iloc[-1], df['Sip_Val'].iloc[-1], df.index[0], df.index[-1])

    # Aesthetic Layout
    cols = st.columns(2)
    for i, title, stats, trades in [(0, "Buy The Dip", btd_s, (df['Btd_Amt']>0).sum()), (1, "Monthly SIP", sip_s, (df['Sip_Amt']>0).sum())]:
        with cols[i]:
            st.subheader(f"🛡️ {title}")
            st.metric("Total Cash Deployed", f"${stats[0]:,.2f}")
            st.metric("Final Value", f"${stats[1]:,.2f}")
            st.metric("Net Profit", f"${stats[2]:,.2f}")
            st.metric("Strategy Return", f"{stats[3]:.2f}%")
            st.metric("CAGR", f"{stats[4]:.2f}%")
            st.write(f"**Total Trades:** {trades}")

    # Matching your Original Chart Style
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(df.index, df['Close'], color='royalblue', alpha=0.4, label='Close Price')
    
    init = df[df['Btd_Amt'] == inv_amt]
    subs = df[df['Btd_Amt'] == sub_inv]
    sip = df[df['Sip_Amt'] > 0]
    
    ax.scatter(init.index, init['Close'], color='forestgreen', marker='^', s=130, label='BTD Initial')
    ax.scatter(subs.index, subs['Close'], color='crimson', marker='^', s=80, label='BTD Subsequent')
    ax.scatter(sip.index, sip['Close'], color='orange', marker='o', s=20, alpha=0.6, label='SIP')
    
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.legend(loc='upper left')
    st.pyplot(fig)

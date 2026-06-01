import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("📈 Investment Strategy Backtester")

# Sidebar Inputs
st.sidebar.header("Configuration")
ticker = st.sidebar.text_input("Ticker Symbol", "^GSPC")
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2020-05-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("2026-05-01"))

dip_threshold = st.sidebar.slider("Initial Dip Threshold (%)", 1, 20, 5) / 100
investment_amount = st.sidebar.number_input("Initial Buy Amount ($)", 1000)
subsequent_dip_threshold = st.sidebar.slider("Subsequent Dip Threshold (%)", 1, 10, 2) / 100
subsequent_investment_amount = st.sidebar.number_input("Subsequent Buy Amount ($)", 2000)
manual_sip_amount = st.sidebar.number_input("Monthly SIP Amount ($)", 500)

# Add a run button to trigger calculations
if st.sidebar.button("Run Backtest"):
    @st.cache_data
    def load_data(ticker, start, end):
        data = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
        return data

    raw_data = load_data(ticker, start_date, end_date)

    if raw_data.empty:
        st.error("No data found! Please check your ticker or date range.")
    else:
        # Data Cleaning
        if isinstance(raw_data.columns, pd.MultiIndex):
            df = raw_data['Close'].iloc[:, 0].to_frame(name='Close')
        else:
            df = raw_data[['Close']].copy()

        # ... (Rest of your original logic) ...
        rolling_high = df['Close'].cummax()
        market_drawdown = (df['Close'] - rolling_high) / rolling_high

        # BTD Logic
        inv_list, share_list = [], []
        last_buy_price, triggered = None, False
        for price, dd in zip(df['Close'], market_drawdown):
            inv, sh = 0, 0
            if dd == 0: triggered, last_buy_price = False, None
            if not triggered and dd <= -dip_threshold:
                triggered, last_buy_price = True, price
                inv, sh = investment_amount, investment_amount / price
            elif triggered and last_buy_price and price <= last_buy_price * (1 - subsequent_dip_threshold):
                last_buy_price, inv, sh = price, subsequent_investment_amount, subsequent_investment_amount / price
            inv_list.append(inv); share_list.append(sh)

        df['Btd_Invested_Amt'], df['Btd_Shares_Bought'] = inv_list, share_list
        df['Btd_Total_Invested'], df['Btd_Total_Shares'] = df['Btd_Invested_Amt'].cumsum(), df['Btd_Shares_Bought'].cumsum()
        df['Btd_Portfolio_Value'] = df['Btd_Total_Shares'] * df['Close']

        # SIP Logic
        df['Year_Month'] = df.index.to_period('M')
        is_first = df['Year_Month'] != df['Year_Month'].shift(1)
        df['Sip_Invested_Amt'] = np.where(is_first, manual_sip_amount, 0.0)
        df['Sip_Total_Invested'], df['Sip_Total_Shares'] = df['Sip_Invested_Amt'].cumsum(), (df['Sip_Invested_Amt'] / df['Close']).cumsum()
        df['Sip_Portfolio_Value'] = df['Sip_Total_Shares'] * df['Close']

        # Safe Metrics Extraction
        idx = -1
        btd_inv = df['Btd_Total_Invested'].iloc[idx]
        btd_val = df['Btd_Portfolio_Value'].iloc[idx]
        sip_inv = df['Sip_Total_Invested'].iloc[idx]
        sip_val = df['Sip_Portfolio_Value'].iloc[idx]

        # UI Display
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Buy The Dip")
            st.metric("Total Invested", f"${btd_inv:,.2f}")
            st.metric("Final Value", f"${btd_val:,.2f}")
        with col2:
            st.subheader("Monthly SIP")
            st.metric("Total Invested", f"${sip_inv:,.2f}")
            st.metric("Final Value", f"${sip_val:,.2f}")

        # Plotting
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df.index, df['Close'], label='Price', alpha=0.3)
        st.pyplot(fig)
else:
    st.info("Adjust settings in the sidebar and click 'Run Backtest' to begin.")

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Strategy Backtester", layout="wide")
st.title("📈 Hybrid Strategy Backtester")

# ==========================================
# SIDEBAR INPUTS
# ==========================================
with st.sidebar:
    st.header("Configuration")
    with st.form("inputs_form"):
        ticker = st.text_input("Ticker Symbol", "TQQQ")
        start_date = st.date_input("Start Date", pd.to_datetime("2020-01-01"))
        end_date = st.date_input("End Date", pd.to_datetime("2026-06-01"))
        
        st.divider()
        st.subheader("Strategy Parameters")
        # Changed to number inputs as requested
        dip_pct = st.number_input("Initial Dip Threshold (%)", value=5.0)
        sub_dip_pct = st.number_input("Subsequent Dip Threshold (%)", value=2.5)
        
        investment_amount = st.number_input("Initial BTD Investment ($)", value=1000)
        subsequent_investment_amount = st.number_input("Subsequent BTD Investment ($)", value=2000)
        manual_sip_amount = st.number_input("Monthly SIP Amount ($)", value=500)
        
        run_btn = st.form_submit_button("Run Backtest")

# Convert % inputs to decimals
dip_threshold = dip_pct / 100
subsequent_dip_threshold = sub_dip_pct / 100

# ==========================================
# EXECUTION LOGIC
# ==========================================
if run_btn:
    # 1. Download Data
    data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=True, progress=False)
    if data.empty:
        st.error("No data found for this ticker/date range.")
        st.stop()
        
    df = data[['Close']].copy() if not isinstance(data.columns, pd.MultiIndex) else data['Close'].iloc[:, 0].to_frame(name='Close')

    # 2. Strategy Calculation
    rolling_high = df['Close'].cummax()
    market_drawdown = (df['Close'] - rolling_high) / rolling_high

    investment_triggers = []
    shares_purchased = []
    last_buy_price = None
    has_triggered_initial_dip = False

    for price, dd in zip(df['Close'], market_drawdown):
        current_investment = 0
        shares = 0
        if dd == 0:
            has_triggered_initial_dip = False
            last_buy_price = None
        if not has_triggered_initial_dip and dd <= -dip_threshold:
            has_triggered_initial_dip = True
            last_buy_price = price
            current_investment = investment_amount
            shares = current_investment / price
        elif has_triggered_initial_dip and last_buy_price is not None:
            if price <= last_buy_price * (1 - subsequent_dip_threshold):
                last_buy_price = price
                current_investment = subsequent_investment_amount
                shares = current_investment / price
        investment_triggers.append(current_investment)
        shares_purchased.append(shares)

    df['Btd_Invested_Amt'] = investment_triggers
    df['Btd_Shares_Bought'] = shares_purchased
    df['Btd_Total_Shares'] = df['Btd_Shares_Bought'].cumsum()
    df['Btd_Portfolio_Value'] = df['Btd_Total_Shares'] * df['Close']

    # SIP
    df['Year_Month'] = df.index.to_period('M')
    is_first_day_of_month = df['Year_Month'] != df['Year_Month'].shift(1)
    df['Sip_Invested_Amt'] = np.where(is_first_day_of_month, manual_sip_amount, 0.0)
    df['Sip_Shares_Bought'] = df['Sip_Invested_Amt'] / df['Close']
    df['Sip_Total_Shares'] = df['Sip_Shares_Bought'].cumsum()
    
    # 3. Visualization
    st.subheader("Performance Chart")
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(df.index, df['Close'], label='Close Price', color='royalblue', linewidth=1.5, alpha=0.4)

    # Filter buy points
    initial_buys = df[df['Btd_Invested_Amt'] == investment_amount]
    subsequent_buys = df[df['Btd_Invested_Amt'] == subsequent_investment_amount]
    sip_buys = df[df['Sip_Invested_Amt'] > 0]

    # Plot Scatter
    ax.scatter(initial_buys.index, initial_buys['Close'], color='forestgreen', marker='^', s=100, label='BTD Initial Trigger', zorder=5)
    ax.scatter(subsequent_buys.index, subsequent_buys['Close'], color='crimson', marker='^', s=60, label='BTD Subsequent', zorder=4)
    ax.scatter(sip_buys.index, sip_buys['Close'], color='orange', marker='o', s=10, alpha=0.5, label='Monthly SIP', zorder=3)

    ax.set_title(f'Buy Points for {ticker}')
    ax.legend()
    st.pyplot(fig)

    # 4. Metrics
    col1, col2 = st.columns(2)
    final_val = (df['Btd_Total_Shares'].iloc[-1] + df['Sip_Total_Shares'].iloc[-1]) * df['Close'].iloc[-1]
    total_cash = df['Btd_Invested_Amt'].sum() + df['Sip_Invested_Amt'].sum()
    
    with col1:
        st.metric("Total Deployed", f"${total_cash:,.2f}")
    with col2:
        st.metric("Final Value", f"${final_val:,.2f}", f"{((final_val/total_cash)-1)*100:.2f}%")

else:
    st.info("Adjust parameters in the sidebar and click 'Run Backtest' to see results.")

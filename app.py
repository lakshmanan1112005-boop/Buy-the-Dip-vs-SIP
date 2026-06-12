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
        dip_pct = st.number_input("Initial Dip Threshold (%)", value=5.0)
        sub_dip_pct = st.number_input("Subsequent Dip Threshold (%)", value=2.5)
        
        investment_amount = st.number_input("Initial BTD Investment ($)", value=1000)
        subsequent_investment_amount = st.number_input("Subsequent BTD Investment ($)", value=2000)
        manual_sip_amount = st.number_input("Monthly SIP Amount ($)", value=500)
        
        run_btn = st.form_submit_button("Run Backtest")

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def calculate_cagr(final_val, total_invested, start, end):
    years = (pd.to_datetime(end) - pd.to_datetime(start)).days / 365.25
    if years <= 0 or total_invested <= 0: return 0.0
    return (((final_val / total_invested) ** (1/years)) - 1) * 100

# ==========================================
# EXECUTION LOGIC
# ==========================================
if run_btn:
    data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=True, progress=False)
    if data.empty:
        st.error("No data found for this ticker/date range.")
        st.stop()
        
    df = data[['Close']].copy() if not isinstance(data.columns, pd.MultiIndex) else data['Close'].iloc[:, 0].to_frame(name='Close')

    # Strategy Calculation
    rolling_high = df['Close'].cummax()
    market_drawdown = (df['Close'] - rolling_high) / rolling_high

    # Initialize columns
    df['Btd_Invested_Amt'] = 0.0
    df['Btd_Shares_Bought'] = 0.0
    df['Sip_Invested_Amt'] = 0.0
    df['Sip_Shares_Bought'] = 0.0

    # BTD Logic
    last_buy_price = None
    has_triggered_initial_dip = False
    for i in range(len(df)):
        price = df['Close'].iloc[i]
        dd = market_drawdown.iloc[i]
        
        if dd == 0:
            has_triggered_initial_dip = False
            last_buy_price = None
        
        if not has_triggered_initial_dip and dd <= -(dip_pct/100):
            has_triggered_initial_dip = True
            last_buy_price = price
            df.iloc[i, df.columns.get_loc('Btd_Invested_Amt')] = investment_amount
            df.iloc[i, df.columns.get_loc('Btd_Shares_Bought')] = investment_amount / price
        elif has_triggered_initial_dip and last_buy_price is not None:
            if price <= last_buy_price * (1 - (sub_dip_pct/100)):
                last_buy_price = price
                df.iloc[i, df.columns.get_loc('Btd_Invested_Amt')] = subsequent_investment_amount
                df.iloc[i, df.columns.get_loc('Btd_Shares_Bought')] = subsequent_investment_amount / price

    # SIP Logic
    df['Year_Month'] = df.index.to_period('M')
    is_first_day_of_month = df['Year_Month'] != df['Year_Month'].shift(1)
    df.loc[is_first_day_of_month, 'Sip_Invested_Amt'] = manual_sip_amount
    df['Sip_Shares_Bought'] = df['Sip_Invested_Amt'] / df['Close']

    # Aggregation
    df['Hybrid_Invested_Amt'] = df['Btd_Invested_Amt'] + df['Sip_Invested_Amt']
    df['Hybrid_Total_Shares'] = df['Btd_Shares_Bought'].cumsum() + df['Sip_Shares_Bought'].cumsum()
    df['Hybrid_Total_Cash'] = df['Hybrid_Invested_Amt'].cumsum()
    df['Hybrid_Portfolio_Value'] = df['Hybrid_Total_Shares'] * df['Close']

    # Performance Metrics
    final_val = df['Hybrid_Portfolio_Value'].iloc[-1]
    total_cash = df['Hybrid_Total_Cash'].iloc[-1]
    profit = final_val - total_cash
    strategy_return = (profit / total_cash) * 100 if total_cash > 0 else 0
    
    # Drawdown
    hybrid_rolling_high = df['Hybrid_Portfolio_Value'].cummax()
    hybrid_dd = (df['Hybrid_Portfolio_Value'] - hybrid_rolling_high) / hybrid_rolling_high
    max_dd = hybrid_dd.min() * 100
    
    trades = len(df[df['Hybrid_Invested_Amt'] > 0])
    avg_entry = total_cash / df['Hybrid_Total_Shares'].iloc[-1] if df['Hybrid_Total_Shares'].iloc[-1] > 0 else 0
    cagr = calculate_cagr(final_val, total_cash, start_date, end_date)

    # 1. Visualization
    st.subheader("Performance Chart")
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df.index, df['Close'], label='Close Price', color='royalblue', alpha=0.3)
    
    initial_buys = df[df['Btd_Invested_Amt'] == investment_amount]
    subsequent_buys = df[df['Btd_Invested_Amt'] == subsequent_investment_amount]
    sip_buys = df[df['Sip_Invested_Amt'] > 0]
    
    ax.scatter(initial_buys.index, initial_buys['Close'], color='green', marker='^', s=80, label='BTD Initial')
    ax.scatter(subsequent_buys.index, subsequent_buys['Close'], color='red', marker='^', s=40, label='BTD Subsequent')
    ax.scatter(sip_buys.index, sip_buys['Close'], color='orange', marker='o', s=10, alpha=0.5, label='SIP')
    
    ax.legend()
    st.pyplot(fig)

    # 2. Metrics Table
    st.subheader("Strategy Performance Summary")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Total Cash Deployed:** ${total_cash:,.2f}")
        st.write(f"**Final Portfolio Value:** ${final_val:,.2f}")
        st.write(f"**Net Profit/Loss:** ${profit:,.2f}")
        st.write(f"**Strategy Return:** {strategy_return:.2f}%")
        
    with col2:
        st.write(f"**Max Strategy Drawdown:** {max_dd:.2f}%")
        st.write(f"**Total Number of Trades:** {trades}")
        st.write(f"**Average Entry Price:** ${avg_entry:,.2f}")
        st.write(f"**Strategy CAGR:** {cagr:.2f}%")

else:
    st.info("Adjust parameters in the sidebar and click 'Run Backtest' to see results.")

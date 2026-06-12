import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# PAGE SETUP
# ==========================================
st.set_page_config(page_title="Strategy Backtester", layout="wide")
st.title("📈 Hybrid Strategy Backtester (SIP + BTD)")

# ==========================================
# SIDEBAR CONFIGURATION
# ==========================================
with st.sidebar:
    st.header("Configuration")
    ticker = st.text_input("Ticker Symbol", "TQQQ")
    start_date = st.date_input("Start Date", pd.to_datetime("2020-01-01"))
    end_date = st.date_input("End Date", pd.to_datetime("2026-06-01"))
    
    st.divider()
    dip_threshold = st.slider("Dip Threshold (%)", 0.01, 0.20, 0.05, 0.01)
    subsequent_dip_threshold = st.slider("Subsequent Dip Threshold (%)", 0.01, 0.10, 0.025, 0.005)
    
    investment_amount = st.number_input("Initial BTD Investment ($)", 1000)
    subsequent_investment_amount = st.number_input("Subsequent BTD Investment ($)", 2000)
    manual_sip_amount = st.number_input("Monthly SIP Amount ($)", 500)

# ==========================================
# DATA PROCESSING (Cached for speed)
# ==========================================
@st.cache_data
def get_data(ticker, start, end):
    data = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        df = data['Close'].iloc[:, 0].to_frame(name='Close')
    else:
        df = data[['Close']].copy()
    return df

df = get_data(ticker, start_date, end_date)

# Logic for Strategy
rolling_high = df['Close'].cummax()
market_drawdown = (df['Close'] - rolling_high) / rolling_high

# (Your core logic remains the same)
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
df['Btd_Total_Invested'] = df['Btd_Invested_Amt'].cumsum()
df['Btd_Total_Shares'] = df['Btd_Shares_Bought'].cumsum()
df['Btd_Portfolio_Value'] = df['Btd_Total_Shares'] * df['Close']

# SIP
df['Year_Month'] = df.index.to_period('M')
is_first_day_of_month = df['Year_Month'] != df['Year_Month'].shift(1)
df['Sip_Invested_Amt'] = np.where(is_first_day_of_month, manual_sip_amount, 0.0)
df['Sip_Shares_Bought'] = df['Sip_Invested_Amt'] / df['Close']
df['Sip_Total_Invested'] = df['Sip_Invested_Amt'].cumsum()
df['Sip_Total_Shares'] = df['Sip_Shares_Bought'].cumsum()
df['Sip_Portfolio_Value'] = df['Sip_Total_Shares'] * df['Close']

# Hybrid
df['Hybrid_Total_Invested'] = df['Btd_Total_Invested'] + df['Sip_Total_Invested']
df['Hybrid_Total_Shares'] = df['Btd_Total_Shares'] + df['Sip_Total_Shares']
df['Hybrid_Portfolio_Value'] = df['Hybrid_Total_Shares'] * df['Close']

# ==========================================
# DASHBOARD DISPLAY
# ==========================================
def calculate_cagr(final_val, total_invested, start, end):
    years = (pd.to_datetime(end) - pd.to_datetime(start)).days / 365.25
    if years <= 0 or total_invested <= 0: return 0.0
    return (((final_val / total_invested) ** (1/years)) - 1) * 100

def show_metric(label, cash, value):
    profit = value - cash
    return_pct = (profit / cash) * 100 if cash > 0 else 0
    st.metric(label, f"${value:,.2f}", f"{return_pct:.2f}% return")

col1, col2, col3 = st.columns(3)
with col1: show_metric("BTD Portfolio", df['Btd_Total_Invested'].iloc[-1], df['Btd_Portfolio_Value'].iloc[-1])
with col2: show_metric("SIP Portfolio", df['Sip_Total_Invested'].iloc[-1], df['Sip_Portfolio_Value'].iloc[-1])
with col3: show_metric("Hybrid Portfolio", df['Hybrid_Total_Invested'].iloc[-1], df['Hybrid_Portfolio_Value'].iloc[-1])

# Plotting
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(df.index, df['Close'], label='Close Price', color='royalblue', alpha=0.3)
ax.plot(df.index, (df['Btd_Portfolio_Value'] / df['Btd_Total_Shares'].replace(0, np.nan)), label='BTD Equity Curve', color='green')
plt.legend()
st.pyplot(fig)

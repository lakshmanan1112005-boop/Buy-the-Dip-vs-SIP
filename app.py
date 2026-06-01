import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
# Force non-interactive backend to ensure the script saves the plot reliably
matplotlib.use('Agg')
import matplotlib.pyplot as plt

class StrategyBacktester:
    def __init__(self, ticker, start_date, end_date):
        self.ticker = ticker
        self.start_date = start_date
        self.end_date = end_date
        self.df = self._download_data()

    def _download_data(self):
        data = yf.download(self.ticker, start=self.start_date, end=self.end_date, auto_adjust=True, progress=False)
        df = data['Close'].iloc[:, 0].to_frame(name='Close') if isinstance(data.columns, pd.MultiIndex) else data[['Close']].copy()
        rolling_high = df['Close'].cummax()
        df['Market_Drawdown'] = (df['Close'] - rolling_high) / rolling_high
        return df

    def calculate_cagr(self, final_val, total_invested):
        years = (pd.to_datetime(self.end_date) - pd.to_datetime(self.start_date)).days / 365.25
        if years <= 0 or total_invested <= 0: return 0.0
        base = final_val / total_invested
        return ((base ** (1/years)) - 1) * 100 if base >= 0 else -100

    def run_btd(self, dip_threshold, investment_amount, sub_dip_threshold, sub_investment_amount):
        investment_triggers, shares_purchased = [], []
        last_buy_price, has_triggered = None, False

        for price, dd in zip(self.df['Close'], self.df['Market_Drawdown']):
            cur_inv, shares = 0, 0
            if dd == 0: has_triggered, last_buy_price = False, None
            if not has_triggered and dd <= -dip_threshold:
                has_triggered, last_buy_price = True, price
                cur_inv, shares = investment_amount, investment_amount / price
            elif has_triggered and last_buy_price and price <= last_buy_price * (1 - sub_dip_threshold):
                last_buy_price = price
                cur_inv, shares = sub_investment_amount, sub_investment_amount / price
            investment_triggers.append(cur_inv)
            shares_purchased.append(shares)

        self.df['Btd_Invested_Amt'] = investment_triggers
        self.df['Btd_Total_Invested'] = self.df['Btd_Invested_Amt'].cumsum()
        self.df['Btd_Total_Shares'] = np.array(shares_purchased).cumsum()
        self.df['Btd_Portfolio_Value'] = self.df['Btd_Total_Shares'] * self.df['Close']
        
        # Drawdown calculation
        btd_started = self.df['Btd_Total_Invested'] > 0
        rolling = self.df.loc[btd_started, 'Btd_Portfolio_Value'].cummax()
        self.btd_max_dd = ((self.df.loc[btd_started, 'Btd_Portfolio_Value'] - rolling) / rolling).min() * 100

    def run_sip(self, monthly_budget):
        self.df['Year_Month'] = self.df.index.to_period('M')
        is_first = self.df['Year_Month'] != self.df['Year_Month'].shift(1)
        self.df['Sip_Invested_Amt'] = np.where(is_first, monthly_budget, 0.0)
        self.df['Sip_Total_Invested'] = self.df['Sip_Invested_Amt'].cumsum()
        self.df['Sip_Total_Shares'] = (self.df['Sip_Invested_Amt'] / self.df['Close']).cumsum()
        self.df['Sip_Portfolio_Value'] = self.df['Sip_Total_Shares'] * self.df['Close']
        
        sip_started = self.df['Sip_Total_Invested'] > 0
        rolling = self.df.loc[sip_started, 'Sip_Portfolio_Value'].cummax()
        self.sip_max_dd = ((self.df.loc[sip_started, 'Sip_Portfolio_Value'] - rolling) / rolling).min() * 100

    def print_summary(self, name, cash, final_val, total_shares, max_dd):
        profit = final_val - cash
        ret = (profit / cash) * 100 if cash > 0 else 0
        cagr = self.calculate_cagr(final_val, cash)
        print(f"--- {name} ---")
        print(f"Cash Deployed: ${cash:,.2f} | Final Value: ${final_val:,.2f}")
        print(f"Return: {ret:.2f}% | Max DD: {max_dd:.2f}% | CAGR: {cagr:.2f}%")
        print("="*40)

# --- Execution ---
bt = StrategyBacktester('^GSPC', '2020-05-01', '2026-05-01')
bt.run_btd(0.05, 1000, 0.025, 2000)
bt.run_sip(500)

bt.print_summary("BUY THE DIP", bt.df['Btd_Total_Invested'].iloc[-1], bt.df['Btd_Portfolio_Value'].iloc[-1], bt.df['Btd_Total_Shares'].iloc[-1], bt.btd_max_dd)
bt.print_summary("MONTHLY SIP", bt.df['Sip_Total_Invested'].iloc[-1], bt.df['Sip_Portfolio_Value'].iloc[-1], bt.df['Sip_Total_Shares'].iloc[-1], bt.sip_max_dd)

plt.figure(figsize=(12, 6))
plt.plot(bt.df.index, bt.df['Close'], label='S&P 500', alpha=0.3)
plt.scatter(bt.df[bt.df['Btd_Invested_Amt']>0].index, bt.df.loc[bt.df['Btd_Invested_Amt']>0, 'Close'], color='green', label='BTD Buy', s=10)
plt.legend()
plt.savefig('strategy_result.png')
print("Backtest complete. Chart saved as 'strategy_result.png'.")

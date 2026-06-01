import { useState, useRef, useEffect } from "react";

const COLORS = {
  bg: "#0d1117",
  surface: "#161b22",
  border: "#30363d",
  borderLight: "#21262d",
  text: "#e6edf3",
  textMuted: "#7d8590",
  textFaint: "#484f58",
  green: "#3fb950",
  red: "#f85149",
  blue: "#58a6ff",
  orange: "#d29922",
  purple: "#bc8cff",
  btdLine: "#3fb950",
  sipLine: "#58a6ff",
  priceLine: "#484f58",
  initialBuy: "#3fb950",
  subBuy: "#f85149",
  sipDot: "#d29922",
};

const CHART_COLORS = {
  btd: "#3fb950",
  sip: "#58a6ff",
  price: "#58a6ff",
  grid: "#21262d",
  axis: "#484f58",
};

const DEFAULT_CONFIG = {
  ticker: "^GSPC",
  start_date: "2020-05-01",
  end_date: "2026-05-01",
  dip_threshold: 0.05,
  investment_amount: 1000,
  subsequent_dip_threshold: 0.025,
  subsequent_investment_amount: 2000,
  manual_sip_amount: 500,
};

function buildPrompt(cfg) {
  return `You are a financial backtesting engine. Given the config below, simulate the two strategies and return ONLY a valid JSON object (no markdown, no explanation).

Config:
- Ticker: ${cfg.ticker} (assume S&P 500 index data)
- Period: ${cfg.start_date} to ${cfg.end_date}
- BTD initial dip threshold: ${cfg.dip_threshold * 100}%
- BTD initial investment: $${cfg.investment_amount}
- BTD subsequent dip threshold: ${cfg.subsequent_dip_threshold * 100}%
- BTD subsequent investment: $${cfg.subsequent_investment_amount}
- Monthly SIP amount: $${cfg.manual_sip_amount}

Simulate using realistic S&P 500 price history. Compute all metrics accurately.

Return JSON with this exact structure:
{
  "btd": {
    "total_invested": <number>,
    "final_value": <number>,
    "net_profit": <number>,
    "return_pct": <number>,
    "max_drawdown_pct": <number>,
    "num_trades": <integer>,
    "avg_entry_price": <number>,
    "cagr_pct": <number>,
    "trades": [
      { "date": "YYYY-MM-DD", "price": <number>, "type": "initial"|"subsequent", "amount": <number> }
    ]
  },
  "sip": {
    "total_invested": <number>,
    "final_value": <number>,
    "net_profit": <number>,
    "return_pct": <number>,
    "max_drawdown_pct": <number>,
    "avg_entry_price": <number>,
    "cagr_pct": <number>,
    "monthly_amount": <number>
  },
  "benchmark": {
    "max_drawdown_pct": <number>,
    "ticker": "${cfg.ticker}"
  },
  "price_series": [
    { "date": "YYYY-MM-DD", "close": <number> }
  ],
  "portfolio_series": [
    { "date": "YYYY-MM-DD", "btd_value": <number>, "sip_value": <number> }
  ]
}

Use realistic monthly price_series (first trading day of each month) from ${cfg.start_date} to ${cfg.end_date} — about 72 data points. portfolio_series should also be monthly. Ensure all numbers are realistic and consistent with actual S&P 500 history.`;
}

function MetricCard({ label, value, sub, color }) {
  return (
    <div style={{
      background: COLORS.surface,
      border: `1px solid ${COLORS.border}`,
      borderRadius: 6,
      padding: "12px 16px",
    }}>
      <div style={{ fontSize: 11, color: COLORS.textMuted, marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.06em", fontFamily: "monospace" }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 600, color: color || COLORS.text, fontFamily: "monospace" }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: COLORS.textFaint, marginTop: 2, fontFamily: "monospace" }}>{sub}</div>}
    </div>
  );
}

function SectionHeader({ icon, title }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
      <span style={{ fontSize: 13, color: COLORS.textMuted }}>{icon}</span>
      <span style={{ fontSize: 13, fontWeight: 600, color: COLORS.textMuted, textTransform: "uppercase", letterSpacing: "0.08em", fontFamily: "monospace" }}>{title}</span>
    </div>
  );
}

function Divider() {
  return <div style={{ borderTop: `1px solid ${COLORS.borderLight}`, margin: "20px 0" }} />;
}

function InputField({ label, value, onChange, type = "text", step, min, max }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <label style={{ fontSize: 11, color: COLORS.textMuted, fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        step={step}
        min={min}
        max={max}
        style={{
          background: COLORS.bg,
          border: `1px solid ${COLORS.border}`,
          borderRadius: 6,
          padding: "6px 10px",
          color: COLORS.text,
          fontSize: 13,
          fontFamily: "monospace",
          outline: "none",
          width: "100%",
          boxSizing: "border-box",
        }}
      />
    </div>
  );
}

function LineChart({ series, trades, width = 680, height = 280 }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!series || series.length === 0) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    ctx.scale(dpr, dpr);

    const pad = { top: 20, right: 20, bottom: 40, left: 65 };
    const W = width - pad.left - pad.right;
    const H = height - pad.top - pad.bottom;

    ctx.clearRect(0, 0, width, height);

    const closes = series.map(d => d.close);
    const minP = Math.min(...closes) * 0.97;
    const maxP = Math.max(...closes) * 1.03;
    const n = series.length;

    const xScale = i => pad.left + (i / (n - 1)) * W;
    const yScale = v => pad.top + H - ((v - minP) / (maxP - minP)) * H;

    const gridCount = 5;
    for (let i = 0; i <= gridCount; i++) {
      const y = pad.top + (i / gridCount) * H;
      const val = maxP - (i / gridCount) * (maxP - minP);
      ctx.strokeStyle = CHART_COLORS.grid;
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(pad.left + W, y);
      ctx.stroke();
      ctx.fillStyle = COLORS.textFaint;
      ctx.font = "10px monospace";
      ctx.textAlign = "right";
      ctx.fillText("$" + Math.round(val).toLocaleString(), pad.left - 8, y + 3.5);
    }

    const step = Math.max(1, Math.floor(n / 8));
    for (let i = 0; i < n; i += step) {
      const x = xScale(i);
      const dateStr = series[i].date.slice(0, 7);
      ctx.fillStyle = COLORS.textFaint;
      ctx.font = "10px monospace";
      ctx.textAlign = "center";
      ctx.fillText(dateStr, x, pad.top + H + 20);
    }

    ctx.beginPath();
    ctx.strokeStyle = CHART_COLORS.price + "55";
    ctx.lineWidth = 1.5;
    series.forEach((d, i) => {
      const x = xScale(i);
      const y = yScale(d.close);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();

    if (trades) {
      const dateToIdx = {};
      series.forEach((d, i) => { dateToIdx[d.date] = i; });

      trades.forEach(t => {
        const idx = dateToIdx[t.date];
        if (idx === undefined) return;
        const x = xScale(idx);
        const y = yScale(t.price);
        const isInitial = t.type === "initial";
        ctx.beginPath();
        if (isInitial) {
          ctx.moveTo(x, y - 8);
          ctx.lineTo(x + 6, y + 4);
          ctx.lineTo(x - 6, y + 4);
          ctx.closePath();
          ctx.fillStyle = COLORS.initialBuy;
        } else {
          ctx.moveTo(x, y - 6);
          ctx.lineTo(x + 5, y + 3);
          ctx.lineTo(x - 5, y + 3);
          ctx.closePath();
          ctx.fillStyle = COLORS.subBuy;
        }
        ctx.fill();
      });

      series.forEach((d, i) => {
        const x = xScale(i);
        const y = yScale(d.close);
        ctx.beginPath();
        ctx.arc(x, y, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = COLORS.sipDot + "99";
        ctx.fill();
      });
    }

    ctx.strokeStyle = CHART_COLORS.axis;
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    ctx.moveTo(pad.left, pad.top);
    ctx.lineTo(pad.left, pad.top + H);
    ctx.lineTo(pad.left + W, pad.top + H);
    ctx.stroke();

  }, [series, trades, width, height]);

  return <canvas ref={canvasRef} style={{ display: "block" }} />;
}

function PortfolioChart({ portfolioSeries, width = 680, height = 220 }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!portfolioSeries || portfolioSeries.length === 0) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    ctx.scale(dpr, dpr);

    const pad = { top: 20, right: 20, bottom: 40, left: 75 };
    const W = width - pad.left - pad.right;
    const H = height - pad.top - pad.bottom;

    ctx.clearRect(0, 0, width, height);

    const allVals = portfolioSeries.flatMap(d => [d.btd_value, d.sip_value]).filter(v => v > 0);
    if (allVals.length === 0) return;
    const maxV = Math.max(...allVals) * 1.08;
    const n = portfolioSeries.length;

    const xScale = i => pad.left + (i / (n - 1)) * W;
    const yScale = v => pad.top + H - (v / maxV) * H;

    for (let i = 0; i <= 4; i++) {
      const y = pad.top + (i / 4) * H;
      const val = maxV - (i / 4) * maxV;
      ctx.strokeStyle = CHART_COLORS.grid;
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(pad.left + W, y);
      ctx.stroke();
      ctx.fillStyle = COLORS.textFaint;
      ctx.font = "10px monospace";
      ctx.textAlign = "right";
      ctx.fillText("$" + Math.round(val).toLocaleString(), pad.left - 8, y + 3.5);
    }

    const step = Math.max(1, Math.floor(n / 8));
    portfolioSeries.forEach((d, i) => {
      if (i % step !== 0) return;
      ctx.fillStyle = COLORS.textFaint;
      ctx.font = "10px monospace";
      ctx.textAlign = "center";
      ctx.fillText(d.date.slice(0, 7), xScale(i), pad.top + H + 20);
    });

    ctx.beginPath();
    ctx.strokeStyle = COLORS.btdLine;
    ctx.lineWidth = 2;
    portfolioSeries.forEach((d, i) => {
      const x = xScale(i);
      const y = yScale(d.btd_value || 0);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();

    ctx.beginPath();
    ctx.strokeStyle = COLORS.sipLine;
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 4]);
    portfolioSeries.forEach((d, i) => {
      const x = xScale(i);
      const y = yScale(d.sip_value || 0);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.strokeStyle = CHART_COLORS.axis;
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    ctx.moveTo(pad.left, pad.top);
    ctx.lineTo(pad.left, pad.top + H);
    ctx.lineTo(pad.left + W, pad.top + H);
    ctx.stroke();
  }, [portfolioSeries, width, height]);

  return <canvas ref={canvasRef} style={{ display: "block" }} />;
}

function fmt(n, decimals = 2) {
  if (n === undefined || n === null) return "—";
  return n.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}
function fmtPct(n) {
  if (n === undefined || n === null) return { val: "—", color: COLORS.textMuted };
  const color = n >= 0 ? COLORS.green : COLORS.red;
  return { val: (n >= 0 ? "+" : "") + fmt(n) + "%", color };
}
function fmtDollar(n) {
  if (n === undefined || n === null) return "—";
  return "$" + fmt(n);
}

export default function App() {
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [streamLog, setStreamLog] = useState("");

  const setField = (k) => (v) => setConfig(c => ({
    ...c,
    [k]: isNaN(parseFloat(v)) || (typeof v === "string" && v.includes("-") && k.includes("date")) ? v : parseFloat(v) || v
  }));

  const run = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setStreamLog("Initializing backtest engine...");

    try {
      const response = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 4000,
          messages: [{ role: "user", content: buildPrompt(config) }],
        }),
      });

      const data = await response.json();
      if (data.error) throw new Error(data.error.message);

      const raw = data.content.map(b => b.text || "").join("");
      setStreamLog("Parsing results...");

      const jsonMatch = raw.match(/\{[\s\S]*\}/);
      if (!jsonMatch) throw new Error("No JSON found in response");
      const parsed = JSON.parse(jsonMatch[0]);
      setResult(parsed);
      setStreamLog("");
    } catch (e) {
      setError(e.message);
      setStreamLog("");
    } finally {
      setLoading(false);
    }
  };

  const btd = result?.btd;
  const sip = result?.sip;

  return (
    <div style={{
      background: COLORS.bg,
      minHeight: "100vh",
      color: COLORS.text,
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', monospace",
      padding: "0 0 60px",
    }}>
      {/* Header */}
      <div style={{
        borderBottom: `1px solid ${COLORS.border}`,
        padding: "16px 24px",
        display: "flex",
        alignItems: "center",
        gap: 12,
        background: COLORS.surface,
      }}>
        <svg width="20" height="20" viewBox="0 0 16 16" fill={COLORS.textMuted}>
          <path d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 010-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8zM5 12.25v3.25a.25.25 0 00.4.2l1.45-1.087a.25.25 0 01.3 0L8.6 15.7a.25.25 0 00.4-.2v-3.25a.25.25 0 00-.25-.25h-3.5a.25.25 0 00-.25.25z" />
        </svg>
        <span style={{ fontSize: 14, fontWeight: 600, color: COLORS.text }}>strategy-backtest</span>
        <span style={{ fontSize: 12, color: COLORS.textMuted }}>/</span>
        <span style={{ fontSize: 14, color: COLORS.blue }}>btd_vs_sip.py</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <span style={{
            background: "#1f6feb33",
            border: "1px solid #1f6feb",
            borderRadius: 20,
            padding: "2px 10px",
            fontSize: 11,
            color: "#58a6ff",
            fontWeight: 500,
          }}>finance</span>
          <span style={{
            background: "#3fb95033",
            border: "1px solid #3fb950",
            borderRadius: 20,
            padding: "2px 10px",
            fontSize: 11,
            color: "#3fb950",
            fontWeight: 500,
          }}>backtesting</span>
        </div>
      </div>

      <div style={{ maxWidth: 860, margin: "0 auto", padding: "24px 24px 0" }}>

        {/* README */}
        <div style={{
          background: COLORS.surface,
          border: `1px solid ${COLORS.border}`,
          borderRadius: 6,
          padding: "16px 20px",
          marginBottom: 24,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill={COLORS.textMuted}>
              <path d="M0 1.75A.75.75 0 01.75 1h4.253c1.227 0 2.317.59 3 1.501A3.744 3.744 0 0111.006 1h4.245a.75.75 0 01.75.75v10.5a.75.75 0 01-.75.75h-4.507a2.25 2.25 0 00-1.591.659l-.622.621a.75.75 0 01-1.06 0l-.622-.621A2.25 2.25 0 005.258 13H.75a.75.75 0 01-.75-.75V1.75zm7.251 10.324l.004-5.073-.002-2.253A2.25 2.25 0 005.003 2.5H1.5v9h3.757a3.75 3.75 0 011.994.574zM8.755 4.75l-.004 7.322a3.752 3.752 0 011.992-.572H14.5v-9h-3.495a2.25 2.25 0 00-2.25 2.25z"/>
            </svg>
            <span style={{ fontSize: 13, fontWeight: 600, color: COLORS.textMuted, textTransform: "uppercase", letterSpacing: "0.06em" }}>README.md</span>
          </div>
          <p style={{ margin: "0 0 6px", fontSize: 13, color: COLORS.textMuted, lineHeight: 1.6 }}>
            Compares a <span style={{ color: COLORS.green }}>Buy-the-Dip</span> strategy against a <span style={{ color: COLORS.blue }}>Monthly SIP</span> on any ticker.
            Replicates the full Python backtest — metrics, drawdown, CAGR, and entry charts.
          </p>
          <p style={{ margin: 0, fontSize: 12, color: COLORS.textFaint, fontFamily: "monospace" }}>
            src: yfinance + pandas · powered by claude-sonnet-4
          </p>
        </div>

        {/* Config Panel */}
        <div style={{
          background: COLORS.surface,
          border: `1px solid ${COLORS.border}`,
          borderRadius: 6,
          marginBottom: 20,
          overflow: "hidden",
        }}>
          <div style={{
            borderBottom: `1px solid ${COLORS.border}`,
            padding: "10px 16px",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}>
            <svg width="14" height="14" viewBox="0 0 16 16" fill={COLORS.textMuted}>
              <path d="M8 0a8 8 0 100 16A8 8 0 008 0zm-.5 4.5A.5.5 0 018 4a.5.5 0 01.5.5v4a.5.5 0 01-.5.5.5.5 0 01-.5-.5v-4zm.5 7.5a.75.75 0 110-1.5.75.75 0 010 1.5z"/>
            </svg>
            <span style={{ fontSize: 13, fontWeight: 600, color: COLORS.textMuted }}>inputs & configuration</span>
          </div>
          <div style={{ padding: "16px 20px" }}>
            <SectionHeader icon="◎" title="General" />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 16 }}>
              <InputField label="Ticker" value={config.ticker} onChange={setField("ticker")} />
              <InputField label="Start Date" value={config.start_date} onChange={setField("start_date")} type="date" />
              <InputField label="End Date" value={config.end_date} onChange={setField("end_date")} type="date" />
            </div>

            <Divider />
            <SectionHeader icon="▲" title="Buy-the-Dip Settings" />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 12, marginBottom: 16 }}>
              <InputField label="Initial Dip %" value={config.dip_threshold} onChange={setField("dip_threshold")} type="number" step="0.005" min="0" max="1" />
              <InputField label="Initial Amount ($)" value={config.investment_amount} onChange={setField("investment_amount")} type="number" step="100" min="0" />
              <InputField label="Subsequent Dip %" value={config.subsequent_dip_threshold} onChange={setField("subsequent_dip_threshold")} type="number" step="0.005" min="0" max="1" />
              <InputField label="Subsequent Amount ($)" value={config.subsequent_investment_amount} onChange={setField("subsequent_investment_amount")} type="number" step="100" min="0" />
            </div>

            <Divider />
            <SectionHeader icon="◉" title="Monthly SIP Settings" />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 3fr", gap: 12, marginBottom: 4 }}>
              <InputField label="Monthly SIP ($)" value={config.manual_sip_amount} onChange={setField("manual_sip_amount")} type="number" step="100" min="0" />
              <div style={{ display: "flex", alignItems: "flex-end", paddingBottom: 2 }}>
                <span style={{ fontSize: 11, color: COLORS.textFaint, fontFamily: "monospace" }}>
                  Set to 0 to auto-match total BTD capital across months
                </span>
              </div>
            </div>
          </div>

          <div style={{ borderTop: `1px solid ${COLORS.border}`, padding: "12px 20px", display: "flex", justifyContent: "flex-end" }}>
            <button
              onClick={run}
              disabled={loading}
              style={{
                background: loading ? COLORS.borderLight : "#238636",
                border: `1px solid ${loading ? COLORS.border : "#2ea043"}`,
                borderRadius: 6,
                color: loading ? COLORS.textMuted : "#fff",
                padding: "7px 20px",
                fontSize: 13,
                fontWeight: 600,
                cursor: loading ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                gap: 8,
                fontFamily: "monospace",
              }}
            >
              {loading ? "Running backtest..." : "▶ Run Backtest"}
            </button>
          </div>
        </div>

        {/* Status */}
        {streamLog && (
          <div style={{
            background: COLORS.surface,
            border: `1px solid ${COLORS.border}`,
            borderRadius: 6,
            padding: "10px 16px",
            marginBottom: 16,
            fontSize: 12,
            color: COLORS.textMuted,
            fontFamily: "monospace",
          }}>
            <span style={{ color: COLORS.orange }}>◉</span> {streamLog}
          </div>
        )}

        {error && (
          <div style={{
            background: "#5a0f0f33",
            border: `1px solid ${COLORS.red}`,
            borderRadius: 6,
            padding: "12px 16px",
            marginBottom: 16,
            fontSize: 13,
            color: COLORS.red,
            fontFamily: "monospace",
          }}>
            ✗ Error: {error}
          </div>
        )}

        {/* Results */}
        {result && (
          <>
            {/* BTD Block */}
            <div style={{
              background: COLORS.surface,
              border: `1px solid ${COLORS.border}`,
              borderRadius: 6,
              overflow: "hidden",
              marginBottom: 16,
            }}>
              <div style={{
                borderBottom: `1px solid ${COLORS.border}`,
                padding: "10px 16px",
                display: "flex",
                alignItems: "center",
                gap: 10,
                background: "#3fb95011",
              }}>
                <span style={{ width: 10, height: 10, background: COLORS.green, borderRadius: 2, display: "inline-block" }} />
                <span style={{ fontSize: 13, fontWeight: 700, color: COLORS.green, fontFamily: "monospace" }}>
                  STRATEGY PERFORMANCE: BUY THE DIP
                </span>
              </div>
              <div style={{ padding: "16px 20px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 12 }}>
                  <MetricCard label="Total Cash Deployed" value={fmtDollar(btd?.total_invested)} />
                  <MetricCard label="Final Portfolio Value" value={fmtDollar(btd?.final_value)} />
                  <MetricCard label="Net Profit / Loss" value={fmtDollar(btd?.net_profit)} color={btd?.net_profit >= 0 ? COLORS.green : COLORS.red} />
                  <MetricCard label="Strategy Return" value={fmtPct(btd?.return_pct).val} color={fmtPct(btd?.return_pct).color} />
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
                  <MetricCard label="Max Strategy Drawdown" value={fmtPct(btd?.max_drawdown_pct).val} color={COLORS.red} />
                  <MetricCard label="Total Trades" value={btd?.num_trades ?? "—"} />
                  <MetricCard label="Avg Entry Price" value={fmtDollar(btd?.avg_entry_price)} />
                  <MetricCard label="Strategy CAGR" value={fmtPct(btd?.cagr_pct).val} color={fmtPct(btd?.cagr_pct).color} />
                </div>
              </div>
            </div>

            {/* SIP Block */}
            <div style={{
              background: COLORS.surface,
              border: `1px solid ${COLORS.border}`,
              borderRadius: 6,
              overflow: "hidden",
              marginBottom: 16,
            }}>
              <div style={{
                borderBottom: `1px solid ${COLORS.border}`,
                padding: "10px 16px",
                display: "flex",
                alignItems: "center",
                gap: 10,
                background: "#58a6ff11",
              }}>
                <span style={{ width: 10, height: 10, background: COLORS.blue, borderRadius: 2, display: "inline-block" }} />
                <span style={{ fontSize: 13, fontWeight: 700, color: COLORS.blue, fontFamily: "monospace" }}>
                  STRATEGY PERFORMANCE: MONTHLY SIP (${fmt(sip?.monthly_amount, 2)}/mo)
                </span>
              </div>
              <div style={{ padding: "16px 20px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 12 }}>
                  <MetricCard label="Total Cash Deployed" value={fmtDollar(sip?.total_invested)} />
                  <MetricCard label="Final Portfolio Value" value={fmtDollar(sip?.final_value)} />
                  <MetricCard label="Net Profit / Loss" value={fmtDollar(sip?.net_profit)} color={sip?.net_profit >= 0 ? COLORS.green : COLORS.red} />
                  <MetricCard label="Strategy Return" value={fmtPct(sip?.return_pct).val} color={fmtPct(sip?.return_pct).color} />
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
                  <MetricCard label="Max Strategy Drawdown" value={fmtPct(sip?.max_drawdown_pct).val} color={COLORS.red} />
                  <MetricCard label="Avg Entry Price" value={fmtDollar(sip?.avg_entry_price)} />
                  <MetricCard label="Strategy CAGR" value={fmtPct(sip?.cagr_pct).val} color={fmtPct(sip?.cagr_pct).color} />
                </div>
              </div>
            </div>

            {/* Charts */}
            <div style={{
              background: COLORS.surface,
              border: `1px solid ${COLORS.border}`,
              borderRadius: 6,
              overflow: "hidden",
              marginBottom: 16,
            }}>
              <div style={{
                borderBottom: `1px solid ${COLORS.border}`,
                padding: "10px 16px",
              }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: COLORS.textMuted, fontFamily: "monospace" }}>
                  Strategy Evaluation Comparison ({config.ticker})
                </span>
              </div>
              <div style={{ padding: "16px 20px" }}>
                <div style={{ display: "flex", gap: 20, marginBottom: 16, flexWrap: "wrap" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: COLORS.textMuted, fontFamily: "monospace" }}>
                    <span style={{ width: 20, height: 2, background: CHART_COLORS.price + "55", display: "inline-block" }} />
                    {config.ticker} Close Price
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: COLORS.textMuted, fontFamily: "monospace" }}>
                    <svg width="12" height="12" viewBox="0 0 12 12"><polygon points="6,0 12,12 0,12" fill={COLORS.initialBuy} /></svg>
                    BTD Initial Trigger (-{(config.dip_threshold * 100).toFixed(1)}%: ${config.investment_amount.toLocaleString()})
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: COLORS.textMuted, fontFamily: "monospace" }}>
                    <svg width="10" height="10" viewBox="0 0 10 10"><polygon points="5,0 10,10 0,10" fill={COLORS.subBuy} /></svg>
                    BTD Subsequent (-{(config.subsequent_dip_threshold * 100).toFixed(1)}%: ${config.subsequent_investment_amount.toLocaleString()})
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: COLORS.textMuted, fontFamily: "monospace" }}>
                    <span style={{ width: 8, height: 8, borderRadius: "50%", background: COLORS.sipDot + "99", display: "inline-block" }} />
                    Monthly SIP (${config.manual_sip_amount.toLocaleString()}/mo)
                  </div>
                </div>

                {result.price_series && (
                  <LineChart series={result.price_series} trades={btd?.trades} width={812} height={300} />
                )}

                <div style={{ marginTop: 28, marginBottom: 10 }}>
                  <div style={{ display: "flex", gap: 20, marginBottom: 12, flexWrap: "wrap" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: COLORS.textMuted, fontFamily: "monospace" }}>
                      <span style={{ width: 20, height: 2, background: COLORS.btdLine, display: "inline-block" }} />
                      BTD Portfolio Value
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: COLORS.textMuted, fontFamily: "monospace" }}>
                      <span style={{ width: 20, height: 0, borderTop: `2px dashed ${COLORS.sipLine}`, display: "inline-block" }} />
                      SIP Portfolio Value
                    </div>
                  </div>
                  {result.portfolio_series && (
                    <PortfolioChart portfolioSeries={result.portfolio_series} width={812} height={220} />
                  )}
                </div>
              </div>
            </div>

            {/* Trade Log */}
            {btd?.trades && btd.trades.length > 0 && (
              <div style={{
                background: COLORS.surface,
                border: `1px solid ${COLORS.border}`,
                borderRadius: 6,
                overflow: "hidden",
              }}>
                <div style={{
                  borderBottom: `1px solid ${COLORS.border}`,
                  padding: "10px 16px",
                }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: COLORS.textMuted, fontFamily: "monospace" }}>
                    BTD Trade Log — {btd.trades.length} entries
                  </span>
                </div>
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, fontFamily: "monospace" }}>
                    <thead>
                      <tr style={{ borderBottom: `1px solid ${COLORS.border}` }}>
                        {["#", "Date", "Type", "Price", "Amount", "Shares"].map(h => (
                          <th key={h} style={{ padding: "8px 16px", textAlign: "left", color: COLORS.textMuted, fontWeight: 500 }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {btd.trades.map((t, i) => (
                        <tr key={i} style={{ borderBottom: `1px solid ${COLORS.borderLight}` }}>
                          <td style={{ padding: "7px 16px", color: COLORS.textFaint }}>{i + 1}</td>
                          <td style={{ padding: "7px 16px", color: COLORS.textMuted }}>{t.date}</td>
                          <td style={{ padding: "7px 16px" }}>
                            <span style={{
                              background: t.type === "initial" ? "#3fb95022" : "#f8514922",
                              color: t.type === "initial" ? COLORS.green : COLORS.red,
                              border: `1px solid ${t.type === "initial" ? COLORS.green + "44" : COLORS.red + "44"}`,
                              borderRadius: 4,
                              padding: "2px 8px",
                              fontSize: 11,
                            }}>
                              {t.type}
                            </span>
                          </td>
                          <td style={{ padding: "7px 16px", color: COLORS.text }}>${fmt(t.price)}</td>
                          <td style={{ padding: "7px 16px", color: COLORS.text }}>${fmt(t.amount)}</td>
                          <td style={{ padding: "7px 16px", color: COLORS.textMuted }}>{fmt(t.amount / t.price, 4)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

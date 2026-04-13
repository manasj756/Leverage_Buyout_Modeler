import { useState, useEffect, useCallback, useRef } from 'react'
import './App.css'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell, ReferenceLine, ComposedChart, Line
} from 'recharts'

const API_URL = 'http://127.0.0.1:8001'

// ── Default Assumptions ────────────────────────────────────
const DEFAULT_ASSUMPTIONS = {
  company_name: 'Devyani International',
  base_year: 2024,
  entry_year_ebitda: 120.0,
  entry_ev_multiple: 8.0,
  exit_ev_multiple: 9.0,
  holding_period: 5,
  debt_pct: 0.65,
  interest_rate: 0.10,
  revenue_base: 800.0,
  revenue_cagr: 0.12,
  ebitda_margin: 0.18,
  depreciation_pct_revenue: 0.03,
  capex_pct_revenue: 0.04,
  change_in_wc_pct_revenue: 0.01,
  tax_rate: 0.25,
  cash_sweep: true,
}

// ── Helpers ────────────────────────────────────────────────
function fmt(val, decimals = 1) {
  if (val == null) return 'N/A'
  return Number(val).toFixed(decimals)
}

function fmtCr(val) {
  if (val == null) return 'N/A'
  return `₹${Number(val).toLocaleString('en-IN', { maximumFractionDigits: 0 })} Cr`
}

function getIrrClass(irr) {
  if (irr == null) return 'irr-na'
  if (irr >= 25) return 'irr-exceptional'
  if (irr >= 20) return 'irr-good'
  if (irr >= 15) return 'irr-marginal'
  if (irr >= 10) return 'irr-weak'
  return 'irr-avoid'
}

function getVerdictClass(verdict) {
  if (!verdict) return 'verdict-weak'
  if (verdict.includes('STRONG')) return 'verdict-strong'
  if (verdict.includes('GOOD')) return 'verdict-good'
  if (verdict.includes('MARGINAL')) return 'verdict-marginal'
  return 'verdict-weak'
}

function getIrrColor(irr) {
  if (irr == null) return '#64748b'
  if (irr >= 25) return '#059669'
  if (irr >= 20) return '#10b981'
  if (irr >= 15) return '#eab308'
  if (irr >= 10) return '#f97316'
  return '#dc2626'
}

const SCENARIO_COLORS = {
  Bull: '#10b981',
  Base: '#3b82f6',
  Bear: '#f59e0b',
  Distressed: '#ef4444',
}

// ── Definitions for info tooltips ──────────────────────────
const DEFINITIONS = {
  // Sidebar / Deal structure
  'Entry EBITDA (₹ Cr)': 'Earnings Before Interest, Tax, Depreciation & Amortization in the acquisition year. The baseline profitability used to price the deal.',
  'Entry Multiple': 'EV/EBITDA multiple paid at acquisition. Higher multiple = more expensive purchase. Typical LBO range: 6–10x.',
  'Exit Multiple': 'EV/EBITDA multiple expected at sale. If higher than entry, it creates "multiple expansion" — a key return driver.',
  'Holding Period': 'Number of years the PE firm holds the company before selling. Typical PE hold: 3–7 years.',
  'Debt %': 'Percentage of the purchase price funded by borrowed money. Higher leverage amplifies returns but increases risk.',
  'Interest Rate': 'Annual interest rate charged on the acquisition debt. Directly impacts free cash flow available for debt repayment.',
  'Revenue Base (₹ Cr)': 'Starting annual revenue in the base year. All future revenue projections grow from this number using the CAGR.',
  'Revenue CAGR': 'Compound Annual Growth Rate — the annual % rate at which revenue is projected to grow each year.',
  'EBITDA Margin': 'EBITDA as a percentage of revenue. Measures operational efficiency — how much of each rupee of revenue becomes operating profit.',
  'Capex % Revenue': 'Capital Expenditure as a percentage of revenue. Cash spent on assets (stores, equipment). Reduces Free Cash Flow.',
  'Tax Rate': 'Corporate income tax rate applied to positive earnings before tax.',
  // KPI Cards
  'Base IRR': 'Internal Rate of Return — the annualized % return on equity. PE firms target 20%+. Calculated by finding the discount rate where NPV of all cash flows equals zero.',
  'Money-on-Money': 'Total cash returned divided by total cash invested. A 2.7x MoM means you got back ₹2.70 for every ₹1 invested. Does NOT account for time.',
  'Exit Enterprise Value': 'Total value of the company at sale, calculated as Exit EBITDA × Exit Multiple. This is what the next buyer pays.',
  'Equity at Exit': 'Cash proceeds to the PE firm after repaying all remaining debt from the exit enterprise value. This is the actual "payday".',
  // Attribution
  'EBITDA Growth': 'Value created because the company became more profitable. Higher exit EBITDA × entry multiple shows the operational improvement component.',
  'Multiple Expansion': 'Value created from selling at a higher EV/EBITDA multiple than the purchase multiple. Reflects market re-rating of the business.',
  'Debt Paydown': 'Value created from repaying acquisition debt using company cash flows. Every ₹1 of debt repaid = ₹1 more equity for the PE firm at exit.',
  // Scenarios
  'Revenue CAGR (scenario)': 'Projected annual revenue growth rate under this scenario.',
  'EBITDA Margin (scenario)': 'Projected operating margin under this scenario.',
  'Exit Multiple (scenario)': 'Expected sale multiple under this scenario\'s market conditions.',
  'Exit Equity (scenario)': 'Cash to equity holders after debt repayment under this scenario.',
}

// ── InfoIcon Component ─────────────────────────────────────
function InfoIcon({ term }) {
  const def = DEFINITIONS[term]
  if (!def) return null

  const iconRef = useRef(null)
  const tooltipRef = useRef(null)
  const [pos, setPos] = useState({ top: 0, left: 0 })
  const [visible, setVisible] = useState(false)

  const handleMouseEnter = () => {
    if (iconRef.current) {
      const rect = iconRef.current.getBoundingClientRect()
      const tooltipWidth = 260
      let left = rect.left + rect.width / 2 - tooltipWidth / 2
      // Clamp so tooltip doesn't go off-screen
      if (left < 8) left = 8
      if (left + tooltipWidth > window.innerWidth - 8) left = window.innerWidth - tooltipWidth - 8
      setPos({
        top: rect.top - 8, // will be adjusted with transform in CSS
        left,
      })
    }
    setVisible(true)
  }

  const handleMouseLeave = () => {
    setVisible(false)
  }

  return (
    <span className="info-wrap" onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
      <span className="info-icon" ref={iconRef}>i</span>
      {visible && (
        <div
          className="info-tooltip"
          ref={tooltipRef}
          style={{
            position: 'fixed',
            top: pos.top,
            left: pos.left,
            transform: 'translateY(-100%)',
            visibility: 'visible',
            opacity: 1,
            pointerEvents: 'none',
          }}
        >
          {def}
        </div>
      )}
    </span>
  )
}

// ══════════════════════════════════════════════════════════
//  MAIN APP
// ══════════════════════════════════════════════════════════
export default function App() {
  const [assumptions, setAssumptions] = useState(DEFAULT_ASSUMPTIONS)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')
  const [error, setError] = useState(null)

  const calculate = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await fetch(`${API_URL}/api/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(assumptions),
      })
      if (!resp.ok) throw new Error(`API error: ${resp.status}`)
      const result = await resp.json()
      setData(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [assumptions])

  // Auto-calculate on first load
  useEffect(() => { calculate() }, [])

  const updateAssumption = (key, value) => {
    setAssumptions(prev => ({ ...prev, [key]: value }))
  }

  return (
    <div className="app-layout">
      {/* ── Header ──────────────────────────────────────── */}
      <header className="app-header">
        <h1>◆ LBO Financial Modeler</h1>
        <div className="header-badge">
          <span className="pulse-dot" />
          {data ? 'Model Ready' : 'Awaiting Input'}
        </div>
      </header>

      {/* ── Sidebar: Control Panel ──────────────────────── */}
      <aside className="sidebar">
        <SidebarControls
          assumptions={assumptions}
          onChange={updateAssumption}
          onCalculate={calculate}
          loading={loading}
        />
      </aside>

      {/* ── Main Dashboard ──────────────────────────────── */}
      <main className="main-content">
        {error && (
          <div style={{ padding: 16, background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.2)', borderRadius: 10, marginBottom: 16, color: '#f43f5e', fontSize: '0.85rem' }}>
            ⚠ Error: {error}
          </div>
        )}
        {loading ? (
          <div className="loading-overlay">
            <div className="spinner" />
          </div>
        ) : !data ? (
          <div className="empty-state">
            <div className="empty-state-icon">📊</div>
            <h2>Configure Your LBO Model</h2>
            <p>Set your deal assumptions in the control panel on the left and click "Run Analysis" to generate the full LBO breakdown.</p>
          </div>
        ) : (
          <Dashboard data={data} activeTab={activeTab} setActiveTab={setActiveTab} />
        )}
      </main>
    </div>
  )
}


// ══════════════════════════════════════════════════════════
//  SIDEBAR CONTROLS
// ══════════════════════════════════════════════════════════
function SidebarControls({ assumptions, onChange, onCalculate, loading }) {
  return (
    <>
      <div className="sidebar-section">
        <div className="sidebar-section-title">Company</div>
        <div className="input-group">
          <label className="input-label">Company Name</label>
          <input
            className="input-text"
            type="text"
            value={assumptions.company_name}
            onChange={e => onChange('company_name', e.target.value)}
          />
        </div>
      </div>

      <div className="sidebar-section">
        <div className="sidebar-section-title">Deal Structure</div>
        <SliderInput label="Entry EBITDA (₹ Cr)" value={assumptions.entry_year_ebitda}
          min={20} max={500} step={5} format={v => `₹${v}`}
          onChange={v => onChange('entry_year_ebitda', v)} info />
        <SliderInput label="Entry Multiple" value={assumptions.entry_ev_multiple}
          min={3} max={15} step={0.5} format={v => `${v}x`}
          onChange={v => onChange('entry_ev_multiple', v)} info />
        <SliderInput label="Exit Multiple" value={assumptions.exit_ev_multiple}
          min={3} max={15} step={0.5} format={v => `${v}x`}
          onChange={v => onChange('exit_ev_multiple', v)} info />
        <SliderInput label="Holding Period" value={assumptions.holding_period}
          min={2} max={10} step={1} format={v => `${v} yrs`}
          onChange={v => onChange('holding_period', v)} info />
      </div>

      <div className="sidebar-section">
        <div className="sidebar-section-title">Capital Structure</div>
        <SliderInput label="Debt %" value={assumptions.debt_pct}
          min={0.30} max={0.85} step={0.05} format={v => `${(v * 100).toFixed(0)}%`}
          onChange={v => onChange('debt_pct', v)} info />
        <SliderInput label="Interest Rate" value={assumptions.interest_rate}
          min={0.04} max={0.18} step={0.005} format={v => `${(v * 100).toFixed(1)}%`}
          onChange={v => onChange('interest_rate', v)} info />
      </div>

      <div className="sidebar-section">
        <div className="sidebar-section-title">Operating Assumptions</div>
        <SliderInput label="Revenue Base (₹ Cr)" value={assumptions.revenue_base}
          min={100} max={2000} step={50} format={v => `₹${v}`}
          onChange={v => onChange('revenue_base', v)} info />
        <SliderInput label="Revenue CAGR" value={assumptions.revenue_cagr}
          min={0.0} max={0.30} step={0.01} format={v => `${(v * 100).toFixed(0)}%`}
          onChange={v => onChange('revenue_cagr', v)} info />
        <SliderInput label="EBITDA Margin" value={assumptions.ebitda_margin}
          min={0.05} max={0.40} step={0.01} format={v => `${(v * 100).toFixed(0)}%`}
          onChange={v => onChange('ebitda_margin', v)} info />
        <SliderInput label="Capex % Revenue" value={assumptions.capex_pct_revenue}
          min={0.01} max={0.15} step={0.005} format={v => `${(v * 100).toFixed(1)}%`}
          onChange={v => onChange('capex_pct_revenue', v)} info />
        <SliderInput label="Tax Rate" value={assumptions.tax_rate}
          min={0.10} max={0.40} step={0.01} format={v => `${(v * 100).toFixed(0)}%`}
          onChange={v => onChange('tax_rate', v)} info />
      </div>

      <button
        className={`btn-calculate ${loading ? 'loading' : ''}`}
        onClick={onCalculate}
        disabled={loading}
      >
        {loading ? '⏳ Calculating...' : '▶ Run Analysis'}
      </button>
    </>
  )
}


// ── Slider Input ───────────────────────────────────────────
function SliderInput({ label, value, min, max, step, format, onChange, info }) {
  return (
    <div className="input-group">
      <label className="input-label">
        <span>{label}{info && <InfoIcon term={label} />}</span>
        <span className="input-value">{format(value)}</span>
      </label>
      <input
        className="input-slider"
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
      />
    </div>
  )
}


// ══════════════════════════════════════════════════════════
//  DASHBOARD
// ══════════════════════════════════════════════════════════
function Dashboard({ data, activeTab, setActiveTab }) {
  const { returns, deal_summary, scenarios, sensitivity, income_statement, debt_schedule } = data

  return (
    <div className="dashboard-grid">
      {/* ── KPI Row ─────────────────────────────────────── */}
      <div className="kpi-row animate-in">
        <div className="kpi-card kpi-irr">
          <span className="kpi-label">Base IRR</span>
          <span className={`kpi-value ${returns.irr_pct >= 20 ? 'positive' : returns.irr_pct >= 15 ? 'neutral' : 'negative'}`}>
            {fmt(returns.irr_pct)}%
          </span>
          <span className={`verdict-badge ${getVerdictClass(returns.verdict)}`}>
            {returns.verdict}
          </span>
        </div>
        <div className="kpi-card kpi-mom">
          <span className="kpi-label">Money-on-Money</span>
          <span className="kpi-value neutral">{fmt(returns.mom, 2)}x</span>
          <span className="kpi-sub">₹{fmt(deal_summary.equity_invested, 0)} Cr → {fmtCr(returns.exit_equity)}</span>
        </div>
        <div className="kpi-card kpi-ev">
          <span className="kpi-label">Exit Enterprise Value</span>
          <span className="kpi-value neutral">{fmtCr(returns.exit_ev)}</span>
          <span className="kpi-sub">Exit EBITDA: {fmtCr(returns.exit_ebitda)} @ {deal_summary.exit_ev_multiple}x</span>
        </div>
        <div className="kpi-card kpi-equity">
          <span className="kpi-label">Equity at Exit</span>
          <span className="kpi-value positive">{fmtCr(returns.exit_equity)}</span>
          <span className="kpi-sub">Remaining Debt: {fmtCr(returns.exit_debt)}</span>
        </div>
      </div>

      {/* ── Tab Navigation ──────────────────────────────── */}
      <div className="tab-nav animate-in">
        {[
          { key: 'overview', label: 'Overview' },
          { key: 'financials', label: 'Financials' },
          { key: 'scenarios', label: 'Scenarios' },
          { key: 'sensitivity', label: 'Sensitivity' },
        ].map(tab => (
          <button
            key={tab.key}
            className={`tab-btn ${activeTab === tab.key ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Tab Content ─────────────────────────────────── */}
      {activeTab === 'overview' && <OverviewTab data={data} />}
      {activeTab === 'financials' && <FinancialsTab is_data={income_statement} debt_data={debt_schedule} />}
      {activeTab === 'scenarios' && <ScenariosTab scenarios={scenarios} equity_invested={deal_summary.equity_invested} />}
      {activeTab === 'sensitivity' && <SensitivityTab sensitivity={sensitivity} />}
    </div>
  )
}


// ══════════════════════════════════════════════════════════
//  OVERVIEW TAB
// ══════════════════════════════════════════════════════════
function OverviewTab({ data }) {
  const { returns, debt_schedule, deal_summary } = data
  const attr = returns.attribution

  // Build debt waterfall data
  const years = Object.keys(debt_schedule['Opening Debt (₹ Cr)'] || {})
  const waterfallData = years.map(year => {
    const closingDebt = debt_schedule['Closing Debt (₹ Cr)']?.[year] ?? 0
    const entryEV = deal_summary.entry_ev
    return {
      year,
      debt: closingDebt,
      equity: Math.max(entryEV - closingDebt, 0),
      fcf: debt_schedule['FCF Available (₹ Cr)']?.[year] ?? 0,
      leverage: debt_schedule['Leverage Ratio (Debt/EBITDA)']?.[year],
    }
  })

  // Attribution data
  const ebitdaGrowth = attr['EBITDA Growth Contribution (₹ Cr)'] || 0
  const multipleExp = attr['Multiple Expansion (₹ Cr)'] || 0
  const debtPaydown = attr['Debt Paydown (₹ Cr)'] || 0
  const maxAttr = Math.max(Math.abs(ebitdaGrowth), Math.abs(multipleExp), Math.abs(debtPaydown), 1)

  return (
    <>
      <div className="charts-row animate-in">
        {/* Debt Waterfall */}
        <div className="card">
          <div className="card-title">
            <span className="card-icon" style={{ background: 'rgba(239,68,68,0.15)', color: '#ef4444' }}>⬇</span>
            Capital Structure Evolution
          </div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={waterfallData} barSize={36}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.06)" />
                <XAxis dataKey="year" tick={{ fill: '#64748b', fontSize: 11 }} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: '#0c1120', border: '1px solid rgba(148,163,184,0.15)', borderRadius: 8, fontSize: '0.8rem' }}
                  labelStyle={{ color: '#f1f5f9' }}
                  formatter={(value, name) => [`₹${Number(value).toFixed(0)} Cr`, name]}
                />
                <ReferenceLine y={deal_summary.entry_ev} stroke="#f59e0b" strokeDasharray="5 5"
                  label={{ value: `Entry EV: ₹${deal_summary.entry_ev}Cr`, fill: '#f59e0b', fontSize: 10, position: 'right' }} />
                <Bar dataKey="debt" stackId="cap" name="Remaining Debt" fill="#ef4444" radius={[0, 0, 0, 0]} />
                <Bar dataKey="equity" stackId="cap" name="Implied Equity" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* FCF & Leverage */}
        <div className="card">
          <div className="card-title">
            <span className="card-icon" style={{ background: 'rgba(16,185,129,0.15)', color: '#10b981' }}>💰</span>
            Free Cash Flow & Leverage
          </div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={waterfallData} barSize={36}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.06)" />
                <XAxis dataKey="year" tick={{ fill: '#64748b', fontSize: 11 }} />
                <YAxis yAxisId="left" tick={{ fill: '#64748b', fontSize: 11 }} />
                <YAxis yAxisId="right" orientation="right" tick={{ fill: '#64748b', fontSize: 11 }}
                  domain={[0, 'auto']} />
                <Tooltip
                  contentStyle={{ background: '#0c1120', border: '1px solid rgba(148,163,184,0.15)', borderRadius: 8, fontSize: '0.8rem' }}
                  labelStyle={{ color: '#f1f5f9' }}
                  formatter={(value, name) => {
                    if (name === 'Leverage') return [`${Number(value).toFixed(1)}x`, name]
                    return [`₹${Number(value).toFixed(0)} Cr`, name]
                  }}
                />
                <Bar yAxisId="left" dataKey="fcf" name="FCF" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Line yAxisId="right" type="monotone" dataKey="leverage" name="Leverage"
                  stroke="#f59e0b" strokeWidth={2} dot={{ r: 4, fill: '#f59e0b' }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Return Attribution */}
      <div className="card animate-in">
        <div className="card-title">
          <span className="card-icon" style={{ background: 'rgba(59,130,246,0.15)', color: '#3b82f6' }}>📈</span>
          Return Attribution — Where the Returns Come From
        </div>
        <div className="attribution-bars">
          <div className="attribution-item">
            <div className="attribution-header">
              <span className="attribution-label">EBITDA Growth</span>
              <span className="attribution-value">{fmtCr(ebitdaGrowth)}</span>
            </div>
            <div className="attribution-bar-track">
              <div className="attribution-bar-fill ebitda" style={{ width: `${Math.max((Math.abs(ebitdaGrowth) / maxAttr) * 100, 2)}%` }} />
            </div>
          </div>
          <div className="attribution-item">
            <div className="attribution-header">
              <span className="attribution-label">Multiple Expansion</span>
              <span className="attribution-value">{fmtCr(multipleExp)}</span>
            </div>
            <div className="attribution-bar-track">
              <div className="attribution-bar-fill multiple" style={{ width: `${Math.max((Math.abs(multipleExp) / maxAttr) * 100, 2)}%` }} />
            </div>
          </div>
          <div className="attribution-item">
            <div className="attribution-header">
              <span className="attribution-label">Debt Paydown</span>
              <span className="attribution-value">{fmtCr(debtPaydown)}</span>
            </div>
            <div className="attribution-bar-track">
              <div className="attribution-bar-fill debt" style={{ width: `${Math.max((Math.abs(debtPaydown) / maxAttr) * 100, 2)}%` }} />
            </div>
          </div>
        </div>
      </div>

      {/* Deal Structure Summary */}
      <div className="card animate-in">
        <div className="card-title">
          <span className="card-icon" style={{ background: 'rgba(167,139,250,0.15)', color: '#a78bfa' }}>📋</span>
          Deal Structure
        </div>
        <table className="data-table">
          <tbody>
            <tr><td>Entry EV/EBITDA</td><td>{data.deal_summary.entry_ev_multiple}x</td></tr>
            <tr><td>Entry Enterprise Value</td><td>{fmtCr(data.deal_summary.entry_ev)}</td></tr>
            <tr><td>Total Debt Raised</td><td>{fmtCr(data.deal_summary.total_debt)} ({(data.deal_summary.debt_pct * 100).toFixed(0)}%)</td></tr>
            <tr><td>Equity Invested</td><td>{fmtCr(data.deal_summary.equity_invested)} ({((1 - data.deal_summary.debt_pct) * 100).toFixed(0)}%)</td></tr>
            <tr><td>Interest Rate</td><td>{(data.deal_summary.interest_rate * 100).toFixed(1)}%</td></tr>
            <tr><td>Holding Period</td><td>{data.deal_summary.holding_period} Years</td></tr>
            <tr><td>Exit Multiple</td><td>{data.deal_summary.exit_ev_multiple}x</td></tr>
            <tr><td>Revenue CAGR</td><td>{(data.deal_summary.revenue_cagr * 100).toFixed(0)}%</td></tr>
            <tr><td>EBITDA Margin</td><td>{(data.deal_summary.ebitda_margin * 100).toFixed(0)}%</td></tr>
          </tbody>
        </table>
      </div>
    </>
  )
}


// ══════════════════════════════════════════════════════════
//  FINANCIALS TAB
// ══════════════════════════════════════════════════════════
function FinancialsTab({ is_data, debt_data }) {
  const isRows = Object.keys(is_data || {})
  const debtRows = Object.keys(debt_data || {})
  const years = isRows.length > 0 ? Object.keys(is_data[isRows[0]]) : []
  const debtYears = debtRows.length > 0 ? Object.keys(debt_data[debtRows[0]]) : []

  const highlightRows = new Set(['EBITDA (₹ Cr)', 'Free Cash Flow (₹ Cr)'])
  const debtHighlightRows = new Set(['Closing Debt (₹ Cr)', 'FCF Available (₹ Cr)'])

  return (
    <>
      <div className="card animate-in">
        <div className="card-title">
          <span className="card-icon" style={{ background: 'rgba(59,130,246,0.15)', color: '#3b82f6' }}>📊</span>
          Projected Income Statement & Free Cash Flow
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Line Item</th>
                {years.map(y => <th key={y}>{y}</th>)}
              </tr>
            </thead>
            <tbody>
              {isRows.map(row => (
                <tr key={row} className={highlightRows.has(row) ? 'highlight' : ''}>
                  <td>{row}</td>
                  {years.map(y => <td key={y}>{fmt(is_data[row][y])}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card animate-in">
        <div className="card-title">
          <span className="card-icon" style={{ background: 'rgba(239,68,68,0.15)', color: '#ef4444' }}>🏦</span>
          Debt Repayment Schedule
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Line Item</th>
                {debtYears.map(y => <th key={y}>{y}</th>)}
              </tr>
            </thead>
            <tbody>
              {debtRows.map(row => (
                <tr key={row} className={debtHighlightRows.has(row) ? 'highlight' : ''}>
                  <td>{row}</td>
                  {debtYears.map(y => <td key={y}>{fmt(debt_data[row][y])}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}


// ══════════════════════════════════════════════════════════
//  SCENARIOS TAB
// ══════════════════════════════════════════════════════════
function ScenariosTab({ scenarios, equity_invested }) {
  const scenarioNames = Object.keys(scenarios)
  const classMap = { Bull: 'bull', Base: 'base', Bear: 'bear', Distressed: 'distressed' }

  // Chart data
  const chartData = scenarioNames.map(name => ({
    name,
    irr: scenarios[name].irr_pct,
    exit_equity: scenarios[name].exit_equity,
    invested: equity_invested,
  }))

  return (
    <>
      {/* Scenario Cards */}
      <div className="scenario-grid animate-in">
        {scenarioNames.map(name => {
          const s = scenarios[name]
          return (
            <div key={name} className={`scenario-card ${classMap[name] || ''}`}>
              <div className="scenario-name">{name}</div>
              <div className="scenario-irr" style={{ color: getIrrColor(s.irr_pct) }}>
                {s.irr_pct != null ? `${fmt(s.irr_pct)}%` : 'N/A'}
              </div>
              <div className="scenario-mom">{fmt(s.mom, 2)}x MoM</div>
              <div className="scenario-detail">
                <span>Revenue CAGR <span className="detail-value">{s.revenue_cagr}%</span></span>
                <span>EBITDA Margin <span className="detail-value">{s.ebitda_margin}%</span></span>
                <span>Exit Multiple <span className="detail-value">{s.exit_multiple}x</span></span>
                <span>Exit Equity <span className="detail-value">{fmtCr(s.exit_equity)}</span></span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Scenario Charts */}
      <div className="charts-row animate-in">
        <div className="card">
          <div className="card-title">IRR by Scenario</div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} barSize={44}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.06)" />
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: '#0c1120', border: '1px solid rgba(148,163,184,0.15)', borderRadius: 8 }}
                  labelStyle={{ color: '#f1f5f9' }}
                  formatter={v => [`${fmt(v)}%`, 'IRR']}
                />
                <ReferenceLine y={20} stroke="#f59e0b" strokeDasharray="5 5"
                  label={{ value: '20% Hurdle', fill: '#f59e0b', fontSize: 10 }} />
                <Bar dataKey="irr" name="IRR (%)" radius={[6, 6, 0, 0]}>
                  {chartData.map((entry, i) => (
                    <Cell key={i} fill={SCENARIO_COLORS[entry.name] || '#3b82f6'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-title">Equity: Invested vs Exit</div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} barSize={28}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.06)" />
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: '#0c1120', border: '1px solid rgba(148,163,184,0.15)', borderRadius: 8 }}
                  labelStyle={{ color: '#f1f5f9' }}
                  formatter={v => [fmtCr(v)]}
                />
                <Bar dataKey="invested" name="Invested" fill="#475569" radius={[4, 4, 0, 0]} />
                <Bar dataKey="exit_equity" name="Exit Equity" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, i) => (
                    <Cell key={i} fill={SCENARIO_COLORS[entry.name] || '#3b82f6'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </>
  )
}


// ══════════════════════════════════════════════════════════
//  SENSITIVITY TAB
// ══════════════════════════════════════════════════════════
function SensitivityTab({ sensitivity }) {
  return (
    <>
      <HeatmapCard config={sensitivity.entry_exit} />
      <HeatmapCard config={sensitivity.growth_margin} />
    </>
  )
}

function HeatmapCard({ config }) {
  const { title, row_label, col_label, data, base_row, base_col } = config
  const rowLabels = Object.keys(data)
  const colLabels = rowLabels.length > 0 ? Object.keys(data[rowLabels[0]]) : []

  return (
    <div className="card animate-in">
      <div className="card-title">
        <span className="card-icon" style={{ background: 'rgba(16,185,129,0.15)', color: '#10b981' }}>🔥</span>
        {title}
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table className="heatmap-table">
          <thead>
            <tr>
              <th className="row-header">{row_label} ↓ / {col_label} →</th>
              {colLabels.map(c => <th key={c}>{c}</th>)}
            </tr>
          </thead>
          <tbody>
            {rowLabels.map(row => (
              <tr key={row}>
                <th className="row-header">{row}</th>
                {colLabels.map(col => {
                  const val = data[row][col]
                  const isBase = row === base_row && col === base_col
                  return (
                    <td key={col}
                      className={`heatmap-cell ${getIrrClass(val)} ${isBase ? 'base-case' : ''}`}
                      title={`${row_label}: ${row} | ${col_label}: ${col} → IRR: ${val != null ? fmt(val) + '%' : 'N/A'}`}
                    >
                      {val != null ? fmt(val) : 'N/A'}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="heatmap-legend">
        <div className="legend-item"><div className="legend-swatch" style={{ background: '#059669' }} /> &gt;25% Exceptional</div>
        <div className="legend-item"><div className="legend-swatch" style={{ background: '#10b981' }} /> 20–25% Good</div>
        <div className="legend-item"><div className="legend-swatch" style={{ background: '#eab308' }} /> 15–20% Marginal</div>
        <div className="legend-item"><div className="legend-swatch" style={{ background: '#f97316' }} /> 10–15% Weak</div>
        <div className="legend-item"><div className="legend-swatch" style={{ background: '#dc2626' }} /> &lt;10% Avoid</div>
      </div>
    </div>
  )
}

import { useEffect, useRef, useState } from 'react'
import './App.css'
import { useGoogleAuth } from './hooks/useGoogleAuth'
import { downloadFileContent, findFinanceFolder, listFinanceFiles } from './utils/driveApi'
import { prefetchPyodide, runSummarizer } from './utils/pyEngine'

// Formatters mirroring multi_account_summarizer/writer.py's conventions:
// spending is always shown with a leading "-", credits/income always "+".
function fmtSpending(amount) { return `-$${Math.abs(amount ?? 0).toFixed(2)}` }
function fmtCredit(amount)   { return `+$${Math.abs(amount ?? 0).toFixed(2)}` }
function fmtAmount(amount) {
  amount = amount ?? 0
  return amount < 0 ? `-$${Math.abs(amount).toFixed(2)}` : `+$${amount.toFixed(2)}`
}
function fmtMonthLabel(monthKey) {
  const [year, month] = monthKey.split('-').map(Number)
  return new Date(year, month - 1, 1).toLocaleString('en-US', { month: 'short', year: 'numeric' })
}

const PIPELINE_STAGES = (fileCount) => [
  ['Connecting to Google Drive', 'Scanning Finance/ folder', `Downloading ${fileCount} CSV files…`, 'Sending to Python engine', 'Building summary payload'],
  ['Connecting to Google Drive', 'Scanning Finance/ folder', `Downloaded ${fileCount} CSV files`, 'Python engine processing…', 'Building summary payload'],
  ['Connecting to Google Drive', 'Scanning Finance/ folder', `Downloaded ${fileCount} CSV files`, 'Python engine complete', 'Summary payload ready ✓'],
]
const PIPELINE_ICONS = ['☁️', '📂', '📥', '🐍', '📊']

function LineChart() {
  return (
    <svg viewBox="0 0 420 160" width="100%" height="160" style={{ display: 'block' }}>
      <line x1="40" y1="10"  x2="400" y2="10"  stroke="#f0f0f0" strokeWidth="1"/>
      <line x1="40" y1="50"  x2="400" y2="50"  stroke="#f0f0f0" strokeWidth="1"/>
      <line x1="40" y1="90"  x2="400" y2="90"  stroke="#f0f0f0" strokeWidth="1"/>
      <line x1="40" y1="130" x2="400" y2="130" stroke="#f0f0f0" strokeWidth="1"/>
      <text x="35" y="14"  textAnchor="end" fontSize="10" fill="#b2bec3">$3k</text>
      <text x="35" y="54"  textAnchor="end" fontSize="10" fill="#b2bec3">$2k</text>
      <text x="35" y="94"  textAnchor="end" fontSize="10" fill="#b2bec3">$1k</text>
      <text x="35" y="134" textAnchor="end" fontSize="10" fill="#b2bec3">$0</text>
      <polygon
        points="40,88 100,62 160,96 220,36 280,55 340,106 400,130"
        fill="#00b894" fillOpacity="0.1"/>
      <polyline
        points="40,88 100,62 160,96 220,36 280,55 340,106"
        fill="none" stroke="#00b894" strokeWidth="2.5" strokeLinejoin="round"/>
      <polyline
        points="340,106 400,130"
        fill="none" stroke="#b2bec3" strokeWidth="2" strokeDasharray="5,4"/>
      {[[40,88],[100,62],[160,96],[220,36],[340,106]].map(([x,y]) => (
        <circle key={x} cx={x} cy={y} r="4" fill="#00b894"/>
      ))}
      <circle cx="280" cy="55" r="5" fill="#00cec9" stroke="#fff" strokeWidth="2"/>
      <circle cx="400" cy="130" r="4" fill="#b2bec3"/>
      {[['Jan',40],['Feb',100],['Mar',160],['Apr',220],['Jun',340],['Jul',400]].map(([label,x]) => (
        <text key={label} x={x} y="150" textAnchor="middle" fontSize="10" fill="#b2bec3">{label}</text>
      ))}
      <text x="280" y="150" textAnchor="middle" fontSize="10" fill="#00cec9" fontWeight="600">May</text>
    </svg>
  )
}

function PieChart() {
  return (
    <div className="pie-wrapper">
      <div className="pie"/>
      <div className="legend">
        {[
          ['#00b894','Groceries 35%'],
          ['#0984e3','Dining 23%'],
          ['#fdcb6e','Shopping 14%'],
          ['#e17055','Transport 12%'],
          ['#a29bfe','Other 16%'],
        ].map(([color, label]) => (
          <div key={label} className="legend-item">
            <div className="dot" style={{ background: color }}/>
            {label}
          </div>
        ))}
      </div>
    </div>
  )
}

function AppNav({ profile, onSignOut }) {
  return (
    <nav>
      <div className="logo">Finance<span>Dashboard</span></div>
      <div className="google-account">
        {profile?.picture && <img className="google-avatar" src={profile.picture} alt=""/>}
        <span className="google-email">{profile?.email}</span>
        <button className="btn btn-google" onClick={onSignOut}>Sign out</button>
      </div>
    </nav>
  )
}

function LandingScreen({ onSignIn, error }) {
  return (
    <div className="flow-landing">
      <div className="landing-badge">✦ Personal Finance</div>
      <h1 className="landing-title">Your money,<br/><em>clearly summarized</em></h1>
      <p className="landing-sub">
        Connect your Google Drive to automatically pull your bank and credit card CSV exports —
        we'll crunch the numbers and show you the full picture.
      </p>
      <button className="btn btn-google btn-gsi" onClick={onSignIn}>
        <div className="google-icon"/>
        Sign in with Google
      </button>
      {error && <div className="google-auth-error">{error}</div>}
      <p className="landing-footnote">No account needed to browse · Your data stays in your Drive</p>
    </div>
  )
}

function CheckingScreen() {
  return (
    <div className="flow-checking">
      <div className="spinner"/>
      <div className="check-title">Checking your Google Drive…</div>
      <div className="check-sub">Looking for a <code>Finance/</code> folder</div>
    </div>
  )
}

function SetupScreen({ reason, driveError, onRefresh }) {
  return (
    <div className="flow-setup">
      <div className="setup-icon">📂</div>
      <h1 className="setup-title">Let's get your files ready</h1>
      <p className="setup-sub">
        {reason === 'no-files'
          ? <>We found your <strong>Finance/</strong> folder, but no CSV files inside it yet. Follow these steps to add some.</>
          : reason === 'error'
            ? <>We ran into a problem checking your Google Drive. This may be temporary — hit <strong>Refresh</strong> to try again, or follow these steps if you haven't set up your <strong>Finance/</strong> folder yet.</>
            : <>We couldn't find a <strong>Finance/</strong> folder in your Google Drive. Follow these steps to set it up — only needed once.</>}
      </p>

      <div className="notice-box">
        <strong>
          {reason === 'no-files' ? '⚠ No CSV files found' : reason === 'error' ? '⚠ Something went wrong' : '⚠ Folder not found'}
        </strong>
        {driveError
          ? driveError
          : reason === 'no-files'
            ? <>Your <code>Finance/</code> folder is empty. Add your CSVs using the steps below, then hit <strong>Refresh</strong>.</>
            : <>No <code>Finance/</code> folder was detected in your Google Drive. Create it using the steps below, then hit <strong>Refresh</strong>.</>}
      </div>

      <div className="steps-list">
        <div className="step-item">
          <div className="step-num-badge">1</div>
          <div className="step-body">
            <h4>Create the folder structure in Google Drive</h4>
            <p>Open Google Drive and create the following folder layout at the root. The app scans exactly these paths to find your CSVs.</p>
            <div className="folder-tree">
              <span className="dir">📁 Finance/</span><br/>
              <span className="dir">├── 📁 Bank/</span><br/>
              <span className="dir">│   └── 📁 Chase/</span><br/>
              <span className="file">│       └── chase_checking_may2025.csv</span><br/>
              <span className="dir">├── 📁 CreditCard/</span><br/>
              <span className="dir">│   ├── 📁 Amex/</span><br/>
              <span className="file">│   │   └── amex_gold_may2025.csv</span><br/>
              <span className="dir">│   └── 📁 Citi/</span><br/>
              <span className="file">│       └── citi_double_may2025.csv</span><br/>
              <span className="dir">└── 📁 Investment/</span><br/>
              <span className="dir">    └── 📁 Fidelity/</span><br/>
              <span className="file">        └── fidelity_may2025.csv</span>
            </div>
          </div>
        </div>

        <div className="step-item">
          <div className="step-num-badge">2</div>
          <div className="step-body">
            <h4>Download CSV exports from your bank</h4>
            <p>Log into each bank's website and export your transaction history as a <strong>.csv</strong> file. Supported: Chase, Amex, Citi, Wells Fargo, Fidelity.</p>
          </div>
        </div>

        <div className="step-item">
          <div className="step-num-badge">3</div>
          <div className="step-body">
            <h4>Upload the CSVs into the matching folders</h4>
            <p>Place each CSV in its institution's folder — e.g. your Chase CSV goes inside <span className="path-chip">Finance/Bank/Chase/</span>. File names don't matter, only the folder structure.</p>
          </div>
        </div>

        <div className="step-item">
          <div className="step-num-badge">4</div>
          <div className="step-body">
            <h4>Come back here and click Refresh</h4>
            <p>Once your files are in place, hit the button below. The app will scan your Drive and build your summary automatically.</p>
          </div>
        </div>
      </div>

      <div className="refresh-cta">
        <p>✅ Already uploaded your files? Click below to load your dashboard.</p>
        <button className="btn-refresh" onClick={onRefresh}>
          🔄 Refresh &amp; Load My Data
        </button>
      </div>
    </div>
  )
}

function CsvPreview({ accessToken, file }) {
  const [content, setContent] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    downloadFileContent(accessToken, file.id)
      .then(text => { if (!cancelled) setContent(text) })
      .catch(err => { if (!cancelled) setError(err.message) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [accessToken, file.id])

  if (loading) return <div className="csv-preview-status">Loading preview…</div>
  if (error) return <div className="csv-preview-status csv-preview-error">Couldn't load file: {error}</div>

  const lines = content.split(/\r\n|\n/)
  const preview = lines.slice(0, 20)
  return (
    <div className="csv-preview">
      <pre className="csv-preview-body">{preview.join('\n')}</pre>
      {lines.length > preview.length && (
        <div className="csv-preview-truncated">Showing first {preview.length} of {lines.length} lines</div>
      )}
    </div>
  )
}

function FileRow({ accessToken, file }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="file-row">
      <div className="file-row-main" onClick={() => setExpanded(e => !e)}>
        <div className="file-row-name">📄 {file.name}</div>
        <div className="file-row-meta">{new Date(file.modifiedTime).toLocaleDateString()}</div>
        <div className="file-row-chevron">{expanded ? '▼' : '▶'}</div>
      </div>
      {expanded && <CsvPreview accessToken={accessToken} file={file} />}
    </div>
  )
}

function FilesScreen({ accessToken, driveFiles, onContinue }) {
  const groups = {}
  for (const file of driveFiles) {
    const key = `${file.accountType} / ${file.institution}`
    if (!groups[key]) groups[key] = []
    groups[key].push(file)
  }

  return (
    <div className="flow-files">
      <h1 className="files-title">Files found in your <em>Finance/</em> folder</h1>
      <p className="files-sub">
        {driveFiles.length} CSV file{driveFiles.length === 1 ? '' : 's'} detected. Click a file to preview its raw contents.
      </p>

      <div className="file-groups">
        {Object.entries(groups).map(([groupName, files]) => (
          <div key={groupName} className="file-group">
            <div className="file-group-title">{groupName}</div>
            {files.map(file => (
              <FileRow key={file.id} accessToken={accessToken} file={file} />
            ))}
          </div>
        ))}
      </div>

      <button className="btn-refresh" onClick={onContinue}>Continue &amp; build summary →</button>
    </div>
  )
}

function pipeStepClass(state) {
  return state === 'done' ? 'done-step' : state === 'active' ? 'active-step' : 'wait-step'
}
function pipeLabelClass(state) {
  return state === 'done' ? 'done-lbl' : state === 'active' ? 'active-lbl' : 'wait-lbl'
}

function ProcessingScreen({ stageIndex, fileCount }) {
  const states = [
    ['done', 'done', 'active', 'wait', 'wait'],
    ['done', 'done', 'done', 'active', 'wait'],
    ['done', 'done', 'done', 'done', 'active'],
    ['done', 'done', 'done', 'done', 'done'],
  ]
  const labelStage = Math.max(0, Math.min(stageIndex, PIPELINE_STAGES(fileCount).length - 1))
  const labels = PIPELINE_STAGES(fileCount)[labelStage]
  const stepStates = states[Math.min(stageIndex, states.length - 1)]

  return (
    <div className="flow-processing">
      <div className="pipeline">
        {stepStates.map((state, i) => (
          <div key={i} className={`pipe-step ${pipeStepClass(state)}`}>
            <div className="pipe-icon">{PIPELINE_ICONS[i]}</div>
            <div className={`pipe-label ${pipeLabelClass(state)}`}>{labels[i]}</div>
            {state === 'done' && <div className="pipe-check">✓</div>}
            {state === 'active' && <div className="pipe-spin"/>}
          </div>
        ))}
      </div>
    </div>
  )
}

function DashboardScreen({ openMonth, setOpenMonth, driveFiles, summary, onRefresh }) {
  const ccSummary = summary?.cc_summary ?? null
  const bankSummary = summary?.bank_summary ?? null
  const warnings = summary?.warnings ?? []

  const ccRows = (ccSummary?.by_card ?? []).map(card => ({
    account: card.name,
    spending: fmtSpending(card.spending),
    credits: fmtCredit(card.credits),
  }))

  // by_bank merges every account under the same institution into one row
  // (it groups by account_name only) — use by_account instead so accounts
  // from the same bank (e.g. two Chase checking CSVs) stay distinguishable,
  // the same way by_card already does for credit cards.
  const bankRows = (bankSummary?.by_account ?? [])
    .map(account => {
      const totals = (account.categories ?? []).reduce(
        (sum, cat) => ({ spending: sum.spending + cat.spending, income: sum.income + cat.income }),
        { spending: 0, income: 0 }
      )
      return {
        account: `${account.account_name} (${account.last4})`,
        income: fmtCredit(totals.income),
        net: fmtAmount(totals.income + totals.spending),
        _spending: totals.spending,
      }
    })
    .sort((a, b) => a._spending - b._spending)

  // Newest month first, to match the original mock's ordering. Kept as the
  // raw monthly_cc entries (not just formatted strings) so the by_card/
  // by_category breakdown is available when a row is expanded below.
  const monthlyCcByRecency = [...(summary?.monthly_cc ?? [])].reverse()
  const monthlyRows = monthlyCcByRecency.map(m => ({
    month: fmtMonthLabel(m.month),
    spending: fmtSpending(m.total_spending),
    credits: fmtCredit(m.total_credits),
    txns: (m.by_card ?? []).reduce((sum, c) => sum + c.transactions, 0),
  }))

  const allMonths = [...(summary?.monthly_cc ?? []), ...(summary?.monthly_bank ?? [])].map(m => m.month)
  const headerLabel = allMonths.length ? fmtMonthLabel([...allMonths].sort().at(-1)) : 'All Time'

  const netCashFlow = (bankSummary?.total_income ?? 0) + (bankSummary?.total_spending ?? 0) + (bankSummary?.total_cc_payments ?? 0)

  return (
    <>
      <div className="dash-topbar">
        <div>
          <h2>{headerLabel} Summary</h2>
          <span>Last updated: just now · {driveFiles.length} file{driveFiles.length === 1 ? '' : 's'} processed</span>
        </div>
        <button className="btn-ref-sm" onClick={onRefresh}>
          🔄 Refresh Drive files
        </button>
      </div>

      {warnings.length > 0 && (
        <div className="notice-box">
          <strong>⚠ Some files were skipped</strong>
          {warnings.join(' · ')}
        </div>
      )}

      <div className="section-title">Overview · {headerLabel}</div>
      <div className="cards">
        <div className="card">
          <div className="label">Net Cash Flow</div>
          <div className={`value ${netCashFlow >= 0 ? 'positive' : 'negative'}`}>{fmtAmount(netCashFlow)}</div>
          <div className="sub">Income − All Spending</div>
        </div>
        <div className="card">
          <div className="label">Credit Card Spending</div>
          <div className="value negative">{fmtSpending(ccSummary?.total_spending ?? 0)}</div>
          <div className="sub">Across {ccSummary?.total_cards ?? 0} card{ccSummary?.total_cards === 1 ? '' : 's'}</div>
        </div>
        <div className="card">
          <div className="label">Bank Income</div>
          <div className="value neutral">{fmtCredit(bankSummary?.total_income ?? 0)}</div>
          <div className="sub">{bankSummary?.total_accounts ?? 0} account{bankSummary?.total_accounts === 1 ? '' : 's'}</div>
        </div>
      </div>

      <div className="section-title">Trends</div>
      <div className="charts">
        <div className="chart-card">
          <h4>Monthly Credit Card Spending</h4>
          <LineChart/>
        </div>
        <div className="chart-card">
          <h4>Spending by Category</h4>
          <PieChart/>
        </div>
      </div>

      <div className="section-title">Account Summary</div>
      <div className="tables">
        <div className="table-card">
          <h4>Credit Cards</h4>
          <table>
            <thead>
              <tr><th>Account</th><th>Spending</th><th>Credits</th></tr>
            </thead>
            <tbody>
              {ccRows.length === 0 && (
                <tr><td colSpan={3} className="empty-row">No credit card files found</td></tr>
              )}
              {ccRows.map(row => (
                <tr key={row.account}>
                  <td>{row.account}</td>
                  <td className="amount-neg">{row.spending}</td>
                  <td className="amount-pos">{row.credits}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="table-card">
          <h4>Bank Accounts</h4>
          <table>
            <thead>
              <tr><th>Account</th><th>Income</th><th>Net Flow</th></tr>
            </thead>
            <tbody>
              {bankRows.length === 0 && (
                <tr><td colSpan={3} className="empty-row">No bank account files found</td></tr>
              )}
              {bankRows.map(row => (
                <tr key={row.account}>
                  <td>{row.account}</td>
                  <td className="amount-pos">{row.income}</td>
                  <td className={row.net.startsWith('-') ? 'amount-neg' : 'amount-pos'}>{row.net}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="section-title">Monthly Breakdown</div>
      <div className="monthly-card">
        <h4>Credit Card · Monthly Detail</h4>
        {monthlyRows.length === 0 && <div className="empty-row">No credit card transactions found</div>}
        {monthlyRows.map((row, i) => {
          const isOpen = openMonth === i
          const monthDetail = monthlyCcByRecency[i]
          return (
            <div key={row.month}>
              <div className="month-row" onClick={() => setOpenMonth(isOpen ? null : i)}>
                <div className="month-name">{row.month}</div>
                <div className="month-stats">
                  <div className="month-stat">
                    <div className="stat-label">Spending</div>
                    <div className="stat-value amount-neg">{row.spending}</div>
                  </div>
                  <div className="month-stat">
                    <div className="stat-label">Credits</div>
                    <div className="stat-value amount-pos">{row.credits}</div>
                  </div>
                  <div className="month-stat">
                    <div className="stat-label">Transactions</div>
                    <div className="stat-value">{row.txns}</div>
                  </div>
                </div>
                <div className="chevron">{isOpen ? '▼' : '▶'}</div>
              </div>
              {isOpen && (
                <div className="month-detail">
                  <div className="month-detail-cols">
                    <div className="month-detail-col">
                      <h5>By Card</h5>
                      <table>
                        <thead>
                          <tr><th>Card</th><th>Txns</th><th>Spending</th><th>Credits</th></tr>
                        </thead>
                        <tbody>
                          {(monthDetail.by_card ?? []).map(card => (
                            <tr key={card.name}>
                              <td>{card.name}</td>
                              <td>{card.transactions}</td>
                              <td className="amount-neg">{fmtSpending(card.spending)}</td>
                              <td className="amount-pos">{fmtCredit(card.credits)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="month-detail-col">
                      <h5>By Category</h5>
                      <table>
                        <thead>
                          <tr><th>Category</th><th>Txns</th><th>Spending</th><th>Credits</th></tr>
                        </thead>
                        <tbody>
                          {(monthDetail.by_category ?? []).map(cat => (
                            <tr key={cat.category}>
                              <td>{cat.category}</td>
                              <td>{cat.count}</td>
                              <td className="amount-neg">{fmtSpending(cat.spending)}</td>
                              <td className="amount-pos">{fmtCredit(cat.credits)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </>
  )
}

function ProcessingErrorScreen({ error, onRetry }) {
  return (
    <div className="flow-setup">
      <div className="setup-icon">⚠️</div>
      <h1 className="setup-title">Couldn't build your summary</h1>
      <p className="setup-sub">Something went wrong while parsing your CSVs in the browser.</p>
      <div className="notice-box">
        <strong>⚠ Processing error</strong>
        {error}
      </div>
      <div className="refresh-cta">
        <button className="btn-refresh" onClick={onRetry}>🔄 Try again</button>
      </div>
    </div>
  )
}

export default function App() {
  const { accessToken, profile, error, signIn, signOut } = useGoogleAuth()
  const [openMonth, setOpenMonth] = useState(0)

  // 'landing' | 'checking' | 'setup' | 'files' | 'processing' | 'processing-error' | 'dashboard'
  const [screen, setScreen] = useState(accessToken ? 'checking' : 'landing')
  const [setupReason, setSetupReason] = useState(null) // 'no-folder' | 'no-files' | 'error'
  const [driveFiles, setDriveFiles] = useState([])
  const [driveError, setDriveError] = useState(null)
  const [stageIndex, setStageIndex] = useState(0)
  const [summary, setSummary] = useState(null)
  const [pipelineError, setPipelineError] = useState(null)
  const pipelineTimer = useRef(null)

  // async：这个函式里面有要等待的事（找 Finance 资料夹、找档案都要等 Drive API 回应）。
  // await：每一行 await 都是「先等这行做完，才做下一行」；中间任何一步失败，
  // 都会跳进下面的 catch。
  const checkDrive = async (token) => {
    setScreen('checking')
    setDriveError(null)
    try {
      const folderId = await findFinanceFolder(token)
      if (!folderId) {
        setSetupReason('no-folder')
        setScreen('setup')
        return
      }
      const files = await listFinanceFiles(token, folderId)
      if (files.length === 0) {
        setDriveFiles([])
        setSetupReason('no-files')
        setScreen('setup')
        return
      }
      setDriveFiles(files)
      setScreen('files')
    } catch (err) {
      setDriveError(err.message)
      setSetupReason('error')
      setScreen('setup')
    }
  }

  // Real pipeline: download each CSV's content from Drive, hand it to the
  // Python engine running in Pyodide (multi_account_summarizer/browser_api.py),
  // and show whatever it computes — no more fake timers.
  const runPipeline = async () => {
    setScreen('processing')
    setStageIndex(0)
    setPipelineError(null)
    try {
      setStageIndex(1)
      const files = await Promise.all(
        driveFiles.map(async (file) => ({
          accountType: file.accountType,
          institution: file.institution,
          name: file.name,
          content: await downloadFileContent(accessToken, file.id),
        }))
      )

      setStageIndex(2)
      const result = await runSummarizer(files)

      setStageIndex(3)
      setSummary(result)
      pipelineTimer.current = setTimeout(() => setScreen('dashboard'), 600)
    } catch (err) {
      setPipelineError(err.message)
      setScreen('processing-error')
    }
  }

  // The Pyodide runtime is several MB and slow to cold-start — start loading
  // it in the background as soon as the user can see their files, so it's
  // likely already warm by the time they click "Continue."
  useEffect(() => {
    if (screen === 'files') prefetchPyodide()
  }, [screen])

  useEffect(() => {
    if (accessToken) {
      checkDrive(accessToken)
    } else {
      setScreen('landing')
      setDriveFiles([])
      setDriveError(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken])

  useEffect(() => () => clearTimeout(pipelineTimer.current), [])

  const handleSignOut = () => {
    clearTimeout(pipelineTimer.current)
    signOut()
  }

  const handleRefresh = () => {
    if (accessToken) checkDrive(accessToken)
  }

  if (screen === 'landing') {
    return <LandingScreen onSignIn={signIn} error={error} />
  }

  return (
    <>
      <AppNav profile={profile} onSignOut={handleSignOut} />
      <main>
        {screen === 'checking' && <CheckingScreen />}
        {screen === 'setup' && (
          <SetupScreen
            reason={setupReason}
            driveError={driveError}
            onRefresh={handleRefresh}
          />
        )}
        {screen === 'files' && (
          <FilesScreen
            accessToken={accessToken}
            driveFiles={driveFiles}
            onContinue={runPipeline}
          />
        )}
        {screen === 'processing' && (
          <ProcessingScreen stageIndex={stageIndex} fileCount={driveFiles.length} />
        )}
        {screen === 'processing-error' && (
          <ProcessingErrorScreen error={pipelineError} onRetry={runPipeline} />
        )}
        {screen === 'dashboard' && (
          <DashboardScreen
            openMonth={openMonth}
            setOpenMonth={setOpenMonth}
            driveFiles={driveFiles}
            summary={summary}
            onRefresh={handleRefresh}
          />
        )}
      </main>
    </>
  )
}

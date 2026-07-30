import { useEffect, useRef, useState } from 'react'
import './App.css'
import { useGoogleAuth } from './hooks/useGoogleAuth'
import { readCsvFile } from './utils/parseCsv'
import { findOrCreateFinanceFolder, listFinanceFiles } from './utils/driveApi'
import { pickFinanceFolder } from './utils/googlePicker'

const FOLDER_STORAGE_KEY = 'financeFolder'

const CC_ROWS = [
  { account: 'Chase Sapphire ···4521', spending: '−$980.20',  credits: '+$200.00' },
  { account: 'Amex Gold ···8834',      spending: '−$760.30',  credits: '+$0.00'   },
  { account: 'Citi Double ···1209',    spending: '−$600.00',  credits: '+$50.00'  },
]

const BANK_ROWS = [
  { account: 'Chase Checking ···6789',  income: '+$4,300.00', net: '+$890.50' },
  { account: 'Wells Fargo ···3312',     income: '+$1,500.00', net: '+$379.20' },
]

const MONTHLY_ROWS = [
  { month: 'May 2025', spending: '−$2,340', credits: '+$250', txns: 47, open: true  },
  { month: 'Apr 2025', spending: '−$2,890', credits: '+$100', txns: 53, open: false },
  { month: 'Mar 2025', spending: '−$1,650', credits: '+$0',   txns: 38, open: false },
]

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

export default function App() {
  const [openMonth, setOpenMonth] = useState(0)
  const { accessToken, profile, error, signIn, signOut, isSignedIn } = useGoogleAuth()
  const fileInputRef = useRef(null)
  const [uploadedFiles, setUploadedFiles] = useState([])
  const [uploadError, setUploadError] = useState(null)

  const [driveFiles, setDriveFiles] = useState([])
  const [driveLoading, setDriveLoading] = useState(false)
  const [driveError, setDriveError] = useState(null)
  const [driveFetched, setDriveFetched] = useState(false)
  const [pendingAction, setPendingAction] = useState(null) // null | 'connect' | 'change'
  const [financeFolder, setFinanceFolder] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(FOLDER_STORAGE_KEY))
    } catch {
      return null
    }
  })

  const handleFilesSelected = async (event) => {
    const files = Array.from(event.target.files)
    event.target.value = '' // allow re-selecting the same file later
    if (files.length === 0) return

    setUploadError(null)
    try {
      const summaries = await Promise.all(files.map(readCsvFile))
      setUploadedFiles(prev => [...prev, ...summaries])
    } catch (err) {
      setUploadError(err.message)
    }
  }

  const fetchDriveFiles = async (folderIdOverride) => {
    setDriveLoading(true)
    setDriveError(null)
    try {
      const folderId = folderIdOverride || financeFolder?.id || (await findOrCreateFinanceFolder(accessToken))
      const files = await listFinanceFiles(accessToken, folderId)
      setDriveFiles(files)
      setDriveFetched(true)
    } catch (err) {
      setDriveError(err.message)
    } finally {
      setDriveLoading(false)
    }
  }

  const chooseFolder = async (token) => {
    setDriveError(null)
    try {
      const folder = await pickFinanceFolder(token)
      if (!folder) return
      localStorage.setItem(FOLDER_STORAGE_KEY, JSON.stringify(folder))
      setFinanceFolder(folder)
      fetchDriveFiles(folder.id)
    } catch (err) {
      setDriveError(err.message)
    }
  }

  // Single Drive entry point: picks a folder the first time, then just
  // refreshes from the already-chosen folder on subsequent clicks.
  const connectDrive = () => {
    if (financeFolder) {
      fetchDriveFiles()
    } else {
      chooseFolder(accessToken)
    }
  }

  const handleDriveButtonClick = () => {
    if (!isSignedIn) {
      setPendingAction('connect')
      signIn()
      return
    }
    connectDrive()
  }

  const handleChangeFolder = () => {
    if (!isSignedIn) {
      setPendingAction('change')
      signIn()
      return
    }
    chooseFolder(accessToken)
  }

  useEffect(() => {
    if (isSignedIn && pendingAction) {
      const action = pendingAction
      setPendingAction(null)
      if (action === 'change') chooseFolder(accessToken)
      else connectDrive()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isSignedIn, pendingAction])

  return (
    <>
      <nav>
        <div className="logo">Finance<span>Dashboard</span></div>
        {isSignedIn ? (
          <div className="google-account">
            {profile?.picture && <img className="google-avatar" src={profile.picture} alt=""/>}
            <span className="google-email">{profile?.email}</span>
            <button className="btn btn-google" onClick={signOut}>Sign out</button>
          </div>
        ) : (
          <button className="btn btn-google" onClick={signIn}>
            <div className="google-icon"/>
            Sign in with Google
          </button>
        )}
      </nav>
      {error && <div className="google-auth-error">{error}</div>}

      <main>

        {/* Upload Zone */}
        <div className="upload-zone">
          <div className="upload-icon">📂</div>
          <h3>Upload your bank / credit card statements</h3>
          <p>Supports Chase, Amex, Citi, Wells Fargo — CSV format</p>
          <div className="upload-actions">
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              multiple
              hidden
              onChange={handleFilesSelected}
            />
            <button className="btn btn-primary" onClick={() => fileInputRef.current.click()}>
              ⬆ Upload CSV files
            </button>
            <button className="btn btn-secondary" onClick={handleDriveButtonClick} disabled={driveLoading}>
              {driveLoading
                ? 'Connecting…'
                : financeFolder ? '🔄 Refresh Drive files' : '📁 Connect Google Drive'}
            </button>
          </div>
          {financeFolder && (
            <p className="upload-hint">
              Finance folder: <strong>{financeFolder.name}</strong>{' '}
              <button className="link-btn" onClick={handleChangeFolder} disabled={driveLoading}>Change</button>
            </p>
          )}
          {uploadError && <div className="upload-error">{uploadError}</div>}
          {uploadedFiles.length > 0 && (
            <ul className="upload-preview-list">
              {uploadedFiles.map((f, i) => (
                <li key={`${f.fileName}-${i}`}>
                  <span className="upload-file-name">{f.fileName}</span>
                  <span className="upload-file-meta">
                    {f.rowCount} rows · {f.headers.length} columns
                  </span>
                </li>
              ))}
            </ul>
          )}
          {driveError && <div className="upload-error">{driveError}</div>}
          {driveFiles.length > 0 && (
            <ul className="upload-preview-list">
              {driveFiles.map(f => (
                <li key={f.id}>
                  <span className="upload-file-name">{f.accountType} / {f.institution} / {f.name}</span>
                  <span className="upload-file-meta">
                    {new Date(f.modifiedTime).toLocaleDateString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {driveFetched && !driveError && driveFiles.length === 0 && (
            <p className="upload-hint">
              Connected — no CSVs found yet. Drop files into your Drive's
              Finance/Bank (or CreditCard/Investment)/&lt;institution&gt; folders, then Connect again.
            </p>
          )}
        </div>

        {/* Summary Cards */}
        <div className="section-title">Overview · May 2025</div>
        <div className="cards">
          <div className="card">
            <div className="label">Net Cash Flow</div>
            <div className="value positive">+$1,269.70</div>
            <div className="sub">Income − All Spending</div>
          </div>
          <div className="card">
            <div className="label">Credit Card Spending</div>
            <div className="value negative">−$2,340.50</div>
            <div className="sub">Across 3 cards</div>
          </div>
          <div className="card">
            <div className="label">Bank Income</div>
            <div className="value neutral">$5,800.00</div>
            <div className="sub">2 accounts</div>
          </div>
        </div>

        {/* Charts */}
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

        {/* Account Tables */}
        <div className="section-title">Account Summary</div>
        <div className="tables">
          <div className="table-card">
            <h4>Credit Cards</h4>
            <table>
              <thead>
                <tr><th>Account</th><th>Spending</th><th>Credits</th></tr>
              </thead>
              <tbody>
                {CC_ROWS.map(row => (
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
                {BANK_ROWS.map(row => (
                  <tr key={row.account}>
                    <td>{row.account}</td>
                    <td className="amount-pos">{row.income}</td>
                    <td className="amount-pos">{row.net}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Monthly Breakdown */}
        <div className="section-title">Monthly Breakdown</div>
        <div className="monthly-card">
          <h4>Credit Card · Monthly Detail</h4>
          {MONTHLY_ROWS.map((row, i) => (
            <div key={row.month} className="month-row" onClick={() => setOpenMonth(i)}>
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
              <div className="chevron">{openMonth === i ? '▼' : '▶'}</div>
            </div>
          ))}
        </div>

      </main>
    </>
  )
}

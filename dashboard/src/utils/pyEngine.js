// Runs the real multi_account_summarizer Python package inside the browser
// via Pyodide (Python compiled to WebAssembly) — no backend involved. The
// site is a static GitHub Pages deploy, so this keeps CSV parsing entirely
// client-side while reusing the existing, tested Python parsers/calculators
// unchanged (see ../../../multi_account_summarizer/browser_api.py).
//
// Why anything gets "written" at all: Pyodide's Python runs inside a WASM
// sandbox and can only read data through its own virtual filesystem
// (Emscripten's MEMFS) — an in-memory filesystem that lives entirely inside
// this browser tab's memory. It is NOT the user's real disk, nothing here
// is ever saved/persisted anywhere, and the CSV half of it is wiped and
// rewritten on every single run (see resetCsvInputDir). We can't hand a JS
// string straight to Python's open() across the JS↔WASM boundary, and the
// existing parsers (parsers/*.py, unchanged from the CLI tool) do call
// open(file_path) — so "write into MEMFS, then let unchanged Python code
// open() it" is the mechanism, not a design choice to persist anything.
// The package's own .py source needs the same treatment for the same
// reason: `import parsers.chase_cc` only works if those files exist
// somewhere on Pyodide's sys.path inside that same virtual filesystem.

// Bundles every .py source file as raw text at build time — single source
// of truth, no copy step. Skips tests/ since it's dev-only, never executed.
const RAW_PY_SOURCES = import.meta.glob('../../../multi_account_summarizer/**/*.py', {
  query: '?raw',
  import: 'default',
  eager: true,
})

const PACKAGE_MARKER = 'multi_account_summarizer/'
const PY_LIB_ROOT = '/lib'         // where the package's .py source lives in Pyodide's FS
const CSV_INPUT_DIR = '/csv_input' // where the current run's downloaded CSVs live in Pyodide's FS

let pyodidePromise = null
let pyodideInstance = null // set once loadPyodideRuntime() resolves — lets clearCsvData() check synchronously without forcing a load
let sourcesWritten = false

// import.meta.glob's keys are the literal relative path from the glob
// pattern (e.g. "../../../multi_account_summarizer/parsers/chase_cc.py").
// Strip everything through the package name to get the path we want inside
// Pyodide's FS (e.g. "parsers/chase_cc.py") — kept as its own pure function
// so it's testable without touching Pyodide at all.
export function relPathFromGlobKey(key) {
  return key.slice(key.indexOf(PACKAGE_MARKER) + PACKAGE_MARKER.length)
}

// Drive folder names (accountType/institution) are free text the user
// typed when creating their Finance/ folder structure — could contain
// slashes or other characters that aren't safe as a virtual FS path
// segment. Filenames themselves aren't sanitized: they're expected to
// already be safe CSV filenames per the AccountName_1234.csv convention.
export function sanitizePathSegment(name) {
  return (name || 'unknown').replace(/[^a-zA-Z0-9 _-]/g, '_')
}

// Where a given Drive file lands inside Pyodide's FS: nested under its
// accountType/institution, mirroring Drive's own Finance/<accountType>/
// <institution>/ layout, with the real filename kept as-is (the last4 in
// e.g. "Chase_Sapphire_4521.csv" is real user data, not something we
// should replace). browser_api.summarize_folder() scans recursively
// (Path.rglob), so this nesting also sidesteps same-name collisions
// between files from different institutions/account types.
export function csvFileDestPath({ accountType, institution, name }) {
  return `${CSV_INPUT_DIR}/${sanitizePathSegment(accountType)}/${sanitizePathSegment(institution)}/${name}`
}

// Loads the actual Pyodide WASM runtime — the Python interpreter itself
// (several MB the first time). Dynamic import: Pyodide is excluded from
// esbuild's dep pre-bundling (see vite.config.js) and fetches its own
// wasm/stdlib assets at runtime, relative to indexURL.
function loadPyodideRuntime() {
  return import('pyodide').then(({ loadPyodide }) =>
    loadPyodide({ indexURL: `${import.meta.env.BASE_URL}pyodide/` })
  )
}

// Memoized so the (slow) runtime is only ever loaded once per browser tab,
// no matter how many times prefetchPyodide()/runSummarizer() are called.
function getPyodide() {
  if (!pyodidePromise) {
    pyodidePromise = loadPyodideRuntime().then(pyodide => {
      pyodideInstance = pyodide
      return pyodide
    })
  }
  return pyodidePromise
}

// Kick off the (slow, multi-MB) first-time Pyodide load in the background
// so it's likely already warm by the time the user clicks "Continue" and
// runSummarizer() actually needs it. Safe to call more than once and safe
// to ignore its rejection here — the real error surfaces from
// runSummarizer()'s own await.
export function prefetchPyodide() {
  getPyodide().catch(() => {})
}

// Writes multi_account_summarizer's own .py files into Pyodide's virtual
// filesystem so `import browser_api` (and everything it in turn imports)
// can find them — Python's import system only looks at real files on
// sys.path, it can't import from a JS string held in memory. Guarded by
// sourcesWritten because the package's source code never changes mid
// session; only the CSV input changes on every run (see writeCsvFiles),
// so re-writing ~15 unchanged files on every "Refresh" would be wasted work.
export function writeSourcesOnce(pyodide) {
  if (sourcesWritten) return
  for (const [key, source] of Object.entries(RAW_PY_SOURCES)) {
    const relPath = relPathFromGlobKey(key)
    if (relPath.startsWith('tests/')) continue

    const destPath = `${PY_LIB_ROOT}/${relPath}`
    const destDir = destPath.slice(0, destPath.lastIndexOf('/'))
    pyodide.FS.mkdirTree(destDir)
    pyodide.FS.writeFile(destPath, source)
  }
  pyodide.runPython(
    `import sys\nif "${PY_LIB_ROOT}" not in sys.path:\n    sys.path.insert(0, "${PY_LIB_ROOT}")`
  )
  sourcesWritten = true
}

// Emscripten's MEMFS has no "rm -rf" — deleting a non-empty directory
// means deleting its contents first. Used by resetCsvInputDir to fully
// clear out the previous run's CSVs.
export function removeRecursively(pyodide, dirPath) {
  for (const name of pyodide.FS.readdir(dirPath)) {
    if (name === '.' || name === '..') continue
    const childPath = `${dirPath}/${name}`
    if (pyodide.FS.isDir(pyodide.FS.stat(childPath).mode)) {
      removeRecursively(pyodide, childPath)
      pyodide.FS.rmdir(childPath)
    } else {
      pyodide.FS.unlink(childPath)
    }
  }
}

// Wipes /csv_input before writing the current run's files. This matters
// because Pyodide (and its virtual filesystem) stay alive for the whole
// browser tab session — runSummarizer() is called again every time the
// user hits "Refresh Drive files," reusing the same warm Pyodide instance
// rather than reloading the multi-MB runtime from scratch. Without this
// reset, a file removed or renamed in Drive since the last run would still
// be sitting in the FS and get silently included in the new summary
// alongside the current files (see pyEngine.test.js for a regression test
// that reproduces exactly this if the reset is skipped).
export function resetCsvInputDir(pyodide) {
  pyodide.FS.mkdirTree(CSV_INPUT_DIR)
  removeRecursively(pyodide, CSV_INPUT_DIR)
}

// Wipes any CSV content currently sitting in Pyodide's FS — call this on
// sign-out so a signed-out user's transaction data doesn't linger in memory
// (nothing here was ever written to real disk, but it does stay in this
// tab's memory until the tab itself closes/reloads; see App.jsx's
// handleSignOut). Deliberately synchronous and a no-op if Pyodide was never
// loaded or hasn't finished loading yet — there's nothing to clear in that
// case, and this must never trigger a fresh (slow) Pyodide load just to
// immediately wipe an empty directory.
//
// Defaults to the instance getPyodide() has already resolved (the real
// call site, App.jsx), but accepts an explicit pyodide so it can be tested
// directly against a real instance without going through getPyodide()'s
// browser-only indexURL.
export function clearCsvData(pyodide = pyodideInstance) {
  if (pyodide) {
    resetCsvInputDir(pyodide)
  }
}

// files: [{ accountType, institution, name, content }] — name/content are
// the Drive file's real name and raw CSV text (see driveApi.js:
// listFinanceFiles / downloadFileContent).
export function writeCsvFiles(pyodide, files) {
  resetCsvInputDir(pyodide)
  for (const file of files) {
    const destPath = csvFileDestPath(file)
    const destDir = destPath.slice(0, destPath.lastIndexOf('/'))
    pyodide.FS.mkdirTree(destDir)
    pyodide.FS.writeFile(destPath, file.content)
  }
}

// The actual summarize step, decoupled from getPyodide()'s browser-only
// indexURL so it can be exercised directly against a Pyodide instance
// created any way the caller likes (e.g. tests loading the local
// node_modules/pyodide copy instead of fetching over HTTP).
export async function runSummarizerWithPyodide(pyodide, files) {
  writeSourcesOnce(pyodide)
  writeCsvFiles(pyodide, files)

  try {
    const resultJson = pyodide.runPython(
      `import browser_api\nbrowser_api.summarize_folder_json("${CSV_INPUT_DIR}")`
    )
    return JSON.parse(resultJson)
  } finally {
    // The raw CSVs (every transaction's date/description/amount) are only
    // ever needed for this brief parse — once summarize_folder_json() has
    // produced the aggregated summary, nothing else reads them again.
    // Wipe them immediately (success or failure) rather than leaving them
    // sitting in Pyodide's FS for the rest of the browsing session; only
    // clearCsvData() on sign-out (App.jsx) would otherwise ever clear them,
    // which could be minutes or hours later.
    resetCsvInputDir(pyodide)
  }
}

// Returns the parsed summary payload:
// { cc_summary, monthly_cc, bank_summary, monthly_bank, warnings }.
export async function runSummarizer(files) {
  const pyodide = await getPyodide()
  return runSummarizerWithPyodide(pyodide, files)
}

// Runs the real multi_account_summarizer Python package inside the browser
// via Pyodide (Python compiled to WebAssembly) — no backend involved. The
// site is a static GitHub Pages deploy, so this keeps CSV parsing entirely
// client-side while reusing the existing, tested Python parsers/calculators
// unchanged (see ../../../multi_account_summarizer/browser_api.py).

// Bundles every .py source file as raw text at build time — single source
// of truth, no copy step. Skips tests/ since it's dev-only, never executed.
const RAW_PY_SOURCES = import.meta.glob('../../../multi_account_summarizer/**/*.py', {
  query: '?raw',
  import: 'default',
  eager: true,
})

const PACKAGE_MARKER = 'multi_account_summarizer/'
const PY_LIB_ROOT = '/lib'
const CSV_INPUT_DIR = '/csv_input'

let pyodidePromise = null
let sourcesWritten = false

function loadPyodideRuntime() {
  // Dynamic import: Pyodide is excluded from esbuild's dep pre-bundling
  // (see vite.config.js) and fetches its own wasm/stdlib assets at runtime.
  return import('pyodide').then(({ loadPyodide }) =>
    loadPyodide({ indexURL: `${import.meta.env.BASE_URL}pyodide/` })
  )
}

function getPyodide() {
  if (!pyodidePromise) {
    pyodidePromise = loadPyodideRuntime()
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

function writeSourcesOnce(pyodide) {
  if (sourcesWritten) return
  for (const [key, source] of Object.entries(RAW_PY_SOURCES)) {
    const relPath = key.slice(key.indexOf(PACKAGE_MARKER) + PACKAGE_MARKER.length)
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

function removeRecursively(pyodide, dirPath) {
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

function resetCsvInputDir(pyodide) {
  pyodide.FS.mkdirTree(CSV_INPUT_DIR)
  removeRecursively(pyodide, CSV_INPUT_DIR)
}

function sanitizePathSegment(name) {
  return (name || 'unknown').replace(/[^a-zA-Z0-9 _-]/g, '_')
}

// Mirrors Drive's own Finance/<accountType>/<institution>/ layout inside
// Pyodide's FS and keeps each file's real name — the naming convention
// (AccountName_1234.csv) is enforced when uploading to Drive, so the real
// last4 in the filename should be preserved rather than replaced.
// browser_api.summarize_folder() scans recursively (Path.rglob), so nesting
// by folder here also sidesteps same-name collisions across institutions.
function writeCsvFiles(pyodide, files) {
  resetCsvInputDir(pyodide)
  for (const { accountType, institution, name, content } of files) {
    const dir = `${CSV_INPUT_DIR}/${sanitizePathSegment(accountType)}/${sanitizePathSegment(institution)}`
    pyodide.FS.mkdirTree(dir)
    pyodide.FS.writeFile(`${dir}/${name}`, content)
  }
}

// files: [{ accountType, institution, name, content }] — name/content are
// the Drive file's real name and raw CSV text (see driveApi.js:
// listFinanceFiles / downloadFileContent). Returns the parsed summary
// payload: { cc_summary, monthly_cc, bank_summary, monthly_bank, warnings }.
export async function runSummarizer(files) {
  const pyodide = await getPyodide()

  writeSourcesOnce(pyodide)
  writeCsvFiles(pyodide, files)

  const resultJson = pyodide.runPython(
    `import browser_api\nbrowser_api.summarize_folder_json("${CSV_INPUT_DIR}")`
  )
  return JSON.parse(resultJson)
}

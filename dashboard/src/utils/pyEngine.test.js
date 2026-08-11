import { fileURLToPath } from 'node:url'
import { beforeAll, describe, expect, it } from 'vitest'

import {
  clearCsvData,
  csvFileDestPath,
  relPathFromGlobKey,
  removeRecursively,
  resetCsvInputDir,
  runSummarizerWithPyodide,
  sanitizePathSegment,
  writeCsvFiles,
  writeSourcesOnce,
} from './pyEngine.js'

// runSummarizer()'s own getPyodide() points indexURL at a same-origin HTTP
// path (`${BASE_URL}pyodide/`), which only makes sense once this is served
// by a browser/dev server. For these tests we load the exact same local
// Pyodide package a different way — pointing indexURL at the on-disk
// node_modules/pyodide/ directory — and then drive the rest of pyEngine.js
// (writeSourcesOnce, writeCsvFiles, runSummarizerWithPyodide, ...) exactly
// as the browser would, against that real instance. This is the same
// technique used to manually verify browser_api.py under the real Pyodide
// WASM runtime before this PR; it's just now a committed, repeatable test.
const PYODIDE_DIR = fileURLToPath(new URL('../../node_modules/pyodide/', import.meta.url))

let pyodide

beforeAll(async () => {
  const { loadPyodide } = await import('pyodide')
  pyodide = await loadPyodide({ indexURL: PYODIDE_DIR })
})

const CHASE_CC_CSV =
  'Transaction Date,Post Date,Description,Category,Type,Amount,Memo\n' +
  '01/05/2024,01/06/2024,Amazon,Shopping,Sale,-50.00,\n' +
  '01/20/2024,01/21/2024,Payment,Payment,Payment,200.00,\n'

const chaseBankCsv = (amount, description) =>
  'Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #\n' +
  `DEBIT,01/10/2024,${description},${amount},ACH_DEBIT,1000.00,\n`

describe('sanitizePathSegment', () => {
  it('keeps alphanumerics, spaces, underscores, and hyphens as-is', () => {
    expect(sanitizePathSegment('Chase Bank_1')).toBe('Chase Bank_1')
  })

  it('replaces characters that are unsafe as a virtual FS path segment', () => {
    expect(sanitizePathSegment('Chase/Bank')).toBe('Chase_Bank')
  })

  it('falls back to "unknown" for empty/missing input', () => {
    expect(sanitizePathSegment('')).toBe('unknown')
    expect(sanitizePathSegment(undefined)).toBe('unknown')
  })
})

describe('relPathFromGlobKey', () => {
  it('strips everything through the package name', () => {
    expect(relPathFromGlobKey('../../../multi_account_summarizer/parsers/chase_cc.py'))
      .toBe('parsers/chase_cc.py')
  })
})

describe('csvFileDestPath', () => {
  it('nests under sanitized accountType/institution and keeps the real filename', () => {
    expect(csvFileDestPath({
      accountType: 'Bank', institution: 'Chase', name: 'Chase_Checking_6789.csv',
    })).toBe('/csv_input/Bank/Chase/Chase_Checking_6789.csv')
  })
})

describe('removeRecursively + resetCsvInputDir', () => {
  it('clears out nested files and directories, not just top-level ones', () => {
    pyodide.FS.mkdirTree('/scratch/a/b')
    pyodide.FS.writeFile('/scratch/a/b/leaf.txt', 'x')
    pyodide.FS.writeFile('/scratch/top.txt', 'x')

    removeRecursively(pyodide, '/scratch')

    expect(pyodide.FS.readdir('/scratch')).toEqual(['.', '..'])
  })

  it('resetCsvInputDir empties /csv_input even when files were left by a previous run', () => {
    pyodide.FS.mkdirTree('/csv_input/Bank/Chase')
    pyodide.FS.writeFile('/csv_input/Bank/Chase/stale.csv', 'x')

    resetCsvInputDir(pyodide)

    expect(pyodide.FS.readdir('/csv_input')).toEqual(['.', '..'])
  })
})

// Regression coverage for App.jsx's handleSignOut: signing out revokes the
// Google token, but without an explicit clear, a signed-out user's CSV data
// would keep sitting in Pyodide's FS (which stays alive for the whole tab
// session) until the tab itself closes or reloads.
describe('clearCsvData', () => {
  it('wipes CSV content out of the given Pyodide instance', () => {
    pyodide.FS.mkdirTree('/csv_input/Bank/Chase')
    pyodide.FS.writeFile('/csv_input/Bank/Chase/Chase_Checking_6789.csv', 'x')

    clearCsvData(pyodide)

    expect(pyodide.FS.readdir('/csv_input')).toEqual(['.', '..'])
  })

  it('is a no-op instead of forcing a Pyodide load when nothing has loaded yet', () => {
    // Called with no argument, it falls back to the module-level instance
    // that only getPyodide() (App.jsx's real code path) ever sets — this
    // test file drives Pyodide directly and never calls getPyodide(), so
    // that fallback is still unset here. Must not throw.
    expect(() => clearCsvData()).not.toThrow()
  })
})

describe('writeSourcesOnce', () => {
  it('makes browser_api importable from Pyodide', () => {
    writeSourcesOnce(pyodide)
    // Should not raise — proves the package's .py files landed on sys.path
    // with their package structure (parsers/, calculators/) intact.
    pyodide.runPython('import browser_api')
  })

  it('is safe to call again (idempotent, does not re-throw or re-import-fail)', () => {
    expect(() => writeSourcesOnce(pyodide)).not.toThrow()
  })
})

describe('writeCsvFiles', () => {
  it('writes files nested by accountType/institution using their real names', () => {
    writeCsvFiles(pyodide, [
      { accountType: 'CreditCard', institution: 'Chase', name: 'Chase_Sapphire_4521.csv', content: CHASE_CC_CSV },
    ])

    const content = pyodide.FS.readFile('/csv_input/CreditCard/Chase/Chase_Sapphire_4521.csv', { encoding: 'utf8' })
    expect(content).toBe(CHASE_CC_CSV)
  })
})

describe('runSummarizerWithPyodide', () => {
  it('extracts the real last4 from AccountName_1234.csv filenames', async () => {
    const result = await runSummarizerWithPyodide(pyodide, [
      { accountType: 'CreditCard', institution: 'Chase', name: 'Chase_Sapphire_4521.csv', content: CHASE_CC_CSV },
    ])
    expect(result.cc_summary.by_card[0].name).toBe('Chase Sapphire (4521)')
  })

  // The raw CSVs (every transaction's date/description/amount) are only
  // needed for this one parse — once the aggregated summary is back, they
  // should be gone immediately rather than sitting around until the next
  // run or sign-out clears them.
  it('wipes /csv_input immediately after producing the summary', async () => {
    await runSummarizerWithPyodide(pyodide, [
      { accountType: 'CreditCard', institution: 'Chase', name: 'Chase_Sapphire_4521.csv', content: CHASE_CC_CSV },
    ])
    expect(pyodide.FS.readdir('/csv_input')).toEqual(['.', '..'])
  })

  it('still wipes /csv_input even if summarizing throws', async () => {
    // Real FS, but a Python execution step that fails — proves the cleanup
    // is a try/finally, not just code that happens to run on the happy path.
    const throwingPyodide = { FS: pyodide.FS, runPython: () => { throw new Error('boom') } }

    await expect(
      runSummarizerWithPyodide(throwingPyodide, [
        { accountType: 'Bank', institution: 'Chase', name: 'Chase_Checking_6789.csv', content: chaseBankCsv('-1.00', 'X') },
      ])
    ).rejects.toThrow('boom')

    expect(pyodide.FS.readdir('/csv_input')).toEqual(['.', '..'])
  })

  it('keeps two accounts from the same institution distinct instead of merging them', async () => {
    const result = await runSummarizerWithPyodide(pyodide, [
      { accountType: 'Bank', institution: 'Chase', name: 'Chase_Checking_6789.csv', content: chaseBankCsv('-82.30', 'SAFEWAY') },
      { accountType: 'Bank', institution: 'Chase', name: 'Chase_Savings_1122.csv', content: chaseBankCsv('12.40', 'INTEREST') },
    ])
    const last4s = new Set(result.bank_summary.by_account.map(a => a.last4))
    expect(last4s).toEqual(new Set(['6789', '1122']))
  })

  // Regression test for why resetCsvInputDir exists: Pyodide stays warm for
  // the whole tab session, so runSummarizerWithPyodide() runs against the
  // same long-lived virtual filesystem every time the user hits "Refresh."
  // Without wiping /csv_input first, a file from an earlier run would still
  // be sitting there and silently bleed into a later, unrelated result.
  it('does not leak a previous run\'s files into a later run', async () => {
    await runSummarizerWithPyodide(pyodide, [
      { accountType: 'Bank', institution: 'Wells Fargo', name: 'WellsFargo_Checking_9001.csv', content: chaseBankCsv('-10.00', 'COFFEE') },
    ])

    const second = await runSummarizerWithPyodide(pyodide, [
      { accountType: 'Bank', institution: 'Chase', name: 'Chase_Checking_6789.csv', content: chaseBankCsv('-82.30', 'SAFEWAY') },
    ])

    const institutions = second.bank_summary.by_account.map(a => a.account_name)
    expect(institutions).toEqual(['Chase Checking'])
  })
})

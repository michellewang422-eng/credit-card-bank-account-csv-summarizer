const DRIVE_FILES_URL = 'https://www.googleapis.com/drive/v3/files'
const FOLDER_MIME_TYPE = 'application/vnd.google-apps.folder'

async function driveRequest(accessToken, path, options = {}) {
  const res = await fetch(`${DRIVE_FILES_URL}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      ...options.headers,
    },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error?.message || `Drive API error (${res.status})`)
  }
  return res.json()
}

async function listChildren(accessToken, folderId) {
  const params = new URLSearchParams({
    q: `'${folderId}' in parents and trashed = false`,
    fields: 'files(id,name,mimeType,modifiedTime)',
    pageSize: '100',
  })
  const { files } = await driveRequest(accessToken, `?${params}`)
  return files
}

function createFolder(accessToken, name, parentId) {
  return driveRequest(accessToken, '', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, mimeType: FOLDER_MIME_TYPE, parents: [parentId] }),
  })
}

// Every signed-in user gets their own top-level "Finance" folder — found by
// name in their Drive root if it already exists, created (with the
// Bank/CreditCard/Investment skeleton) the first time otherwise.
export async function findOrCreateFinanceFolder(accessToken) {
  const params = new URLSearchParams({
    q: `'root' in parents and mimeType = '${FOLDER_MIME_TYPE}' and name = 'Finance' and trashed = false`,
    fields: 'files(id,name)',
    pageSize: '1',
  })
  const { files } = await driveRequest(accessToken, `?${params}`)
  if (files.length > 0) return files[0].id

  const financeFolder = await createFolder(accessToken, 'Finance', 'root')
  await Promise.all(
    ['Bank', 'CreditCard', 'Investment'].map(name => createFolder(accessToken, name, financeFolder.id))
  )
  return financeFolder.id
}

// Finance/<accountType>/<institution>/*.csv — walk two levels of subfolders
// to collect CSVs, tagging each with the account type + institution inferred
// from its folder path (per project notes' metadata inference rules).
export async function listFinanceFiles(accessToken, financeFolderId) {
  const accountTypeFolders = await listChildren(accessToken, financeFolderId)
  const results = []

  for (const accountTypeFolder of accountTypeFolders) {
    if (accountTypeFolder.mimeType !== FOLDER_MIME_TYPE) continue
    const institutionFolders = await listChildren(accessToken, accountTypeFolder.id)

    for (const institutionFolder of institutionFolders) {
      if (institutionFolder.mimeType !== FOLDER_MIME_TYPE) continue
      const files = await listChildren(accessToken, institutionFolder.id)

      for (const file of files) {
        if (!file.name.toLowerCase().endsWith('.csv')) continue
        results.push({
          id: file.id,
          name: file.name,
          accountType: accountTypeFolder.name,
          institution: institutionFolder.name,
          modifiedTime: file.modifiedTime,
        })
      }
    }
  }

  return results
}

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

// Every signed-in user is expected to have their own top-level "Finance"
// folder, set up by hand following the in-app setup guide. Returns null if
// no such folder exists yet — callers show the setup guide in that case.
export async function findFinanceFolder(accessToken) {
  const params = new URLSearchParams({
    q: `'root' in parents and mimeType = '${FOLDER_MIME_TYPE}' and name = 'Finance' and trashed = false`,
    fields: 'files(id,name)',
    pageSize: '1',
  })
  const { files } = await driveRequest(accessToken, `?${params}`)
  return files.length > 0 ? files[0].id : null
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

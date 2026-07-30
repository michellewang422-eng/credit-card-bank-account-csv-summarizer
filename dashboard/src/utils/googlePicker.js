const API_KEY = import.meta.env.VITE_GOOGLE_API_KEY

function loadPickerApi() {
  return new Promise((resolve, reject) => {
    if (window.google?.picker) {
      resolve()
      return
    }
    if (!window.gapi) {
      reject(new Error('Google API loader is still loading — try again in a moment'))
      return
    }
    window.gapi.load('picker', { callback: resolve, onerror: reject })
  })
}

// Lets the user pick an existing Drive folder to use as the Finance root,
// instead of requiring one named exactly "Finance" in their Drive root.
export async function pickFinanceFolder(accessToken) {
  if (!API_KEY) throw new Error('Missing VITE_GOOGLE_API_KEY — set it in dashboard/.env.local')

  await loadPickerApi()

  const view = new window.google.picker.DocsView(window.google.picker.ViewId.FOLDERS)
    .setSelectFolderEnabled(true)
    .setIncludeFolders(true)

  return new Promise((resolve, reject) => {
    const picker = new window.google.picker.PickerBuilder()
      .addView(view)
      .setOAuthToken(accessToken)
      .setDeveloperKey(API_KEY)
      .setCallback((data) => {
        if (data.action === window.google.picker.Action.PICKED) {
          const folder = data.docs[0]
          resolve({ id: folder.id, name: folder.name })
        } else if (data.action === window.google.picker.Action.CANCEL) {
          resolve(null)
        }
      })
      .build()
    picker.setVisible(true)
  })
}

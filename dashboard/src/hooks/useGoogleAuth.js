import { useCallback, useEffect, useRef, useState } from 'react'

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID
// drive.readonly: find/read the user's existing Finance folder & CSVs.
// The app never writes to Drive (missing folders route to an in-app
// setup guide instead), so no write scope is requested.
const SCOPE = [
  'openid',
  'email',
  'profile',
  'https://www.googleapis.com/auth/drive.readonly',
].join(' ')

// Access tokens from GIS aren't restored on page reload by themselves —
// persist them (per tab) so a refresh doesn't look like a sign-out.
const SESSION_KEY = 'googleAuthSession'

function loadSession() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(SESSION_KEY))
    if (saved && saved.expiresAt > Date.now()) return saved
  } catch {
    // ignore malformed/missing session
  }
  sessionStorage.removeItem(SESSION_KEY)
  return null
}

function saveSession(session) {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
}

const MAX_INIT_ATTEMPTS = 100 // ~10s at 100ms intervals

export function useGoogleAuth() {
  const initialSession = loadSession()
  const [accessToken, setAccessToken] = useState(initialSession?.accessToken ?? null)
  const [profile, setProfile] = useState(initialSession?.profile ?? null)
  const [error, setError] = useState(null)
  const tokenClientRef = useRef(null)

  useEffect(() => {
    if (!CLIENT_ID) {
      setError('Missing VITE_GOOGLE_CLIENT_ID — set it in dashboard/.env.local')
      return
    }

    let cancelled = false
    const initWhenReady = () => {
      if (cancelled) return
      if (window.google?.accounts?.oauth2) {
        tokenClientRef.current = window.google.accounts.oauth2.initTokenClient({
          client_id: CLIENT_ID,
          scope: SCOPE,
          callback: async (tokenResponse) => {
            if (tokenResponse.error) {
              setError(tokenResponse.error)
              return
            }
            setAccessToken(tokenResponse.access_token)
            try {
              const res = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
                headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
              })
              const info = await res.json()
              setProfile(info)
              saveSession({
                accessToken: tokenResponse.access_token,
                profile: info,
                expiresAt: Date.now() + tokenResponse.expires_in * 1000,
              })
              console.log('Signed in as', info.email)
            } catch (err) {
              setError(err.message)
            }
          },
        })
      } else if (attempts < MAX_INIT_ATTEMPTS) {
        attempts++
        setTimeout(initWhenReady, 100)
      } else {
        setError('Google sign-in failed to load — check your network or ad blocker and reload the page')
      }
    }
    let attempts = 0
    initWhenReady()

    return () => {
      cancelled = true
    }
  }, [])

  const signIn = useCallback(() => {
    if (!tokenClientRef.current) {
      setError('Google Identity Services is still loading — try again in a moment')
      return
    }
    setError(null)
    tokenClientRef.current.requestAccessToken({ prompt: 'consent' })
  }, [])

  const signOut = useCallback(() => {
    if (accessToken && window.google?.accounts?.oauth2) {
      window.google.accounts.oauth2.revoke(accessToken, () => {})
    }
    setAccessToken(null)
    setProfile(null)
    sessionStorage.removeItem(SESSION_KEY)
    console.log('Signed out')
  }, [accessToken])

  return { accessToken, profile, error, signIn, signOut }
}

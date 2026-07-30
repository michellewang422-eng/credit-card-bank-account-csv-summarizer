import { useCallback, useEffect, useRef, useState } from 'react'

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID
// drive.readonly: find/read the user's existing Finance folder & CSVs.
// drive.file: create the Finance/Bank/CreditCard/Investment skeleton for
// users who don't have one yet. See project notes §7.1.
const SCOPE = [
  'openid',
  'email',
  'profile',
  'https://www.googleapis.com/auth/drive.readonly',
  'https://www.googleapis.com/auth/drive.file',
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
      } else {
        setTimeout(initWhenReady, 100)
      }
    }
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

  return { accessToken, profile, error, signIn, signOut, isSignedIn: !!accessToken }
}

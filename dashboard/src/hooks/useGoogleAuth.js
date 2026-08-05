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
          // async：这个函式里面有需要「等待」的事情（跟 Google 要用户资料，要等网络回应）。
          // await：等这一行的结果真的回来了，才往下执行下一行；不然程式会没等到
          // 结果就往下跑，抓到的东西会是空的。
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

  // useCallback：让这个函式在多次渲染之间保持「同一份」，除非依赖数组
  // 里的东西变了，才重做一份新的。这里依赖是 []，因为函式里用到的
  // tokenClientRef 是 ref（本身参照永远不变）、setError 是 useState 的
  // setter（React 保证参照稳定），所以 signIn 永远不需要变，一直用同一份就好。
  const signIn = useCallback(() => {
    if (!tokenClientRef.current) {
      setError('Google Identity Services is still loading — try again in a moment')
      return
    }
    setError(null)
    tokenClientRef.current.requestAccessToken({ prompt: 'consent' })
  }, [])

  // useCallback + [accessToken]：因为函式里面要读 accessToken 这个 state，
  // 所以 accessToken 一变，就要重做一份新的函式，才能读到最新的值——
  // 不然会一直读到旧的（stale closure，过时闭包）。
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

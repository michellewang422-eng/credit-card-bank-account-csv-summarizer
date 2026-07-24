import { useCallback, useEffect, useRef, useState } from 'react'

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID
// drive.readonly is requested now so the token already carries the scope
// PR4/PR5 will need — login itself doesn't call the Drive API yet.
const SCOPE = 'openid email profile https://www.googleapis.com/auth/drive.readonly'

export function useGoogleAuth() {
  const [accessToken, setAccessToken] = useState(null)
  const [profile, setProfile] = useState(null)
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
    console.log('Signed out')
  }, [accessToken])

  return { accessToken, profile, error, signIn, signOut, isSignedIn: !!accessToken }
}

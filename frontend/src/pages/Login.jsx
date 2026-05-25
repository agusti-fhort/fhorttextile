import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../store/auth'

const Logo = () => (
  <svg viewBox="0 0 222.7 79.76" xmlns="http://www.w3.org/2000/svg" style={{width: 200, height: 'auto'}}>
    <path fill="#c27a2a" d="M31.22,0H1.07C.48,0,0,.48,0,1.07v38.22c0,.59.48,1.07,1.07,1.07h9.04c.59,0,1.07-.48,1.07-1.07v-12.27c0-.59.48-1.07,1.07-1.07h16.94c.59,0,1.07-.48,1.07-1.07v-7.14c0-.59-.48-1.07-1.07-1.07H12.26c-.59,0-1.07-.48-1.07-1.07v-4.72c0-.59.48-1.07,1.07-1.07h18.96c.59,0,1.07-.48,1.07-1.07V1.07c0-.59-.48-1.07-1.07-1.07Z"/>
    <path fill="#c27a2a" d="M54.21,8.48c-4.38,0-7.24,2.3-9.25,4.85-.03.04-.09.02-.09-.03V1.07c0-.59-.48-1.07-1.07-1.07h-8.81c-.59,0-1.07.48-1.07,1.07v38.22c0,.59.48,1.07,1.07,1.07h8.81c.59,0,1.07-.48,1.07-1.07v-15.82c0-3.46,1.96-5.31,4.61-5.31s4.44,1.85,4.44,5.31v15.82c0,.59.48,1.07,1.07,1.07h8.75c.59,0,1.07-.48,1.07-1.07v-19.34c0-7.09-3.98-11.48-10.61-11.48Z"/>
    <path fill="#c27a2a" d="M83.62,8.48c-9.98,0-17.24,7.44-17.24,16.32v.12c0,8.88,7.21,16.2,17.13,16.2s17.3-7.44,17.3-16.32v-.12c0-8.88-7.21-16.2-17.18-16.2ZM90.19,24.91c0,3.75-2.59,6.92-6.57,6.92s-6.63-3.23-6.63-7.04v-.12c0-3.39,2.02-6.28,5.27-6.87,4.16-.75,7.93,2.62,7.93,6.84v.26Z"/>
    <path fill="#c27a2a" d="M137.24,20.18h6.14c.59,0,1.07-.48,1.07-1.07v-9.39c0-.59-.48-1.07-1.07-1.07h-6.14s-.05-.02-.05-.05V1.07c0-.59-.48-1.07-1.07-1.07h-8.75c-.59,0-1.07.48-1.07,1.07v7.53s-.02.05-.05.05h-2.89c-5.22,0-7.98,2.45-9.77,6.58-.02.05-.1.04-.1-.02v-4.97c0-.59-.48-1.07-1.07-1.07h-8.81c-.59,0-1.07.48-1.07,1.07v29.05c0,.59.48,1.07,1.07,1.07h8.81c.59,0,1.07-.48,1.07-1.07v-8.67c0-7.15,3.23-10.44,8.94-10.44h3.81s.05.02.05.05v10.45c0,7.44,3.86,10.32,10.44,10.32h6.54c.59,0,1.07-.48,1.07-1.07v-8.76c0-.59-.48-1.07-1.07-1.07-1.07,0-1.91-.02-3.08-.02-2.02,0-3-.92-3-3.11v-6.73s.02-.05.05-.05Z"/>
    <path fill="#ffffff" d="M10.21,51.84H0v-1.27h21.86v1.27h-10.25v27.43h-1.39v-27.43Z"/>
    <path fill="#ffffff" d="M20.83,68.94v-.08c0-6.07,4.18-10.74,9.88-10.74,6.23,0,9.47,5.33,9.47,10.87v.45h-17.92c.25,5.62,4.22,9.1,8.86,9.1,3.2,0,5.78-1.68,7.42-3.81l.98.78c-1.89,2.46-4.67,4.26-8.45,4.26-5.58,0-10.25-4.22-10.25-10.83ZM38.75,68.24c-.2-4.51-2.95-8.9-8.12-8.9-4.68,0-8.12,3.81-8.37,8.9h16.48Z"/>
    <path fill="#ffffff" d="M52.44,67.87l7.75-9.27h1.56l-8.49,10.13,8.82,10.54h-1.64l-8.04-9.64-8.04,9.64h-1.56l8.82-10.5-8.49-10.17h1.64l7.67,9.27Z"/>
    <path fill="#ffffff" d="M68.55,73.98v-14.19h-3.16v-1.19h3.16v-6.93h1.31v6.93h7.5v1.19h-7.5v14.07c0,3.03,1.6,4.55,4.3,4.55,1.03,0,2.05-.25,3.12-.74v1.27c-1.03.49-2.09.7-3.24.7-3.32,0-5.49-1.93-5.49-5.66Z"/>
    <path fill="#ffffff" d="M83.22,50.4h1.77v2.5h-1.77v-2.5ZM83.43,58.6h1.35v20.67h-1.35v-20.67Z"/>
    <path fill="#ffffff" d="M92.9,49.34h1.35v29.94h-1.35v-29.94Z"/>
    <path fill="#ffffff" d="M100.69,68.94v-.08c0-6.07,4.18-10.74,9.88-10.74,6.23,0,9.47,5.33,9.47,10.87v.45h-17.92c.25,5.62,4.22,9.1,8.86,9.1,3.2,0,5.78-1.68,7.42-3.81l.98.78c-1.89,2.46-4.68,4.26-8.45,4.26-5.58,0-10.25-4.22-10.25-10.83ZM118.61,68.24c-.2-4.51-2.95-8.9-8.12-8.9-4.68,0-8.12,3.81-8.37,8.9h16.48Z"/>
    <path fill="#ffffff" d="M145.78,51.84h-10.21v-1.27h21.86v1.27h-10.25v27.43h-1.39v-27.43Z"/>
    <path fill="#ffffff" d="M156.4,68.94v-.08c0-6.07,4.18-10.74,9.88-10.74,6.23,0,9.47,5.33,9.47,10.87v.45h-17.92c.25,5.62,4.22,9.1,8.86,9.1,3.2,0,5.78-1.68,7.42-3.81l.98.78c-1.89,2.46-4.68,4.26-8.45,4.26-5.58,0-10.25-4.22-10.25-10.83ZM174.32,68.24c-.2-4.51-2.95-8.9-8.12-8.9-4.68,0-8.12,3.81-8.37,8.9h16.48Z"/>
    <path fill="#ffffff" d="M180.3,68.98v-.08c0-5.82,4.59-10.79,10.58-10.79,3.81,0,6.23,1.72,8.24,3.81l-.94.94c-1.8-1.93-4.06-3.53-7.34-3.53-5.21,0-9.15,4.31-9.15,9.52v.08c0,5.21,4.06,9.6,9.23,9.6,3.28,0,5.62-1.68,7.42-3.69l.94.82c-2.01,2.34-4.59,4.1-8.45,4.1-5.95,0-10.54-4.92-10.54-10.79Z"/>
    <path fill="#ffffff" d="M204.9,49.34h1.31v14.19c.94-2.46,3.53-5.41,7.96-5.41,5.45,0,8.53,3.69,8.53,9.06v12.1h-1.31v-11.89c0-4.8-2.58-8.04-7.38-8.04-4.35,0-7.79,3.57-7.79,8.28v11.65h-1.31v-29.94Z"/>
  </svg>
)

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const login = useAuthStore(s => s.login)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/')
    } catch {
      setError('Credencials incorrectes. Torna a intentar-ho.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--charcoal)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <div style={{
        width: '100%',
        maxWidth: 400,
        padding: '48px 40px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 32,
      }}>
        <Logo />
        <form onSubmit={handleSubmit} style={{width: '100%', display: 'flex', flexDirection: 'column', gap: 16}}>
          <input
            type="text"
            placeholder="Usuari"
            value={username}
            onChange={e => setUsername(e.target.value)}
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: '0.5px solid rgba(255,255,255,0.15)',
              borderRadius: 8,
              padding: '12px 16px',
              color: 'white',
              fontSize: 13,
              outline: 'none',
              fontFamily: 'var(--font)',
            }}
          />
          <input
            type="password"
            placeholder="Contrasenya"
            value={password}
            onChange={e => setPassword(e.target.value)}
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: '0.5px solid rgba(255,255,255,0.15)',
              borderRadius: 8,
              padding: '12px 16px',
              color: 'white',
              fontSize: 13,
              outline: 'none',
              fontFamily: 'var(--font)',
            }}
          />
          {error && (
            <p style={{fontSize: 12, color: '#e88080', textAlign: 'center'}}>{error}</p>
          )}
          <button
            type="submit"
            disabled={loading}
            style={{
              background: loading ? 'rgba(194,122,42,0.5)' : 'var(--gold)',
              color: 'white',
              border: 'none',
              borderRadius: 8,
              padding: '12px 16px',
              fontSize: 13,
              fontWeight: 500,
              cursor: loading ? 'not-allowed' : 'pointer',
              fontFamily: 'var(--font)',
              marginTop: 8,
            }}
          >
            {loading ? 'Entrant...' : 'Entrar'}
          </button>
        </form>
        <p style={{fontSize: 11, color: 'rgba(255,255,255,0.2)'}}>fhorttextile.tech</p>
      </div>
    </div>
  )
}

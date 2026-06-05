import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { IconEye, IconEyeOff } from '@tabler/icons-react'
import { login as loginApi, me as meApi } from '../api/auth'
import useAuthStore from '../store/authStore'

// Sistema de disseny del producte (tokens a index.css). Estilat via variables
// CSS inline, no utility classes de Tailwind.
const MONO = "'IBM Plex Mono', monospace"

const fieldStyle = {
  width: '100%',
  background: 'var(--bg-card)',
  border: '1px solid var(--border)',
  borderRadius: 6,
  padding: '11px 14px',
  color: 'var(--text-main)',
  fontSize: 13,
  fontFamily: MONO,
  outline: 'none',
}

const labelStyle = {
  display: 'block',
  fontSize: 11,
  letterSpacing: '0.06em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
  marginBottom: 6,
}

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const setAuth = useAuthStore((s) => s.setAuth)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await loginApi(email, password)
      // El backend pot retornar el token amb diferents claus segons la
      // implementació; siguem tolerants.
      const token = data.token || data.access || data.access_token
      let user = data.user || null
      let rol = data.rol || data.user?.rol || null
      setAuth({ token })

      // Si el login no inclou el perfil, el recuperem de /auth/me/.
      if (!user) {
        try {
          const profile = await meApi()
          user = profile
          rol = profile.rol || rol
        } catch {
          // No bloquegem l'accés si /me/ falla; ja tenim token vàlid.
        }
      }
      setAuth({ user, rol })
      navigate('/dashboard')
    } catch {
      setError('Credencials incorrectes. Torna a intentar-ho.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex' }}>
      {/* Columna esquerra — marca */}
      <div
        style={{
          flex: '0 0 40%',
          background: 'var(--bg-sidebar)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 40,
        }}
      >
        <div style={{ textAlign: 'center' }}>
          <div
            style={{
              fontFamily: MONO,
              fontWeight: 600,
              fontSize: 56,
              letterSpacing: '0.12em',
              color: 'var(--gold)',
              lineHeight: 1,
            }}
          >
            FHORT
          </div>
          <div
            style={{
              fontFamily: MONO,
              fontWeight: 400,
              fontSize: 16,
              letterSpacing: '0.28em',
              textTransform: 'uppercase',
              color: 'var(--text-muted)',
              marginTop: 14,
            }}
          >
            Backoffice
          </div>
        </div>
      </div>

      {/* Columna dreta — formulari */}
      <div
        style={{
          flex: '1 1 60%',
          background: 'var(--bg-main)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 40,
        }}
      >
        <form
          onSubmit={handleSubmit}
          style={{ width: '100%', maxWidth: 360, display: 'flex', flexDirection: 'column' }}
        >
          <h1
            style={{
              fontFamily: MONO,
              fontWeight: 500,
              fontSize: 24,
              color: 'var(--text-main)',
              marginBottom: 32,
            }}
          >
            Accés
          </h1>

          <div style={{ marginBottom: 18 }}>
            <label htmlFor="email" style={labelStyle}>Correu electrònic</label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={fieldStyle}
            />
          </div>

          <div style={{ marginBottom: 8 }}>
            <label htmlFor="password" style={labelStyle}>Contrasenya</label>
            <div style={{ position: 'relative' }}>
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ ...fieldStyle, paddingRight: 42 }}
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? 'Amaga la contrasenya' : 'Mostra la contrasenya'}
                style={{
                  position: 'absolute',
                  right: 6,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: 6,
                  display: 'flex',
                  alignItems: 'center',
                  color: 'var(--text-muted)',
                }}
              >
                {showPassword ? <IconEyeOff size={18} stroke={1.5} /> : <IconEye size={18} stroke={1.5} />}
              </button>
            </div>
          </div>

          {error && (
            <p style={{ fontFamily: MONO, fontSize: 12, color: 'var(--err)', marginTop: 8 }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: 24,
              background: 'var(--gold)',
              color: '#ffffff',
              border: 'none',
              borderRadius: 6,
              padding: '12px 16px',
              fontFamily: MONO,
              fontSize: 13,
              fontWeight: 500,
              letterSpacing: '0.04em',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? 'Entrant…' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  )
}

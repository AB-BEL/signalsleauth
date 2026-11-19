import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setErr('')
    setBusy(true)
    try {
      const u = await login(email, password)
      nav('/', { replace: true })
    } catch (ex) {
      setErr(ex.message || 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="screen">
      <h1 style={{ marginTop: 24, color: 'var(--green)' }}>Signal Sleuth</h1>
      <p style={{ color: 'var(--dim)', marginBottom: 20 }}>Student mobile login — your own dashboard & scores</p>
      <form className="card" onSubmit={onSubmit}>
        <label>Email</label>
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="username" />
        <label>Password</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
        {err && <p className="error">{err}</p>}
        <button className="btn" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
      </form>
      <Link className="linkish" to="/register">Create account</Link>
    </div>
  )
}

import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Register() {
  const { register } = useAuth()
  const nav = useNavigate()
  const [form, setForm] = useState({ student_id: '', full_name: '', email: '', password: '', campus_id: '' })
  const [err, setErr] = useState('')
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  async function onSubmit(e) {
    e.preventDefault()
    setErr('')
    setBusy(true)
    try {
      const d = await register(form)
      setMsg(d.message || 'Registered')
      if (d.token) nav('/', { replace: true })
    } catch (ex) {
      setErr(ex.message || 'Registration failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="screen">
      <h1 style={{ marginTop: 16 }}>Register</h1>
      <p style={{ color: 'var(--dim)', fontSize: '0.9rem' }}>Student ID must be pre-listed by admin. A username is generated for you.</p>
      <form className="card" onSubmit={onSubmit}>
        <label>Student ID *</label>
        <input value={form.student_id} onChange={set('student_id')} required placeholder="NaScR####/##" />
        <label>Full name *</label>
        <input value={form.full_name} onChange={set('full_name')} required />
        <label>Campus ID</label>
        <input value={form.campus_id} onChange={set('campus_id')} placeholder="Optional" />
        <label>Email *</label>
        <input type="email" value={form.email} onChange={set('email')} required />
        <label>Password * (min 6)</label>
        <input type="password" value={form.password} onChange={set('password')} required minLength={6} />
        {err && <p className="error">{err}</p>}
        {msg && <p className="ok">{msg}</p>}
        <button className="btn" disabled={busy}>{busy ? 'Creating…' : 'Sign up'}</button>
      </form>
      <Link className="linkish" to="/login">Already registered? Sign in</Link>
    </div>
  )
}

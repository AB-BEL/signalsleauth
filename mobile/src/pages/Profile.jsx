import React from 'react'
import { useAuth } from '../context/AuthContext'

export default function Profile() {
  const { user, logout } = useAuth()
  if (!user) return null
  return (
    <div className="screen">
      <div className="identity">
        <div className="uname">{user.generated_username}</div>
        <div className="meta">{user.full_name}</div>
        <div className="meta">ID: {user.student_id}</div>
        <div className="meta">{user.email}</div>
        <div className="meta">Status chapter: {user.status_chapter || 1}</div>
      </div>
      <p style={{ color: 'var(--dim)', fontSize: '0.88rem' }}>
        Scores and rank are unique to this account. Log out before another player uses this phone.
      </p>
      <button className="btn secondary" onClick={logout}>Log out</button>
    </div>
  )
}

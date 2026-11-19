import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { gameApi } from '../api/client'
import { useAuth } from '../context/AuthContext'

export default function Dashboard() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    gameApi.dashboard()
      .then(setData)
      .catch((e) => setErr(e.message))
  }, [])

  if (err) return <div className="screen"><p className="error">{err}</p></div>
  if (!data) return <div className="screen center">Loading dashboard…</div>

  const u = data.user || user

  return (
    <div className="screen">
      <div className="identity">
        <div className="uname">{u.generated_username}</div>
        <div className="meta">{u.full_name || '—'} · {u.student_id}</div>
        <div className="meta">{u.email} · Ch. {u.status_chapter}</div>
        <div className="stat-row">
          <div className="stat"><b>{data.rank != null ? `#${data.rank}` : '—'}</b><span>Rank</span></div>
          <div className="stat"><b>{Number(data.final_score || 0).toFixed(1)}</b><span>Score /100</span></div>
          <div className="stat"><b>{data.total_players || 0}</b><span>Players</span></div>
        </div>
      </div>

      <div className="card">
        <h3>My chapters</h3>
        <p style={{ fontSize: '0.8rem', color: 'var(--dim)', marginBottom: 8 }}>{data.pass_rule}</p>
        {(data.chapters || []).map((ch) => (
          <div className="chapter-row" key={ch.chapter_num}>
            <div className="info">
              <strong>Ch.{ch.chapter_num} {ch.title}</strong>
              <span>
                {ch.progress
                  ? `${ch.progress.total_score}/${ch.progress.max_possible} pts`
                  : 'No scores yet'}
                {ch.progress?.passed ? ' · passed' : ''}
              </span>
              <div style={{ marginTop: 4 }}>
                {ch.access_ok ? <span className="badge ok">Open</span> : <span className="badge off">Locked</span>}
                {!ch.has_game && <span className="badge warn">No game file</span>}
              </div>
            </div>
            {ch.access_ok && data.season_active && (
              <Link className="btn sm" to={`/play/${ch.chapter_num}`}>Play</Link>
            )}
          </div>
        ))}
      </div>

      <div className="card">
        <h3>League (top)</h3>
        <table className="table">
          <thead><tr><th>#</th><th>User</th><th>Score</th></tr></thead>
          <tbody>
            {(data.league || []).slice(0, 10).map((r) => (
              <tr key={r.user_id} className={r.user_id === u.id ? 'me' : ''}>
                <td>{r.rank}</td>
                <td>{r.generated_username || r.student_id}</td>
                <td>{Number(r.overall_score).toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

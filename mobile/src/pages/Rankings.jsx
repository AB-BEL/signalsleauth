import React, { useEffect, useState } from 'react'
import { gameApi } from '../api/client'
import { useAuth } from '../context/AuthContext'

export default function Rankings() {
  const { user } = useAuth()
  const [ranks, setRanks] = useState([])
  const [err, setErr] = useState('')

  useEffect(() => {
    gameApi.rankings()
      .then((d) => setRanks(d.ranks || []))
      .catch((e) => setErr(e.message))
  }, [])

  return (
    <div className="screen">
      <h2>Overall rankings</h2>
      {err && <p className="error">{err}</p>}
      <div className="card">
        <table className="table">
          <thead><tr><th>#</th><th>Username</th><th>Score</th><th>Passed</th></tr></thead>
          <tbody>
            {ranks.map((r) => (
              <tr key={r.user_id} className={r.user_id === user?.id ? 'me' : ''}>
                <td>{r.rank}</td>
                <td>{r.generated_username || r.student_id}</td>
                <td>{Number(r.overall_score || r.effective_score || 0).toFixed(2)}</td>
                <td>{r.chapters_passed ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

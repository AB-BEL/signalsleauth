import React, { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiBase, gameApi } from '../api/client'

/**
 * Dynamic mobile game loader.
 * Loads chapter game definition from /api/chapter/:n/game-package
 * - mode "bank": native question UI for any chapter (1–10) from question_bank
 * - mode "html": embedded admin-uploaded HTML (tokenized /game-file)
 * Uses same submit-score / rankings / auth services as web.
 */
export default function Play() {
  const { chapter } = useParams()
  const chapterNum = Number(chapter) || 1

  const [pkg, setPkg] = useState(null)
  const [scores, setScores] = useState([])
  const [locks, setLocks] = useState({})
  const [htmlUrl, setHtmlUrl] = useState(null)
  const [err, setErr] = useState('')
  const [levelId, setLevelId] = useState(null)
  const [answers, setAnswers] = useState({})
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [view, setView] = useState('map') // map | level | html

  const load = useCallback(() => {
    setErr('')
    setLevelId(null)
    setResult(null)
    setAnswers({})
    gameApi
      .gamePackage(chapterNum)
      .then((data) => {
        setPkg(data.package || null)
        setScores(data.scores || [])
        setLocks(data.locks || {})
        const base = apiBase()
        const rel = data.html_play_url
        setHtmlUrl(rel ? (rel.startsWith('http') ? rel : base + rel) : null)
        setView(data.package?.mode === 'html' && !data.package?.has_question_bank ? 'html' : 'map')
      })
      .catch((e) => setErr(e.message))
  }, [chapterNum])

  useEffect(() => {
    load()
  }, [load])

  function truthyCleared(v) {
    return v === true || v === 1 || v === '1' || v === 'true'
  }
  function serverCleared(id) {
    const row = scores.find((s) => Number(s.level_num) === Number(id))
    if (!row) return false
    if (truthyCleared(row.cleared) || truthyCleared(row.level_cleared)) return true
    const max = Number(row.max_score) || 0
    const best = Number(row.best_score) || 0
    return max > 0 && best / max >= 0.5
  }
  function isUnlocked(id) {
    if (Number(id) === 1) return true
    return serverCleared(Number(id) - 1)
  }
  function isLockedReplay(id) {
    const lk = locks?.[id] || locks?.[String(id)]
    return lk && lk.locked
  }
  function bestFor(id) {
    const row = scores.find((s) => Number(s.level_num) === Number(id))
    return row ? row.best_score : null
  }

  async function submit() {
    const levels = pkg?.levels || []
    const lv = levels.find((l) => Number(l.id) === Number(levelId))
    if (!lv) return
    setBusy(true)
    setResult(null)
    try {
      const data = await gameApi.submitScore({
        chapter_num: chapterNum,
        level_num: levelId,
        answers: (lv.questions || []).map((q, i) => ({
          q_index: q.q_index || i + 1,
          answer: answers[i] || '',
        })),
      })
      const totalEarned = Number(data.score != null ? data.score : data.level_score) || 0
      const totalMax = Number(data.max_score) || lv.maxScore || 0
      const passed = !!(data.level_cleared || data.cleared)
      setResult({
        totalEarned,
        totalMax,
        passed,
        attempts: data.attempts,
        feedback: data.feedback || [],
        msg: passed
          ? 'Level cleared (≥50%). Next level unlocked.'
          : `Not cleared — need ≥50% (you have ${totalMax ? Math.round((100 * totalEarned) / totalMax) : 0}%).`,
      })
      // refresh scores from package endpoint
      const refreshed = await gameApi.gamePackage(chapterNum)
      setScores(refreshed.scores || [])
      setLocks(refreshed.locks || {})
    } catch (e) {
      setErr(e.message)
    } finally {
      setBusy(false)
    }
  }

  if (err && !pkg) {
    return (
      <div className="screen">
        <div className="topbar">
          <Link to="/">←</Link>
          <h1>Chapter {chapterNum}</h1>
        </div>
        <div className="error-box">{err}</div>
      </div>
    )
  }

  if (!pkg) {
    return <div className="screen center">Loading game…</div>
  }

  const levels = pkg.levels || []

  // HTML embedded mode
  if (view === 'html' && htmlUrl) {
    return (
      <div className="screen play-html">
        <div className="topbar">
          <Link to="/">←</Link>
          <h1>Ch.{chapterNum} {pkg.title}</h1>
          {levels.length > 0 && (
            <button type="button" className="btn sm" onClick={() => setView('map')}>
              Bank UI
            </button>
          )}
        </div>
        <p className="hint">Admin HTML game · scores sync via server bridge</p>
        <iframe title={`Chapter ${chapterNum} game`} className="game-frame" src={htmlUrl} />
      </div>
    )
  }

  // Level play (native bank)
  if (levelId != null) {
    const lv = levels.find((l) => Number(l.id) === Number(levelId))
    if (!lv) {
      return (
        <div className="screen">
          <button type="button" className="btn" onClick={() => setLevelId(null)}>
            Back
          </button>
          <p>Level not found in package.</p>
        </div>
      )
    }
    return (
      <div className="screen">
        <div className="topbar">
          <button type="button" className="linkish" onClick={() => { setLevelId(null); setResult(null); setAnswers({}) }}>
            ← Levels
          </button>
          <h1>
            L{lv.id}: {lv.title}
          </h1>
        </div>
        {err && <div className="error-box">{err}</div>}
        <p className="hint">Answer in your own words. Server scores your answers (≥50% to clear).</p>
        {(lv.questions || []).map((q, i) => (
          <div className="q-block" key={q.q_index || i}>
            <label>
              Q{q.q_index || i + 1}. {q.text}{' '}
              <span className="pts">({q.points} pts)</span>
            </label>
            <textarea
              rows={3}
              value={answers[i] || ''}
              onChange={(e) => setAnswers({ ...answers, [i]: e.target.value })}
              placeholder="Your answer…"
              disabled={!!result}
            />
          </div>
        ))}
        {!result ? (
          <button type="button" className="btn primary block" disabled={busy} onClick={submit}>
            {busy ? 'Scoring…' : 'Submit for scoring'}
          </button>
        ) : (
          <div className="result-card">
            <div className="big">
              {result.totalEarned} / {result.totalMax}
            </div>
            <p>{result.msg}</p>
            <p className="hint">Attempts: {result.attempts ?? '—'}</p>
            {(result.feedback || []).map((f, i) => (
              <div className="fb" key={i}>
                <strong>Q{i + 1}</strong> {f.score}/{f.max}
                <div className="dim">{f.feedback}</div>
              </div>
            ))}
            <div className="row-btns">
              {result.passed && levelId < 7 && levels.some((l) => Number(l.id) === Number(levelId) + 1) && (
                <button
                  type="button"
                  className="btn primary"
                  onClick={() => {
                    setLevelId(Number(levelId) + 1)
                    setResult(null)
                    setAnswers({})
                  }}
                >
                  Next level
                </button>
              )}
              <button
                type="button"
                className="btn"
                onClick={() => {
                  setLevelId(null)
                  setResult(null)
                  setAnswers({})
                }}
              >
                Level map
              </button>
            </div>
          </div>
        )}
      </div>
    )
  }

  // Map
  return (
    <div className="screen">
      <div className="topbar">
        <Link to="/">←</Link>
        <h1>
          Ch.{chapterNum} {pkg.title}
        </h1>
      </div>
      {err && <div className="error-box">{err}</div>}
      <p className="hint">
        Mode: <strong>{pkg.mode}</strong>
        {pkg.has_question_bank ? ' · question bank' : ''}
        {pkg.has_html_game ? ' · HTML available' : ''}
      </p>
      {pkg.has_html_game && htmlUrl && (
        <button type="button" className="btn sm block" onClick={() => setView('html')}>
          Open uploaded HTML game
        </button>
      )}
      {!levels.length && !pkg.has_html_game && (
        <div className="empty">
          No mobile game content for this chapter yet. Admin should load the question bank or upload an HTML game.
        </div>
      )}
      <div className="level-list">
        {levels.map((lv) => {
          const unlocked = isUnlocked(lv.id)
          const cleared = serverCleared(lv.id)
          const lockedReplay = isLockedReplay(lv.id)
          const best = bestFor(lv.id)
          return (
            <button
              type="button"
              key={lv.id}
              className={`level-card ${!unlocked || lockedReplay ? 'locked' : ''} ${cleared ? 'cleared' : ''}`}
              disabled={!unlocked || lockedReplay}
              onClick={() => {
                setLevelId(lv.id)
                setResult(null)
                setAnswers({})
                setErr('')
              }}
            >
              <div className="level-num">{cleared ? '✓' : lv.id}</div>
              <div className="level-info">
                <strong>{lv.title}</strong>
                <span>
                  {lockedReplay
                    ? 'Locked (PDF on web)'
                    : unlocked
                      ? cleared
                        ? 'Cleared'
                        : 'Unlocked'
                      : 'Locked'}
                  {best != null ? ` · ${best}/${lv.maxScore}` : ` · —/${lv.maxScore}`}
                </span>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

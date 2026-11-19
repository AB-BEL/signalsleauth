import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import BottomNav from './components/BottomNav'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Rankings from './pages/Rankings'
import Play from './pages/Play'
import Profile from './pages/Profile'

function Private({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="screen center">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  const { user } = useAuth()
  return (
    <div className="app-shell">
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
        <Route path="/register" element={user ? <Navigate to="/" replace /> : <Register />} />
        <Route path="/" element={<Private><Dashboard /></Private>} />
        <Route path="/rankings" element={<Private><Rankings /></Private>} />
        <Route path="/play/:chapter" element={<Private><Play /></Private>} />
        <Route path="/profile" element={<Private><Profile /></Private>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      {user && <BottomNav />}
    </div>
  )
}

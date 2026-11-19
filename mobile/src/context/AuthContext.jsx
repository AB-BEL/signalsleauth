import React, { createContext, useContext, useEffect, useState } from 'react'
import { authApi } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const t = localStorage.getItem('ss_token')
    if (!t) {
      setLoading(false)
      return
    }
    authApi.me()
      .then((d) => setUser(d.user))
      .catch(() => {
        localStorage.removeItem('ss_token');
    try {
      Object.keys(localStorage).forEach((k) => {
        if (k.startsWith('signalSleuth') || k.startsWith('ss_ch')) localStorage.removeItem(k);
      });
    } catch (e) {}
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  async function login(email, password) {
    const d = await authApi.login(email, password)
    localStorage.setItem('ss_token', d.token)
    setUser(d.user)
    return d.user
  }

  async function register(payload) {
    const d = await authApi.register(payload)
    if (d.token) {
      localStorage.setItem('ss_token', d.token)
      setUser(d.user)
    }
    return d
  }

  function logout() {
    localStorage.removeItem('ss_token');
    try {
      Object.keys(localStorage).forEach((k) => {
        if (k.startsWith('signalSleuth') || k.startsWith('ss_ch')) localStorage.removeItem(k);
      });
    } catch (e) {}
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}

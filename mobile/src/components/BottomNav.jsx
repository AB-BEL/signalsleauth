import React from 'react'
import { NavLink } from 'react-router-dom'

export default function BottomNav() {
  return (
    <nav className="bottom-nav">
      <NavLink to="/" end>Home</NavLink>
      <NavLink to="/rankings">Ranks</NavLink>
      <NavLink to="/profile">Me</NavLink>
    </nav>
  )
}

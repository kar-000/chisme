import { useState } from 'react'
import LoginForm from './LoginForm'
import RegisterForm from './RegisterForm'

export default function AuthPage() {
  const [mode, setMode] = useState('login')

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center p-4">
      {/* CRT glow backdrop */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(0,206,209,0.04)_0%,transparent_70%)] pointer-events-none" />

      <div className="relative w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-[var(--text-primary)] glow-teal tracking-widest">
            chisme
          </h1>
          <p className="text-[var(--text-muted)] text-xs mt-2 tracking-wider">
            ── gossip with your people ──
          </p>
        </div>

        {/* Card */}
        <div className="bg-black/30 border border-[var(--border)] rounded-lg p-8 shadow-glow-sm">
          {mode === 'login' ? (
            <LoginForm onSwitch={() => setMode('register')} />
          ) : (
            <RegisterForm onSwitch={() => setMode('login')} />
          )}
        </div>
      </div>
    </div>
  )
}

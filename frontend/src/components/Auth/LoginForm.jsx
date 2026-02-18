import { useState } from 'react'
import useAuthStore from '../../store/authStore'
import Input from '../Common/Input'
import Button from '../Common/Button'

export default function LoginForm({ onSwitch }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const { login, loading, error, clearError } = useAuthStore()

  const handleSubmit = async (e) => {
    e.preventDefault()
    clearError()
    await login(username, password)
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <h2 className="text-xl font-medium text-[var(--text-primary)] glow-teal">Sign in</h2>

      {error && (
        <p className="text-sm text-[var(--text-error)] border border-[var(--text-error)] rounded px-3 py-2 bg-red-900/10">
          &gt; {error}
        </p>
      )}

      <Input
        label="Username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        placeholder="your_handle"
        required
        autoFocus
      />
      <Input
        label="Password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="••••••••"
        required
      />

      <Button type="submit" disabled={loading} className="w-full mt-1">
        {loading ? 'Connecting...' : 'Connect'}
      </Button>

      <p className="text-center text-xs text-[var(--text-muted)]">
        No account?{' '}
        <button
          type="button"
          onClick={onSwitch}
          className="text-[var(--text-lt)] hover:text-[var(--text-primary)] underline transition-colors"
        >
          Register
        </button>
      </p>
    </form>
  )
}

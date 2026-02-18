import { useState } from 'react'
import useAuthStore from '../../store/authStore'
import Input from '../Common/Input'
import Button from '../Common/Button'

export default function RegisterForm({ onSwitch }) {
  const [form, setForm] = useState({ username: '', email: '', password: '' })
  const { register, loading, error, clearError } = useAuthStore()

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    clearError()
    await register(form.username, form.email, form.password)
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <h2 className="text-xl font-medium text-[var(--text-primary)] glow-teal">Create account</h2>

      {error && (
        <p className="text-sm text-[var(--text-error)] border border-[var(--text-error)] rounded px-3 py-2 bg-red-900/10">
          &gt; {error}
        </p>
      )}

      <Input
        label="Username (3–20 chars, a-z0-9_)"
        value={form.username}
        onChange={set('username')}
        placeholder="your_handle"
        required
        autoFocus
      />
      <Input
        label="Email"
        type="email"
        value={form.email}
        onChange={set('email')}
        placeholder="you@example.com"
        required
      />
      <Input
        label="Password (8+ chars, 1 number, 1 symbol)"
        type="password"
        value={form.password}
        onChange={set('password')}
        placeholder="••••••••"
        required
      />

      <Button type="submit" disabled={loading} className="w-full mt-1">
        {loading ? 'Creating...' : 'Join'}
      </Button>

      <p className="text-center text-xs text-[var(--text-muted)]">
        Already have an account?{' '}
        <button
          type="button"
          onClick={onSwitch}
          className="text-[var(--text-lt)] hover:text-[var(--text-primary)] underline transition-colors"
        >
          Sign in
        </button>
      </p>
    </form>
  )
}

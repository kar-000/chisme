import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LoginForm from './LoginForm'
import useAuthStore from '../../store/authStore'

vi.mock('../../store/authStore', () => ({ default: vi.fn() }))

const defaultStore = {
  login: vi.fn(),
  loading: false,
  error: null,
  clearError: vi.fn(),
}

beforeEach(() => {
  useAuthStore.mockReturnValue(defaultStore)
})

describe('LoginForm', () => {
  it('renders username and password inputs', () => {
    render(<LoginForm />)
    expect(screen.getByPlaceholderText('your_handle')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument()
  })

  it('renders the Connect button', () => {
    render(<LoginForm />)
    expect(screen.getByRole('button', { name: /connect/i })).toBeInTheDocument()
  })

  it('calls clearError and login with credentials on submit', async () => {
    const login = vi.fn()
    const clearError = vi.fn()
    useAuthStore.mockReturnValue({ ...defaultStore, login, clearError })

    render(<LoginForm />)
    await userEvent.type(screen.getByPlaceholderText('your_handle'), 'alice')
    await userEvent.type(screen.getByPlaceholderText('••••••••'), 'secret123')
    await userEvent.click(screen.getByRole('button', { name: /connect/i }))

    expect(clearError).toHaveBeenCalledOnce()
    expect(login).toHaveBeenCalledWith('alice', 'secret123')
  })

  it('shows error when store has an error', () => {
    useAuthStore.mockReturnValue({ ...defaultStore, error: 'Invalid credentials' })
    render(<LoginForm />)
    expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
  })

  it('shows "Connecting..." when loading', () => {
    useAuthStore.mockReturnValue({ ...defaultStore, loading: true })
    render(<LoginForm />)
    expect(screen.getByRole('button', { name: /connecting/i })).toBeInTheDocument()
  })

  it('calls onSwitch when Register link is clicked', async () => {
    const onSwitch = vi.fn()
    render(<LoginForm onSwitch={onSwitch} />)
    await userEvent.click(screen.getByRole('button', { name: /register/i }))
    expect(onSwitch).toHaveBeenCalledOnce()
  })
})

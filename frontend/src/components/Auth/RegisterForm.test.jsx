import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RegisterForm from './RegisterForm'
import useAuthStore from '../../store/authStore'

vi.mock('../../store/authStore', () => ({ default: vi.fn() }))

const defaultStore = {
  register: vi.fn(),
  loading: false,
  error: null,
  clearError: vi.fn(),
}

beforeEach(() => {
  useAuthStore.mockReturnValue(defaultStore)
})

describe('RegisterForm', () => {
  it('renders username, email, and password inputs', () => {
    render(<RegisterForm />)
    expect(screen.getByPlaceholderText('your_handle')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('you@example.com')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument()
  })

  it('renders the Join button', () => {
    render(<RegisterForm />)
    expect(screen.getByRole('button', { name: /join/i })).toBeInTheDocument()
  })

  it('calls clearError and register with form values on submit', async () => {
    const register = vi.fn()
    const clearError = vi.fn()
    useAuthStore.mockReturnValue({ ...defaultStore, register, clearError })

    render(<RegisterForm />)
    await userEvent.type(screen.getByPlaceholderText('your_handle'), 'bob')
    await userEvent.type(screen.getByPlaceholderText('you@example.com'), 'bob@test.com')
    await userEvent.type(screen.getByPlaceholderText('••••••••'), 'Pass1234!')
    await userEvent.click(screen.getByRole('button', { name: /join/i }))

    expect(clearError).toHaveBeenCalledOnce()
    expect(register).toHaveBeenCalledWith('bob', 'bob@test.com', 'Pass1234!')
  })

  it('shows error when store has an error', () => {
    useAuthStore.mockReturnValue({ ...defaultStore, error: 'Username already registered' })
    render(<RegisterForm />)
    expect(screen.getByText(/username already registered/i)).toBeInTheDocument()
  })

  it('shows "Creating..." when loading', () => {
    useAuthStore.mockReturnValue({ ...defaultStore, loading: true })
    render(<RegisterForm />)
    expect(screen.getByRole('button', { name: /creating/i })).toBeInTheDocument()
  })

  it('calls onSwitch when Sign in link is clicked', async () => {
    const onSwitch = vi.fn()
    render(<RegisterForm onSwitch={onSwitch} />)
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
    expect(onSwitch).toHaveBeenCalledOnce()
  })
})
